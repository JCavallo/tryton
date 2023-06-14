# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import os
import binascii

from trytond.pool import PoolMeta
from trytond.model import ModelSQL, ModelView, fields, Unique

__all__ = [
    'Token',
    ]


class Token(ModelSQL, ModelView, metaclass=PoolMeta):
    'API Token'

    __name__ = 'api.token'

    active = fields.Boolean('Active')
    name = fields.Char('Name', required=True)
    key = fields.Char('Key', required=True)
    user = fields.Many2One('res.user', 'User', required=True)
    party = fields.Many2One('party.party', 'Party')

    @classmethod
    def __setup__(cls):
        super(Token, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [('token_uniq_key', Unique(t, t.key),
                'api_token.msg_token_uniq_key')]
        cls._buttons.update({
                'generate_key': {},
                })

    @classmethod
    def default_active(cls):
        return True

    @classmethod
    def default_key(cls):
        return binascii.hexlify(os.urandom(24)).decode('utf-8')

    @classmethod
    def check(cls, key):
        tokens = cls.search([('key', '=', key)])
        if tokens:
            token = tokens[0]
            return token.user.id, token.party.id if token.party else None
        else:
            return None, None

    @ModelView.button_change('key')
    def generate_key(self):
        self.key = self.__class__.default_key()

    @fields.depends('user', '_parent_user.name', 'party', 'name')
    def on_change_with_name(self):
        if self.name:
            return self.name
        if self.user:
            return self.user.name
        if self.party:
            return self.party.rec_name
