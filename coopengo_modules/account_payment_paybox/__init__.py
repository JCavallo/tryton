# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.pool import Pool
from . import payment


def register():
    Pool.register(
        payment.Payment,
        payment.Group,
        payment.Journal,
        module='account_payment_paybox', type_='model')
    Pool.register(
        payment.ProcessPayment,
        module='account_payment_paybox', type_='wizard')
