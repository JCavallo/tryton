#!/usr/bin/env python
# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
"""Pure-framework ORM benchmark.

Creates a fresh database with only ir / res / debug activated, fills it with
a deterministic dataset (hundreds of records), then times each scenario of
scenarios.py. See README.md for usage.

Run it as a script (not with -m): the trytond configuration must be set up
before trytond is imported.
"""
import argparse
import fnmatch
import gc
import json
import os
import platform
import statistics
import subprocess
import sys
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
# Running a script puts its directory first on sys.path: drop it so the
# bench modules are only importable as trytond.modules.debug.bench.*
if sys.path and os.path.abspath(sys.path[0]) == HERE:
    sys.path.pop(0)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--backend', choices=['sqlite', 'postgresql'],
        default='sqlite')
    parser.add_argument('--uri', help='PostgreSQL server URI, without '
        'database name (default: $TRYTOND_DATABASE__URI or '
        'postgresql://tryton:tryton@localhost:5432/)')
    parser.add_argument('--config', help='trytond configuration file. By '
        'default none is loaded ($TRYTOND_CONFIG is ignored) so that the '
        'results only depend on the framework defaults')
    parser.add_argument('--cache-record', type=int,
        help='Override [cache] record (trytond default: 2000)')
    parser.add_argument('--scale', type=float, default=1.0,
        help='Dataset size multiplier (default: 1 = 300 records)')
    parser.add_argument('-n', '--repeat', type=int, default=10,
        help='Timed repetitions per scenario (default: 10)')
    parser.add_argument('-w', '--warmup', type=int, default=2,
        help='Untimed repetitions per scenario (default: 2)')
    parser.add_argument('-s', '--scenario', action='append', default=[],
        help='Scenario name or glob (repeatable, default: all)')
    parser.add_argument('--list', action='store_true',
        help='List scenarios and exit')
    parser.add_argument('-o', '--output', help='Write results as JSON')
    parser.add_argument('-c', '--compare', help='Compare with a JSON result')
    parser.add_argument('--profile', metavar='DIR', help='Also run each '
        'scenario once under cProfile and dump DIR/<scenario>.prof')
    parser.add_argument('--no-check-access', action='store_true',
        help='Do not enable access checks (they are on by default, as for '
        'RPC calls)')
    parser.add_argument('--keep-env', action='store_true',
        help='Keep the TRYTOND_<SECTION>__<OPTION> configuration variables '
        '(cleared by default, as they may enable debug or business options)')
    parser.add_argument('--keep-db', action='store_true',
        help='Do not drop the PostgreSQL database at the end')
    parser.add_argument('--allow-asserts', action='store_true',
        help='Run even without PYTHONOPTIMIZE (production runs with it)')
    return parser.parse_args(argv)


def setup_environment(args):
    "Must run before any trytond import"
    cleared = []
    if not args.keep_env:
        for key in list(os.environ):
            # Only configuration overrides (TRYTOND_<SECTION>__<OPTION>):
            # other TRYTOND_* variables are needed to import some modules
            if key.startswith('TRYTOND_') and '__' in key:
                cleared.append(key)
                del os.environ[key]
    if args.config:
        os.environ['TRYTOND_CONFIG'] = args.config
    else:
        os.environ.pop('TRYTOND_CONFIG', None)
    if args.backend == 'sqlite':
        uri = 'sqlite://'
        db_name = ':memory:'
    else:
        uri = (args.uri or os.environ.get('TRYTOND_DATABASE__URI')
            or os.environ.get('TRYTOND_DATABASE_URI')
            or 'postgresql://tryton:tryton@localhost:5432/')
        if not uri.startswith('postgresql'):
            uri = 'postgresql://tryton:tryton@localhost:5432/'
        db_name = 'bench_%s' % uuid.uuid4().hex[:12]
    os.environ['TRYTOND_DATABASE__URI'] = uri
    os.environ['TRYTOND_DATABASE_URI'] = uri
    os.environ['DB_NAME'] = db_name
    if args.cache_record:
        os.environ['TRYTOND_CACHE__RECORD'] = str(args.cache_record)
    return db_name, cleared


class DBTimer:
    "Accumulates time spent in cursor.execute(many)"
    elapsed = 0.0
    count = 0

    @classmethod
    def reset(cls):
        cls.elapsed = 0.0
        cls.count = 0

    @classmethod
    def wrap(cls, method):
        perf_counter = time.perf_counter

        def wrapper(*args, **kwargs):
            start = perf_counter()
            try:
                return method(*args, **kwargs)
            finally:
                cls.elapsed += perf_counter() - start
                cls.count += 1
        return wrapper

    @classmethod
    def install(cls, backend_name):
        if backend_name == 'postgresql':
            from trytond.backend.postgresql.database import LoggingCursor
            klass = LoggingCursor
        else:
            from trytond.backend.sqlite.database import SQLiteCursor
            klass = SQLiteCursor
        for name in ('execute', 'executemany'):
            setattr(klass, name, cls.wrap(getattr(klass, name)))


def git_revision(path):
    try:
        rev = subprocess.run(['git', '-C', path, 'rev-parse', '--short',
                'HEAD'], capture_output=True, text=True, check=True
            ).stdout.strip()
        dirty = subprocess.run(['git', '-C', path, 'status', '--porcelain',
                '--untracked-files=no', '--', '.'], capture_output=True,
            text=True).stdout.strip()
        return rev + ('-dirty' if dirty else '')
    except Exception:
        return None


def summarize(samples):
    def med(key):
        return statistics.median(s[key] for s in samples)

    walls = [s['wall'] for s in samples]
    pys = [s['wall'] - s['db'] for s in samples]
    py_median = statistics.median(pys)
    mad = statistics.median(abs(p - py_median) for p in pys)
    return {
        'wall': statistics.median(walls),
        'wall_min': min(walls),
        'python': py_median,
        'python_min': min(pys),
        'python_mad': mad,
        'cpu': med('cpu'),
        'db': med('db'),
        'queries': med('queries'),
        'gc0': med('gc0'),
        'samples': samples,
        }


def run_once(func, data, db_name, check_access_enabled):
    from trytond.transaction import Transaction, check_access
    with Transaction().start(db_name, 1) as transaction:
        ctx = check_access() if check_access_enabled else _null()
        with ctx:
            gc.collect()
            gc0 = gc.get_stats()[0]['collections']
            DBTimer.reset()
            cpu = time.process_time()
            start = time.perf_counter()
            func(data)
            wall = time.perf_counter() - start
            cpu = time.process_time() - cpu
            gc0 = gc.get_stats()[0]['collections'] - gc0
            db, queries = DBTimer.elapsed, DBTimer.count
        transaction.rollback()
    return {'wall': wall, 'cpu': cpu, 'db': db, 'queries': queries,
        'gc0': gc0}


class _null:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def fmt_ms(value):
    return '%9.2f' % (value * 1000)


def compare_line(name, current, baseline):
    base = baseline.get(name)
    if not base:
        return '   (new)'
    ratio = current['python'] / base['python'] if base['python'] else 0
    noise = max(0.03, 3 * max(current['python_mad'], base['python_mad'])
        / max(base['python'], 1e-9))
    delta = ratio - 1
    flag = ' '
    if abs(delta) > noise:
        flag = '-' if delta < 0 else '+'
    qdelta = ''
    if current['queries'] != base['queries']:
        qdelta = ' queries %d->%d' % (base['queries'], current['queries'])
    return ' %s %+6.1f%% (noise %.1f%%)%s' % (
        flag, delta * 100, noise * 100, qdelta)


def main(argv=None):
    args = parse_args(argv)
    db_name, cleared_env = setup_environment(args)

    if not sys.flags.optimize and not args.allow_asserts and not args.list:
        sys.exit('Production runs with PYTHONOPTIMIZE=1 and some asserts in '
            'the ORM are O(n) per record: run with PYTHONOPTIMIZE=1 (or -O), '
            'or pass --allow-asserts')

    from trytond.modules.debug.bench.scenarios import SCENARIOS
    if args.list:
        for name, info in SCENARIOS.items():
            print('%-24s %-9s %s' % (name, info['group'], info['doc']))
        return

    selected = [name for name in SCENARIOS
        if not args.scenario
        or any(fnmatch.fnmatch(name, pat) for pat in args.scenario)]
    if not selected:
        sys.exit('No scenario matches %s' % args.scenario)

    from trytond import backend
    from trytond import config
    from trytond.tests import test_tryton
    from trytond.pool import Pool
    from trytond.transaction import Transaction

    print('Setting up %s database %s...' % (backend.name, db_name),
        file=sys.stderr)
    start = time.perf_counter()
    test_tryton.activate_module(['debug'])
    from trytond.modules.debug.bench import data as bench_data
    with Transaction().start(db_name, 0) as transaction:
        data = bench_data.populate(args.scale)
        transaction.commit()
    # Test mode only matters for the setup (table ids, strict gettext)
    Pool.test = False
    print('Setup done in %.1fs (%d records, %d lines)' % (
            time.perf_counter() - start, len(data['record_ids']),
            len(data['line_ids'])), file=sys.stderr)

    DBTimer.install(backend.name)
    baseline = {}
    if args.compare:
        with open(args.compare) as f:
            baseline = json.load(f)['results']

    results = {}
    try:
        print('%-24s %9s %9s %9s %9s %7s %7s' % ('scenario (ms)', 'python',
                'mad', 'db', 'wall', 'queries', 'gc0'))
        for name in selected:
            func = SCENARIOS[name]['func']
            check = not args.no_check_access
            for _ in range(args.warmup):
                run_once(func, data, db_name, check)
            samples = [run_once(func, data, db_name, check)
                for _ in range(args.repeat)]
            results[name] = summary = summarize(samples)
            line = '%-24s %s %s %s %s %7d %7d' % (name,
                fmt_ms(summary['python']), fmt_ms(summary['python_mad']),
                fmt_ms(summary['db']), fmt_ms(summary['wall']),
                summary['queries'], summary['gc0'])
            if baseline:
                line += compare_line(name, summary, baseline)
            print(line, flush=True)

            if args.profile:
                import cProfile
                os.makedirs(args.profile, exist_ok=True)
                profiler = cProfile.Profile()
                from trytond.transaction import check_access
                with Transaction().start(db_name, 1) as transaction:
                    with (check_access() if check else _null()):
                        profiler.enable()
                        func(data)
                        profiler.disable()
                    transaction.rollback()
                profiler.dump_stats(
                    os.path.join(args.profile, name + '.prof'))
    finally:
        if backend.name == 'postgresql' and not args.keep_db:
            test_tryton.drop_db(db_name)

    if baseline:
        total = sum(results[n]['python'] for n in results if n in baseline)
        base_total = sum(baseline[n]['python'] for n in results
            if n in baseline)
        if base_total:
            print('%-24s %s vs %s baseline (%+.1f%%)' % ('TOTAL python',
                    fmt_ms(total), fmt_ms(base_total).strip(),
                    (total / base_total - 1) * 100))

    trytond_path = os.path.dirname(os.path.dirname(
            os.path.abspath(test_tryton.__file__)))
    meta = {
        'date': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'host': platform.node(),
        'python': sys.version.split()[0],
        'optimize': sys.flags.optimize,
        'backend': backend.name,
        'trytond_revision': git_revision(trytond_path),
        'scale': args.scale,
        'sizes': data['sizes'],
        'repeat': args.repeat,
        'warmup': args.warmup,
        'check_access': not args.no_check_access,
        'config': args.config,
        'cleared_env': cleared_env,
        'cache': {k: config.get('cache', k, default=None)
            for k in ('model', 'record', 'field')},
        }
    if args.output:
        with open(args.output, 'w') as f:
            json.dump({'meta': meta, 'results': results}, f, indent=1,
                default=str)
        print('Results written to %s' % args.output, file=sys.stderr)


if __name__ == '__main__':
    main()
