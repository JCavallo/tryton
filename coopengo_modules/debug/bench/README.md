# ORM benchmark

A pure-framework benchmark of the trytond ORM's Python cost. It covers
instantiation, lazy loading, `read`, query building, writes, validation and
the ModelView helpers.

Each run creates a fresh database with only `ir`, `res` and `debug`
activated. It loads a deterministic dataset into it: 300 wide records, 1200
lines, 10 categories and 20 tags. The models are in `models.py`; they have
about 100 stored fields plus m2o / o2m / m2m relations and function fields.
Then the runner times every scenario in `scenarios.py`.

## Usage

```bash
# From an env root, with the env's Python
PYTHONOPTIMIZE=1 python tryton/coopengo_modules/debug/bench/run.py --list
PYTHONOPTIMIZE=1 python tryton/coopengo_modules/debug/bench/run.py \
    --backend postgresql -o baseline.json
# After a patch: compare (flags +/- outside noise, and query count changes)
PYTHONOPTIMIZE=1 python tryton/coopengo_modules/debug/bench/run.py \
    --backend postgresql -c baseline.json -o patched.json
# A subset, with cProfile dumps (one extra run per scenario)
PYTHONOPTIMIZE=1 python tryton/coopengo_modules/debug/bench/run.py \
    -s 'browse_*' --profile /tmp/prof
```

- **Always run it optimized.** Production runs with `PYTHONOPTIMIZE=1`,
  and some ORM asserts are O(n) per record. The runner refuses to start
  without it unless `--allow-asserts` is passed.
- **The environment is pure framework by default.** `$TRYTOND_CONFIG`
  and the `TRYTOND_<SECTION>__<OPTION>` overrides are ignored, so a debug
  or business option set in the env doesn't change the results. Use
  `--config` / `--keep-env` to opt back in, and `--cache-record` to test
  another `[cache] record` value (master_2's conf sets it to 10000; the
  trytond default is 2000).
- **The framework is not fully pure in a Coog env.** `Pool.start()` imports
  every module on disk, activated or not, so import-time patches still
  apply. For example, `coog_core.monkey_patches` adds savepoint-aware
  properties to `Transaction`, and the "Missing canary" log line comes from
  importing coog_core. For upstream-grade numbers, run the bench on a trytond
  install that has no coog modules.
- **PostgreSQL databases are temporary.** They are named `bench_<random>`
  and dropped at the end (`--keep-db` keeps them). The server URI comes
  from `--uri`, `$TRYTOND_DATABASE__URI`, or
  `postgresql://tryton:tryton@localhost:5432/` by default.
- **Access checks are on by default**, as for RPC calls
  (`--no-check-access` turns them off). Scenarios run as the admin user.

## Measurement

Each repetition runs in a fresh transaction that is rolled back afterwards.
So every repetition starts from the same data with cold transaction caches;
the global caches (`Cache`, access rights...) stay warm. That matches a
server in steady state.

| column | meaning |
| --- | --- |
| python | median of (wall time − time spent in `cursor.execute(many)`) |
| mad | median absolute deviation of `python`, the noise level |
| db | median time spent in `cursor.execute(many)` |
| queries | number of `execute(many)` calls |
| gc0 | generation-0 GC collections: a rough proxy for container allocations |

Two caveats about the `python` column:
- Row fetching and conversion (`fetchall`) happen outside `execute`, so
  they count as Python time. With psycopg3 that is the real client-side
  cost, not a measurement artifact.
- On sqlite, `execute` only steps to the first row, so the sqlite DB time is
  a lower bound.

PostgreSQL is the reference backend for the numbers. Sqlite is a fast
smoke check.

Compare mode flags a scenario only when its Python time moved by more than
max(3%, 3 × MAD). It also reports any change in query count, because a
Python speed-up that adds queries is not a win.

## Representativeness

The scenarios are not a weighted workload: each one isolates a single
framework path. The `small` and `service` groups exist because business
calls (APIs, simulations) make many small ORM calls rather than a few big
ones. Their cost is per-call overhead: query building, context switches,
cache lookups, `Pool()`.

The scenario set was checked against a profile of the Coog loan simulation
API (`api.contract.simulate`, from global_tests). Every framework function
above about 0.35% of the API's self time makes up at least about 2% of one
scenario.

## Adding a scenario

Add a `bench_<name>(data)` function decorated with `@scenario('<group>')` in
`scenarios.py`. `data` holds the dataset ids (`record_ids`, `line_ids`,
`category_ids`, `tag_ids`, `sizes`). Keep each scenario focused on one
framework path, at roughly 10–300 ms, so changes can be attributed.
