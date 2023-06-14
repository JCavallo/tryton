# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.tests.test_tryton import ModuleTestCase


class APITokenTestCase(ModuleTestCase):
    'Test API Token module'
    module = 'api_token'


del ModuleTestCase
