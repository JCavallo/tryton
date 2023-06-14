# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
try:
    import phonenumbers
except ImportError:
    phonenumbers = None

from trytond.tests.test_tryton import ModuleTestCase


class AccountTestCase(ModuleTestCase):
    'Test Account Payment Paybox module'
    module = 'account_payment_paybox'


del ModuleTestCase
