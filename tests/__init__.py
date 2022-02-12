# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

try:
    from trytond.modules.account_invoice_watermark.tests.test_account_invoice_watermark import \
        suite  # noqa: E501
except ImportError:
    from .test_account_invoice_watermark import suite

__all__ = ['suite']
