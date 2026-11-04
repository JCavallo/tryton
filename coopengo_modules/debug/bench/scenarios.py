# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
"""ORM benchmark scenarios.

A scenario is a function taking the dataset (see data.populate) and doing
one unit of work. The runner calls it in a fresh transaction for each
repetition and rolls back afterwards, so scenarios may write freely and
always start from the same database state with cold transaction caches.

Each scenario targets one framework path; keep them small and focused so a
regression or an improvement can be attributed.
"""
import datetime
import random
from decimal import Decimal

from trytond.cache import Cache
from trytond.pool import Pool
from trytond.pyson import Bool, Eval, If, PYSONDecoder, PYSONEncoder
from trytond.transaction import Transaction

from .data import line_values, record_values
from .models import WIDE_FIELDS

SCENARIOS = {}

_lookup_cache = Cache('debug.bench.lookup', context=True)

SCALAR_FIELDS = ['name', 'code', 'start_date', 'state'] + [
    'char_00', 'integer_00', 'numeric_00', 'date_00', 'boolean_00',
    'selection_00']


def scenario(group):
    def decorator(func):
        name = func.__name__[len('bench_'):]
        SCENARIOS[name] = {
            'func': func,
            'group': group,
            'doc': (func.__doc__ or '').strip(),
            }
        return func
    return decorator


def _models():
    pool = Pool()
    return (pool.get('debug.bench.record'), pool.get('debug.bench.line'),
        pool.get('debug.bench.category'), pool.get('debug.bench.tag'))


# ---------------------------------------------------------------- instances

@scenario('instance')
def bench_instantiate(data):
    "browse() all records and lines 10 times, no field access"
    Record, Line, _, _ = _models()
    for _ in range(10):
        Record.browse(data['record_ids'])
        Line.browse(data['line_ids'])


@scenario('instance')
def bench_instantiate_single(data):
    "Model(id) one by one for all records and lines, 3 times"
    Record, Line, _, _ = _models()
    for _ in range(3):
        for id_ in data['record_ids']:
            Record(id_)
        for id_ in data['line_ids']:
            Line(id_)


# ------------------------------------------------------------- lazy loading

@scenario('browse')
def bench_browse_scalar(data):
    "Lazy-load 10 scalar fields on all records"
    Record, _, _, _ = _models()
    for record in Record.browse(data['record_ids']):
        for fname in SCALAR_FIELDS:
            getattr(record, fname)


@scenario('browse')
def bench_browse_wide(data):
    "Lazy-load every stored scalar field on all records"
    Record, _, _, _ = _models()
    names = list(WIDE_FIELDS)
    for record in Record.browse(data['record_ids']):
        for fname in names:
            getattr(record, fname)


@scenario('browse')
def bench_browse_many2one(data):
    "Follow two many2one (one with a PYSON context) and read the target"
    Record, _, _, _ = _models()
    for record in Record.browse(data['record_ids']):
        record.category.name
        record.category_ctx.code


@scenario('browse')
def bench_browse_x2many(data):
    "Iterate one2many lines (scalar + function field) and many2many tags"
    Record, _, _, _ = _models()
    for record in Record.browse(data['record_ids']):
        for line in record.lines:
            line.quantity
            line.amount
        for tag in record.tags:
            tag.name


@scenario('browse')
def bench_browse_function(data):
    "Function fields: multiple getter, single getter, on_change_with getter"
    Record, _, _, _ = _models()
    for record in Record.browse(data['record_ids']):
        record.total
        record.line_count
        record.category_name
        record.lines_total


@scenario('browse')
def bench_browse_repeat(data):
    "Access already loaded fields 20 times (pure cache hit path)"
    Record, _, _, _ = _models()
    records = Record.browse(data['record_ids'])
    for record in records:
        record.name
    for _ in range(20):
        for record in records:
            record.name
            record.code
            record.state


# --------------------------------------------------------------------- read

@scenario('read')
def bench_read_some(data):
    "read() 10 scalar fields on all records"
    Record, _, _, _ = _models()
    Record.read(data['record_ids'], SCALAR_FIELDS)


@scenario('read')
def bench_read_all(data):
    "read() every field (stored, relations, functions) on all records"
    Record, _, _, _ = _models()
    Record.read(data['record_ids'], list(Record._fields))


@scenario('read')
def bench_read_dotted(data):
    "read() with dotted names through many2one and x2many"
    Record, _, _, _ = _models()
    Record.read(data['record_ids'], ['name', 'rec_name', 'category.name',
            'category.code', 'lines.amount', 'tags.name'])


@scenario('read')
def bench_read_lines(data):
    "read() on the lines (small model, many records)"
    _, Line, _, _ = _models()
    Line.read(data['line_ids'], ['record', 'sequence', 'quantity',
            'unit_price', 'amount', 'date'])


# ------------------------------------------------------------------- search

def _domains():
    base = datetime.date(2020, 6, 1)
    return [
        [('name', 'ilike', 'Record 1%')],
        [('category.code', '=', 'CAT1')],
        ['OR', ('state', '=', 'draft'), ('integer_00', '>', 500000)],
        [('lines.quantity', '>', 50)],
        [('tags.name', 'in', ['Tag 1', 'Tag 2', 'Tag 3'])],
        [('start_date', '>=', base), ('code', 'like', 'R0001%')],
        [('category', 'where', [('rate', '>', Decimal('0.3'))]),
            ('boolean_00', '=', True)],
        ['OR',
            [('char_00', 'ilike', '%5%'), ('numeric_00', '<', 1000)],
            [('selection_00', 'in', ['v1', 'v2']),
                ('date_00', '<', base)]],
        ]


ORDERS = [
    None,
    [('category.name', 'ASC'), ('code', 'DESC')],
    [('start_date', 'DESC')],
    ]


@scenario('search')
def bench_search_build(data):
    ("Build and stringify search queries (domain parsing + python-sql), "
        "nothing executed")
    Record, _, _, _ = _models()
    domains = _domains()
    for _ in range(5):
        for domain in domains:
            for order in ORDERS:
                query = Record.search(domain, order=order, query=True)
                str(query)
                query.params


@scenario('search')
def bench_search(data):
    "Execute searches returning instances"
    Record, _, _, _ = _models()
    for domain in _domains():
        for order in ORDERS:
            Record.search(domain, order=order)


@scenario('search')
def bench_search_count(data):
    "search_count on every domain"
    Record, _, _, _ = _models()
    for domain in _domains():
        Record.search_count(domain)


@scenario('search')
def bench_search_read(data):
    "search_read() as the clients do it, 10 fields"
    Record, _, _, _ = _models()
    for domain in _domains()[:4]:
        Record.search_read(domain, limit=100,
            fields_names=SCALAR_FIELDS + ['category.rec_name'])


# -------------------------------------------------------------------- write

@scenario('write')
def bench_create(data):
    "create() 30 wide records with 4 lines and 3 tags each"
    Record, _, _, _ = _models()
    rng = random.Random(1)
    Record.create([
            record_values(rng, 100000 + i, data['category_ids'],
                data['tag_ids'], data['sizes'])
            for i in range(30)])


@scenario('write')
def bench_write_batch(data):
    "write() 5 fields on all records in one call"
    Record, _, _, _ = _models()
    Record.write(Record.browse(data['record_ids']), {
            'char_01': 'written',
            'integer_01': 42,
            'numeric_01': Decimal('4.2'),
            'state': 'active',
            'category': data['category_ids'][0],
            })


@scenario('write')
def bench_write_loop(data):
    "write() record by record on 50 records (common business pattern)"
    Record, _, _, _ = _models()
    for i, record in enumerate(Record.browse(data['record_ids'][:50])):
        Record.write([record], {'integer_02': i, 'char_02': 'loop %d' % i})


@scenario('write')
def bench_save(data):
    "Modify instances (scalar + new one2many line) then save() them"
    Record, Line, _, _ = _models()
    rng = random.Random(2)
    records = Record.browse(data['record_ids'][:50])
    for i, record in enumerate(records):
        record.integer_03 = i
        record.char_03 = 'saved %d' % i
        record.lines = list(record.lines) + [Line(**line_values(rng, 99))]
    Record.save(records)


@scenario('write')
def bench_copy(data):
    "copy() 10 records with their lines and tags"
    Record, _, _, _ = _models()
    Record.copy(Record.browse(data['record_ids'][:10]))


@scenario('write')
def bench_delete(data):
    "delete() 50 records (cascades to lines and tags)"
    Record, _, _, _ = _models()
    Record.delete(Record.browse(data['record_ids'][-50:]))


@scenario('write')
def bench_validate(data):
    "_validate() all records (required, domains, digits, selection...)"
    Record, _, _, _ = _models()
    Record._validate(Record.browse(data['record_ids']))


# ---------------------------------------------------------------- modelview

@scenario('view')
def bench_unsaved_on_change(data):
    ("Unsaved instances with nested lines and on_change_with "
        "(simulation pattern)")
    Record, Line, _, _ = _models()
    rng = random.Random(3)
    for i in range(100):
        record = Record(
            name='Simulated %d' % i,
            code='S%d' % i,
            category=data['category_ids'][i % len(data['category_ids'])],
            lines=[Line(**line_values(rng, s)) for s in range(4)])
        for line in record.lines:
            line.on_change_with(['amount'])
        record.on_change_with(['lines_total'])


@scenario('view')
def bench_default_get(data):
    "default_get() for every field, 50 times"
    Record, _, _, _ = _models()
    names = list(Record._fields)
    for _ in range(50):
        Record.default_get(names, with_rec_name=False)


@scenario('view')
def bench_fields_get(data):
    "fields_get() on all bench models, 5 times"
    for Model in _models():
        for _ in range(5):
            Model.fields_get()


@scenario('view')
def bench_pyson(data):
    "PYSON encode + decode of typical states / domains, 500 times"
    exprs = [
        {'readonly': Eval('state') != 'draft',
            'invisible': ~Bool(Eval('lines', []))},
        [('category', '=', Eval('category', -1)),
            If(Bool(Eval('start_date')),
                ('start_date', '>=', Eval('start_date')), ())],
        ]
    ctx = {'state': 'draft', 'lines': [1, 2], 'category': 3,
        'start_date': datetime.date(2020, 1, 1)}
    encoder = PYSONEncoder()
    for _ in range(500):
        for expr in exprs:
            PYSONDecoder(ctx).decode(encoder.encode(expr))


# ------------------------------------------------------- many small calls
# Business code (APIs, simulations) does many small calls rather than a few
# big ones: per-call overhead (query building, context, caches) dominates.

@scenario('small')
def bench_small_search(data):
    "200 searches returning one record (by code), with a limit"
    Record, _, _, _ = _models()
    for i in range(200):
        Record.search([('code', '=', 'R%06d' % (i % 300))], limit=1)


@scenario('small')
def bench_small_read(data):
    "200 read() of one record, 5 fields"
    Record, _, _, _ = _models()
    ids = data['record_ids']
    for i in range(200):
        Record.read([ids[i % len(ids)]], ['name', 'code', 'state',
                'category', 'numeric_00'])


@scenario('small')
def bench_small_browse(data):
    "200 fresh single instances, follow a many2one (one query each)"
    Record, _, _, _ = _models()
    ids = data['record_ids']
    for i in range(200):
        Record(ids[i % len(ids)]).category.code


@scenario('small')
def bench_small_search_m2o(data):
    "200 searches through a many2one join, ordered, count after"
    Record, _, _, _ = _models()
    for i in range(100):
        Record.search([('category.code', '=', 'CAT%d' % (i % 10)),
                ('state', '!=', 'closed')], order=[('start_date', 'DESC')],
            limit=10)
        Record.search_count([('lines.quantity', '>', i % 100)])


# ------------------------------------------------- framework services

@scenario('service')
def bench_context_switch(data):
    "set_context / reset_context / set_user and context reads, 3000 times"
    transaction = Transaction()
    for i in range(3000):
        with transaction.set_context(bench_code='R%06d' % i, bench_i=i):
            with transaction.set_context(_datetime=None):
                Transaction().context.get('bench_code')
            with transaction.reset_context(), transaction.set_user(0):
                Transaction().user
            transaction.get_cache()


@scenario('service')
def bench_memory_cache(data):
    "Cache.get hits with context-dependent keys, 2000 times"
    transaction = Transaction()
    for i in range(2000):
        with transaction.set_context(bench_flag=i % 7):
            key = ('debug.bench.record', i % 50, ('a', 'b'))
            if _lookup_cache.get(key) is None:
                _lookup_cache.set(key, {'value': i})


@scenario('service')
def bench_memory_cache_set(data):
    "Cache.set of nested values (deep immutable copy), 1000 times"
    value = {'ids': list(range(20)), 'names': {'a': [1, 2], 'b': {'c': 3}},
        'flags': {1, 2, 3}, 'label': 'value'}
    for i in range(1000):
        _lookup_cache.set(('debug.bench.set', i % 100), value)


@scenario('service')
def bench_access_check(data):
    "ModelAccess.check + FieldAccess.check (as done for every RPC / read)"
    pool = Pool()
    ModelAccess = pool.get('ir.model.access')
    FieldAccess = pool.get('ir.model.field.access')
    names = ['name', 'code', 'state', 'category', 'lines']
    for _ in range(300):
        for model in ('debug.bench.record', 'debug.bench.line'):
            ModelAccess.check(model, 'read')
            ModelAccess.check(model, 'write')
        FieldAccess.check('debug.bench.record', names, 'read')


@scenario('service')
def bench_pool_get(data):
    "Pool() + get() as business code does it, 5000 times"
    names = ['debug.bench.record', 'debug.bench.line', 'ir.model',
        'res.user', 'ir.model.access']
    for i in range(5000):
        Pool().get(names[i % 5])
