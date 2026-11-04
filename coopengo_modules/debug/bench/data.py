# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
"""Deterministic dataset for the ORM benchmark."""
import datetime
import random
from decimal import Decimal

from trytond.pool import Pool

from .models import SELECTION, WIDE_FIELDS

# Base sizes, multiplied by --scale. Hundreds of records: the benchmark is
# about per-record Python cost, not about volume.
SIZES = {
    'categories': 10,
    'tags': 20,
    'records': 300,
    'lines_per_record': 4,
    'tags_per_record': 3,
    }

BASE_DATE = datetime.date(2020, 1, 1)


def wide_values(rng, index):
    values = {}
    for name, type_ in WIDE_FIELDS.items():
        if type_ == 'char':
            values[name] = 'c%d-%s' % (index, rng.randrange(10 ** 6))
        elif type_ == 'integer':
            values[name] = rng.randrange(10 ** 6)
        elif type_ == 'numeric':
            values[name] = Decimal(rng.randrange(10 ** 6)) / 100
        elif type_ == 'float':
            values[name] = rng.random() * 1000
        elif type_ == 'date':
            values[name] = BASE_DATE + datetime.timedelta(
                days=rng.randrange(3650))
        elif type_ == 'boolean':
            values[name] = rng.random() < 0.5
        elif type_ == 'selection':
            values[name] = rng.choice(SELECTION[1:])[0]
        elif type_ == 'text':
            values[name] = 'text %d ' % index * rng.randrange(1, 20)
    return values


def line_values(rng, sequence):
    return {
        'sequence': sequence,
        'description': 'line %d' % sequence,
        'date': BASE_DATE + datetime.timedelta(days=rng.randrange(3650)),
        'quantity': Decimal(rng.randrange(1, 100)),
        'unit_price': Decimal(rng.randrange(1, 10 ** 6)) / 100,
        }


def record_values(rng, index, category_ids, tag_ids, sizes):
    values = wide_values(rng, index)
    values.update({
            'name': 'Record %d' % index,
            'code': 'R%06d' % index,
            'start_date': BASE_DATE + datetime.timedelta(days=index % 365),
            'state': ('draft', 'active', 'closed')[index % 3],
            'kind': 'k%d' % (index % 5),
            'category': category_ids[index % len(category_ids)],
            'category_ctx': category_ids[(index + 1) % len(category_ids)],
            'lines': [('create', [
                        line_values(rng, s)
                        for s in range(sizes['lines_per_record'])])],
            'tags': [('add', rng.sample(tag_ids,
                        min(sizes['tags_per_record'], len(tag_ids))))],
            })
    return values


def scaled_sizes(scale):
    sizes = dict(SIZES)
    sizes['records'] = max(1, int(SIZES['records'] * scale))
    return sizes


def populate(scale=1.0, seed=42):
    "Create the dataset in the current transaction and return its ids"
    pool = Pool()
    Category = pool.get('debug.bench.category')
    Tag = pool.get('debug.bench.tag')
    Record = pool.get('debug.bench.record')
    Line = pool.get('debug.bench.line')

    rng = random.Random(seed)
    sizes = scaled_sizes(scale)
    categories = Category.create([{
                'name': 'Category %d' % i,
                'code': 'CAT%d' % i,
                'rate': Decimal(i) / 10,
                } for i in range(sizes['categories'])])
    tags = Tag.create([{'name': 'Tag %d' % i}
            for i in range(sizes['tags'])])
    category_ids = [c.id for c in categories]
    tag_ids = [t.id for t in tags]
    records = Record.create([
            record_values(rng, i, category_ids, tag_ids, sizes)
            for i in range(sizes['records'])])
    return {
        'sizes': sizes,
        'category_ids': category_ids,
        'tag_ids': tag_ids,
        'record_ids': [r.id for r in records],
        'line_ids': [line.id
            for line in Line.search([], order=[('id', 'ASC')])],
        }
