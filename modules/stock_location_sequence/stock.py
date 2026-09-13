# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import sequence_ordered
from trytond.pool import PoolMeta


_SequenceOrderedMixin = sequence_ordered()


class Location(_SequenceOrderedMixin, metaclass=PoolMeta):
    __name__ = 'stock.location'
    _order_name = 'sequence'
