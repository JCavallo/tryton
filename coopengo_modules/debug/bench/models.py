# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
"""Synthetic models for the ORM benchmark.

They only depend on the framework (ir / res), so that the benchmark measures
trytond itself rather than business modules. The shapes mimic what business
models look like:

- ``debug.bench.record``: a "wide" model (many stored fields of every basic
  type), with a many2one, a one2many, a many2many, function fields with a
  multiple getter, a single getter, a field with a PYSON context and an
  on_change_with depending on a one2many.
- ``debug.bench.line``: the one2many target, with a function field and an
  on_change_with.
- ``debug.bench.category`` / ``debug.bench.tag``: small referential models.
"""
import datetime
from decimal import Decimal

from trytond.model import ModelSQL, ModelView, fields
from trytond.pyson import Eval

__all__ = [
    'BenchCategory',
    'BenchTag',
    'BenchRecord',
    'BenchRecordTag',
    'BenchLine',
    'WIDE_FIELDS',
    ]

# Number of stored scalar fields per type on the wide model. 100 stored
# scalar fields + relations + function fields is in the range of the big
# business models (party, contract, invoice...).
WIDE_SHAPE = {
    'char': 30,
    'integer': 15,
    'numeric': 15,
    'float': 5,
    'date': 10,
    'boolean': 10,
    'selection': 10,
    'text': 5,
    }

SELECTION = [(None, '')] + [('v%d' % i, 'Value %d' % i) for i in range(10)]


def _make_field(type_, index):
    string = '%s %d' % (type_.capitalize(), index)
    if type_ == 'char':
        return fields.Char(string)
    if type_ == 'integer':
        return fields.Integer(string)
    if type_ == 'numeric':
        return fields.Numeric(string, digits=(16, 2))
    if type_ == 'float':
        return fields.Float(string)
    if type_ == 'date':
        return fields.Date(string)
    if type_ == 'boolean':
        return fields.Boolean(string)
    if type_ == 'selection':
        return fields.Selection(SELECTION, string)
    if type_ == 'text':
        return fields.Text(string)
    raise ValueError(type_)


WIDE_FIELDS = {
    '%s_%02d' % (type_, i): type_
    for type_, nb in WIDE_SHAPE.items()
    for i in range(nb)}


class BenchCategory(ModelSQL, ModelView):
    'Bench Category'
    __name__ = 'debug.bench.category'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    active = fields.Boolean('Active')
    rate = fields.Numeric('Rate', digits=(16, 4))

    @staticmethod
    def default_active():
        return True


class BenchTag(ModelSQL, ModelView):
    'Bench Tag'
    __name__ = 'debug.bench.tag'

    name = fields.Char('Name', required=True)


class BenchRecord(ModelSQL, ModelView):
    'Bench Record'
    __name__ = 'debug.bench.record'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    start_date = fields.Date('Start Date', required=True)
    state = fields.Selection([
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('closed', 'Closed'),
            ], 'State', required=True)
    # Selection from a method: validated through a different path
    kind = fields.Selection('get_kinds', 'Kind')
    category = fields.Many2One('debug.bench.category', 'Category',
        required=True, ondelete='RESTRICT',
        domain=[('active', '=', True)])
    # A relation whose target is read in a specific context, to exercise
    # the PYSON context path in ModelStorage.__getattr__
    category_ctx = fields.Many2One('debug.bench.category',
        'Category (context)', ondelete='SET NULL',
        context={'bench_code': Eval('code')}, depends=['code'])
    lines = fields.One2Many('debug.bench.line', 'record', 'Lines')
    tags = fields.Many2Many('debug.bench.record-debug.bench.tag',
        'record', 'tag', 'Tags')
    total = fields.Function(fields.Numeric('Total', digits=(16, 2)),
        'get_totals')
    line_count = fields.Function(fields.Integer('Line Count'), 'get_totals')
    category_name = fields.Function(fields.Char('Category Name'),
        'get_category_name')
    lines_total = fields.Function(fields.Numeric('Lines Total',
            digits=(16, 2)),
        'on_change_with_lines_total')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order = [('code', 'ASC'), ('id', 'ASC')]

    @staticmethod
    def default_state():
        return 'draft'

    @staticmethod
    def default_start_date():
        return datetime.date(2020, 1, 1)

    @classmethod
    def get_kinds(cls):
        return [(None, '')] + [('k%d' % i, 'Kind %d' % i) for i in range(5)]

    @classmethod
    def get_totals(cls, records, names):
        result = {name: {r.id: None for r in records} for name in names}
        for record in records:
            amounts = [line.amount or 0 for line in record.lines]
            if 'total' in names:
                result['total'][record.id] = sum(amounts, Decimal(0))
            if 'line_count' in names:
                result['line_count'][record.id] = len(amounts)
        return result

    def get_category_name(self, name):
        return self.category.name if self.category else None

    @fields.depends('lines')
    def on_change_with_lines_total(self, name=None):
        return sum((line.amount or 0 for line in self.lines or []),
            Decimal(0))


# The wide part of the record model is generated, to keep the class readable
for _name, _type in WIDE_FIELDS.items():
    setattr(BenchRecord, _name,
        _make_field(_type, int(_name.rsplit('_', 1)[1])))
del _name, _type


class BenchRecordTag(ModelSQL):
    'Bench Record - Tag'
    __name__ = 'debug.bench.record-debug.bench.tag'

    record = fields.Many2One('debug.bench.record', 'Record', required=True,
        ondelete='CASCADE')
    tag = fields.Many2One('debug.bench.tag', 'Tag', required=True,
        ondelete='CASCADE')


class BenchLine(ModelSQL, ModelView):
    'Bench Line'
    __name__ = 'debug.bench.line'

    record = fields.Many2One('debug.bench.record', 'Record', required=True,
        ondelete='CASCADE')
    sequence = fields.Integer('Sequence')
    description = fields.Char('Description')
    date = fields.Date('Date')
    quantity = fields.Numeric('Quantity', digits=(16, 2), required=True,
        domain=[('quantity', '>=', 0)])
    unit_price = fields.Numeric('Unit Price', digits=(16, 4), required=True)
    amount = fields.Function(fields.Numeric('Amount', digits=(16, 2)),
        'on_change_with_amount')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order = [('sequence', 'ASC'), ('id', 'ASC')]

    @fields.depends('quantity', 'unit_price')
    def on_change_with_amount(self, name=None):
        if self.quantity is None or self.unit_price is None:
            return None
        return (self.quantity * self.unit_price).quantize(Decimal('0.01'))
