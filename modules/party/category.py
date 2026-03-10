# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from sql.conditionals import Coalesce
from sql.operators import Equal

from trytond.model import (
    DeactivableMixin, Exclude, ModelSQL, ModelView, fields, tree)

SEPARATOR = ' / '


class Category(DeactivableMixin, tree(separator=' / '), ModelSQL, ModelView):
    __name__ = 'party.category'
    name = fields.Char(
        "Name", required=True, translate=True,
        help="The main identifier of the category.")
    parent = fields.Many2One(
        'party.category', "Parent",
        help="Add the category below the parent.")
    childs = fields.One2Many(
        'party.category', 'parent', "Children",
        help="Add children below the category.")

    @classmethod
    def __setup__(cls):
        super().__setup__()
        t = cls.__table__()
        cls._sql_constraints = [
            ('name_parent_exclude',
                Exclude(t, (t.name, Equal), (Coalesce(t.parent, -1), Equal)),
                'party.msg_category_name_unique'),
            ]
        cls._order.insert(0, ('name', 'ASC'))

    @classmethod
    def validate(cls, categories):
        super(Category, cls).validate(categories)
        cls.check_recursion(categories)

    def get_rec_name(self, name):
        if self.parent:
            return self.parent.get_rec_name(name) + SEPARATOR + self.name
        return self.name

    @classmethod
    def search_rec_name(cls, name, clause):
        if isinstance(clause[2], str):
            values = clause[2].split(SEPARATOR)
            values.reverse()
            domain = []
            field = 'name'
            for name in values:
                domain.append((field, clause[1], name))
                field = 'parent.' + field
            return domain
        # TODO Handle list
        return [('name',) + tuple(clause[1:])]
