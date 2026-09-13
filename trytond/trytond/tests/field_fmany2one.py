# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

from trytond.model import ModelSQL, Unique, fields
from trytond.pool import Pool


class FMany2OneTarget(ModelSQL):
    __name__ = 'test.fmany2one_target'

    name = fields.Char("Name")
    children = fields.One2Many(
        'test.fmany2one_target.child', 'parent', "Children")

    @classmethod
    def __setup__(cls):
        super().__setup__()
        table = cls.__table__()
        cls._sql_constraints += [
            ('name_unique', Unique(table, table.name),
                "The name must be unique."),
            ]


_ParentMixin = fields.fmany2one(
            'parent', 'parent_name', 'test.fmany2one_target,name', "Parent")


class FMany2OneTargetChild(
        _ParentMixin,
        ModelSQL):
    __name__ = 'test.fmany2one_target.child'

    name = fields.Char("Name")
    parent_name = fields.Char("Parent Name")

    @classmethod
    def __setup__(cls):
        super().__setup__()
        table = cls.__table__()
        cls._sql_constraints += [
            ('name_parent_unique',
                Unique(table, table.name, table.parent_name),
                "The name and parent must be unique."),
            ]


_TargetMixin = fields.fmany2one(
            'target', 'target_name', 'test.fmany2one_target,name', "Target")
_ChildMixin = fields.fmany2one(
            'child', 'child_name,target_name',
            'test.fmany2one_target.child,name,parent_name', "Child")


class FMany2One(
        _TargetMixin,
        _ChildMixin,
        ModelSQL):
    __name__ = 'test.fmany2one'

    target_name = fields.Char("Target Name")
    child_name = fields.Char("Child Name")


_TargetMixin2 = fields.fmany2one(
            'target', 'target_name', 'test.fmany2one_target,name', "Target",
            required=True)


class FMany2OneRequired(
        _TargetMixin2,
        ModelSQL):
    __name__ = 'test.fmany2one_required'

    target_name = fields.Char("Target Name", required=True)


def register(module):
    Pool.register(
        FMany2OneTarget,
        FMany2OneTargetChild,
        FMany2One,
        FMany2OneRequired,
        module=module, type_='model')
