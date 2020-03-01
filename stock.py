# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction


class Move(metaclass=PoolMeta):
    __name__ = 'stock.move'
    invoice_lines = fields.Many2Many('account.invoice.line-stock.move',
        'stock_move', 'invoice_line', 'Invoice Lines')

    @property
    def invoiced_quantity(self):
        'The quantity from linked invoice lines in move unit'
        pool = Pool()
        Uom = pool.get('product.uom')
        quantity = 0
        for invoice_line in self.invoice_lines:
            quantity += Uom.compute_qty(invoice_line.unit,
                invoice_line.quantity, self.uom)
        return quantity

    @classmethod
    def copy(cls, moves, default=None):
        if default is None:
            default = {}
        else:
            default = default.copy()
        if not Transaction().context.get('_stock_move_split'):
            default.setdefault('invoice_lines', None)
        return super().copy(moves, default=default)
