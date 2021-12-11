# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import doctest
import unittest

import trytond.tests.test_tryton
from trytond.tests.test_tryton import (
    ModuleTestCase, doctest_checker, doctest_teardown)


class AccountInvoiceCorrectionTestCase(ModuleTestCase):
    'Test Account Invoice Correction module'
    module = 'account_invoice_correction'


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
            AccountInvoiceCorrectionTestCase))
    suite.addTests(doctest.DocFileSuite('scenario_invoice_correction.rst',
            tearDown=doctest_teardown, encoding='utf-8',
            checker=doctest_checker,
            optionflags=doctest.REPORT_ONLY_FIRST_FAILURE))
    return suite
