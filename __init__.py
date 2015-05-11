# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

from trytond.pool import Pool
from .complaint import *
from .sale import *


def register():
    Pool.register(
        Type,
        Complaint,
        Action,
        Action_SaleLine,
        Action_InvoiceLine,
        Configuration,
        Sale,
        module='sale_complaint', type_='model')
