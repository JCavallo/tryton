# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

from trytond.model import ModelSQL, fields, tree
from trytond.pool import Pool


_TreeMixin = tree(separator=' / ')


class Tree(_TreeMixin, ModelSQL):
    __name__ = 'test.tree'
    name = fields.Char("Name")
    parent = fields.Many2One('test.tree', "Parent")


_TreeMixin2 = tree(separator='\\')


class TreeWildcard(_TreeMixin2, ModelSQL):
    __name__ = 'test.tree_wildcard'
    name = fields.Char("Name")
    parent = fields.Many2One('test.tree_wildcard', "Parent")


_TreeMixin3 = tree(parent='parents')


class Polytree(_TreeMixin3, ModelSQL):
    __name__ = 'test.polytree'
    name = fields.Char("Name")
    parents = fields.Many2Many(
        'test.polytree.edge', 'parent', 'child', "Parents")


class PolytreeEdge(ModelSQL):
    __name__ = 'test.polytree.edge'
    parent = fields.Many2One('test.polytree', "Parent")
    child = fields.Many2One('test.polytree', "Child")


def register(module):
    Pool.register(
        Tree,
        TreeWildcard,
        Polytree,
        PolytreeEdge,
        module=module, type_='model')
