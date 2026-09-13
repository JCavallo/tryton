# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

from trytond.model import avatar_mixin
from trytond.pool import PoolMeta


_AvatarMixin = avatar_mixin(200, 'name')


class Party(_AvatarMixin, metaclass=PoolMeta):
    __name__ = 'party.party'
