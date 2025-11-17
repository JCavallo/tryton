# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

from trytond.model import ModelSQL, fields
from trytond.pool import Pool
from trytond.transaction import with_savepoint


class Savepoint(ModelSQL):
    __name__ = 'test.savepoint'

    value = fields.Integer("Value")


class SavepointLogging(ModelSQL):
    __name__ = 'test.savepoint.logging'

    value = fields.Integer("Value")

    @classmethod
    def new(cls, value):
        sp = Savepoint(value=value)
        sp.save()
        sp.log('write', f'{value}')


class SavepointCacheRead(ModelSQL):
    __name__ = 'test.savepoint.cache_read'

    value = fields.Integer("Value")


class SavepointDecorator(ModelSQL):
    __name__ = 'test.savepoint.decorator'

    value = fields.Integer("Value")

    @classmethod
    @with_savepoint()
    def method(cls, value, exception=None):
        sp = cls(value=value)
        sp.save()
        if exception:
            raise exception

    @classmethod
    @with_savepoint(rollback_on=(KeyError, ZeroDivisionError))
    def method_w_exception(cls, value, exception=None):
        sp = cls(value=value)
        sp.save()
        if exception:
            raise exception


def register(module):
    Pool.register(
        Savepoint,
        SavepointLogging,
        SavepointCacheRead,
        SavepointDecorator,
        module=module, type_='model')
