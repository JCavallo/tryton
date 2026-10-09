# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

from collections import defaultdict
from typing import Any, Literal, Self, overload

from sql.conditionals import Coalesce

from trytond.i18n import gettext, lazy_gettext
from trytond.model import Index, ModelSQL, ModelStorage, ModelView, fields
from trytond.model.exceptions import AccessError
from trytond.pool import Pool
from trytond.pyson import Eval
from trytond.tools.domain_inversion import is_leaf
from trytond.transaction import Transaction, without_check_access

__all__ = ['ResourceAccessMixin', 'ResourceMixin', 'resource_copy']


class ResourceAccessMixin(ModelStorage):

    resource = fields.Reference(
        "Resource", selection='get_models', required=True)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        if issubclass(cls, ModelSQL):
            table = cls.__table__()
            cls._sql_indexes.add(
                Index(table, (table.resource, Index.Similarity(begin=True))))

    @classmethod
    def default_resource(cls):
        return Transaction().context.get('resource')

    @staticmethod
    def get_models():
        pool = Pool()
        Model = pool.get('ir.model')
        ModelAccess = pool.get('ir.model.access')
        models = Model.get_name_items((ModelStorage, ModelView))
        if Transaction().check_access:
            access = ModelAccess.get_access([m for m, _ in models])
            models = [(m, n) for m, n in models if access[m]['read']]
        return models

    @classmethod
    def check_access(cls, ids, mode='read'):
        pool = Pool()
        ModelAccess = pool.get('ir.model.access')
        Rule = pool.get('ir.rule')
        transaction = Transaction()
        if transaction.user == 0 or not transaction.check_access:
            return
        records = defaultdict(set)
        with without_check_access():
            for record in cls.browse(ids):
                if record.resource:
                    records[record.resource.__name__].add(record.resource.id)
        for model_name, ids in records.items():
            checks = cls._convert_check_access(model_name, mode)
            for model_name, check_mode in checks:
                ModelAccess.check(model_name, mode=check_mode)
                Rule.check(model_name, ids, mode=check_mode)

    @classmethod
    def _convert_check_access(cls, model, mode):
        return [
            (model, {'create': 'write', 'delete': 'write'}.get(mode, mode))]

    @classmethod
    def check_search_access(cls, domain):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        ModelAccess = pool.get('ir.model.access')
        Rule = pool.get('ir.rule')
        User = pool.get('res.user')

        def check_ressource_in_domain(domain):
            if not domain:
                return False
            elif domain[0] == 'OR':
                return False
            elif domain[0] == 'AND':
                return check_ressource_in_domain(domain[1:])
            elif is_leaf(domain):
                return False

            for expr in domain:
                match expr:
                    case ('resource', '=', resource):
                        model, id_ = resource.split(',', 1)
                        id_ = int(id_)
                        ModelAccess.check(model, mode='read')
                        Rule.check(model, [id_], mode='read')
                        return True
                    case ('resource', 'in', resources):
                        models = defaultdict(list)
                        for resource in resources:
                            if isinstance(resource, str):
                                model, id_ = resource.split(',', 1)
                                id_ = int(id_)
                            else:
                                model = resource.__name__
                                id_ = resource.id
                            models[model].append(id_)
                        for model, ids in models.items():
                            ModelAccess.check(model, mode='read')
                            Rule.check(model, ids, mode='read')
                        return True
                    case _:
                        if check_ressource_in_domain(expr):
                            return True
            return False

        user_groups = {g.id for g in User(Transaction().user).groups}
        admin_group = ModelData.get_id('res', 'group_admin')
        if (Transaction().check_access
                and admin_group not in user_groups
                and not check_ressource_in_domain(domain)):
            raise AccessError(gettext(
                    'ir.msg_access_resource_search_error',
                    resource=cls.__name__))

    # Same overload set as ModelStorage.search: the **kwargs implementation
    # alone hides the query parameter, which mypy then reports as an
    # incompatible "search" for every ResourceAccessMixin + ModelSQL class
    # (mason-3a1.148).
    @overload
    @classmethod
    def search(
            cls, domain, offset=0, limit=None, order=None,
            count: Literal[False] = ..., query: Literal[False] = ...,
            ) -> list[Self]: ...

    @overload
    @classmethod
    def search(
            cls, domain, offset=0, limit=None, order=None,
            count: Literal[True] = ..., query: Literal[False] = ...,
            ) -> int: ...

    @overload
    @classmethod
    def search(
            cls, domain, offset=0, limit=None, order=None,
            count: bool = ..., query: Literal[True] = ...) -> Any: ...

    @overload
    @classmethod
    def search(
            cls, domain, offset=0, limit=None, order=None,
            count: bool = ..., query: bool = ...) -> Any: ...

    @classmethod
    def search(
            cls, domain, offset=0, limit=None, order=None, count=False,
            **kwargs):
        cls.check_search_access(domain)
        return super().search(
            domain, offset=offset, limit=limit, order=order, count=count,
            **kwargs)

    @classmethod
    def read(cls, ids, fields_names):
        cls.check_access(ids, mode='read')
        return super().read(ids, fields_names)

    @classmethod
    def delete(cls, records):
        cls.check_access([a.id for a in records], mode='delete')
        super().delete(records)

    @classmethod
    def write(cls, records, values, *args):
        all_ids = []
        actions = iter((records, values) + args)
        for other_records, _ in zip(actions, actions):
            all_ids.extend(r.id for r in other_records)
        cls.check_access(all_ids, mode='write')
        super().write(records, values, *args)
        cls.check_access(all_ids, mode='write')

    @classmethod
    def create(cls, vlist):
        records = super().create(vlist)
        cls.check_access([r.id for r in records], mode='create')
        return records


class ResourceMixin(ResourceAccessMixin, ModelStorage, ModelView):

    copy_to_resources = fields.MultiSelection(
        'get_copy_to_resources', "Copy to Resources",
        states={
            'invisible': ~Eval('copy_to_resources_visible'),
            },
        depends=['copy_to_resources_visible'])
    copy_to_resources_visible = fields.Function(
        fields.Boolean("Copy to Resources Visible"),
        'on_change_with_copy_to_resources_visible')
    last_user = fields.Function(fields.Char('Last User',
            states={
                'invisible': ~Eval('last_user'),
                }),
        'get_last_user')
    last_modification = fields.Function(fields.DateTime('Last Modification',
            states={
                'invisible': ~Eval('last_modification'),
                }),
        'get_last_modification')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('last_modification', 'DESC'))
        cls.resource.required = True

    @fields.depends('resource')
    def get_copy_to_resources(self):
        pool = Pool()
        Model = pool.get('ir.model')
        resources = []
        if isinstance(self.resource, ResourceCopyMixin):
            models = self.resource.get_resources_to_copy(self.__name__)
            resources.extend((m, Model.get_name(m)) for m in models)
        return resources

    @fields.depends(methods=['get_copy_to_resources'])
    def on_change_with_copy_to_resources_visible(self, name=None):
        return bool(self.get_copy_to_resources())

    def get_last_user(self, name):
        return (self.write_uid.rec_name if self.write_uid
            else self.create_uid.rec_name)

    def get_last_modification(self, name):
        return (self.write_date if self.write_date else self.create_date
            ).replace(microsecond=0)

    @staticmethod
    def order_last_modification(tables):
        table, _ = tables[None]
        return [Coalesce(table.write_date, table.create_date)]


class ResourceCopyMixin(ModelStorage):

    @classmethod
    def get_resources_to_copy(cls, name):
        return set()


def resource_copy(resource, name, string):

    class _ResourceCopyMixin(ResourceCopyMixin):

        @classmethod
        def copy(cls, records, default=None):
            if default is None:
                default = {}
            else:
                default = default.copy()
            default.setdefault(name, None)
            return super().copy(records, default=default)

        def copy_resources_to(self, target):
            pool = Pool()
            Resource = pool.get(resource)

            try:
                super().copy_resources_to(target)
            except AttributeError:
                pass

            to_copy = []
            for record in getattr(self, name):
                if (record.copy_to_resources
                        and target.__name__ in record.copy_to_resources):
                    to_copy.append(record)
            if to_copy:
                return Resource.copy(to_copy, default={
                        'resource': str(target),
                        'copy_to_resources': None,
                        })

    setattr(_ResourceCopyMixin, name, fields.One2Many(
            resource, 'resource', string,
            help=lazy_gettext('ir.msg_resource_copy_help')))
    return _ResourceCopyMixin
