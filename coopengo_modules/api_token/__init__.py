# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.pool import Pool
from . import token
from . import res


def register():
    Pool.register(
        token.Token,
        res.User,
        module='api_token', type_='model')
