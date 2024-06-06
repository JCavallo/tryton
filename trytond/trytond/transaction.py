# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

import copy
import ipaddress
import logging
import time
from collections import defaultdict, deque
from functools import partial, wraps
from itertools import chain
from threading import local
from weakref import WeakValueDictionary

from sql import Flavor, For, Literal, Table

from trytond.config import config
from trytond.tools import grouped_slice, reduce_ids
from trytond.tools.immutabledict import ImmutableDict

__all__ = ['Transaction',
    'check_access', 'without_check_access',
    'active_records', 'inactive_records']

_retry = config.getint('database', 'retry')
_cache_transaction = config.getint('cache', 'transaction')
_cache_model = config.getint('cache', 'model')
_cache_record = config.getint('cache', 'record')
logger = logging.getLogger(__name__)


class TransactionError(Exception):
    def fix(self, extras):
        pass


class _TransactionLockError(TransactionError):
    def __init__(self, table):
        super().__init__()
        self._table = table

    def fix(self, extras):
        super().fix(extras)
        extras.setdefault('_lock_tables', []).append(self._table)


class _TransactionLockRecordsError(TransactionError):
    def __init__(self, table, ids):
        super().__init__()
        self._table = table
        self._ids = ids

    def fix(self, extras):
        super().fix(extras)
        extras.setdefault('_lock_records', {}).setdefault(
            self._table, []).extend(self._ids)


def record_cache_size(transaction):
    return transaction.context.get('_record_cache_size', _cache_record)


def check_access(func=None, *, _access=True):
    if func:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with check_access(_access=_access):
                return func(*args, **kwargs)
        return wrapper
    else:
        return Transaction().set_context(_check_access=_access)


def without_check_access(func=None):
    return check_access(func=func, _access=False)


def active_records(func=None, *, _test=True):
    if func:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with active_records(_test=_test):
                return func(*args, **kwargs)
        return wrapper
    else:
        return Transaction().set_context(active_test=_test)


def inactive_records(func=None):
    return active_records(func=func, _test=False)


class _AttributeManager(object):
    '''
    Manage Attribute of transaction
    '''

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __enter__(self):
        return Transaction()

    def __exit__(self, type, value, traceback):
        t = Transaction()
        for name, value in self.kwargs.items():
            setattr(t, name, value)


class _NoopManager(object):

    def __init__(self, transaction):
        self.transaction = transaction

    def __enter__(self):
        return self.transaction

    def __exit__(self, type, value, traceback):
        return


class SavepointManager:

    _count = 0

    def __init__(self, transaction, *, rollback_on=None, group=None):
        self.rollback_on = rollback_on
        self.name = f'sp-{id(transaction)}-{self._count}'
        self.__class__._count += 1
        self.previous_savepoint = transaction.current_savepoint
        self.transaction = transaction
        transaction.current_savepoint = self.name
        self.transaction.savepoints.append(self)

    def __enter__(self):
        self.transaction.database.savepoint(
            self.transaction.connection, self.name)
        return self

    def __exit__(self, type_, value, traceback):
        transaction_members = vars(Transaction)
        descriptors = [transaction_members[n] for n in (
                'log_records', 'create_records', 'delete_records',
                'trigger_records', 'check_warnings', '_atexit',
                '_datamanagers')]
        inner = self.transaction.current_savepoint
        inner_cache_key = self.transaction._cache_key()
        self.transaction.current_savepoint = outer = self.previous_savepoint
        outer_cache_key = self.transaction._cache_key()
        if type_ is None and value is None and traceback is None:
            for d in descriptors:
                d.merge(self.transaction, inner, outer)
            # since the outer cache is a deepcopy of the inner cache we can
            # safely replace the inner value by the outer value when releasing
            # the savepoint
            if outer_cache_key in self.transaction.cache:
                self.transaction.cache[inner_cache_key] = \
                    self.transaction.cache.pop(outer_cache_key)
            database = self.transaction.database
            database.savepoint_release(
                self.transaction.connection, self.name)
            self.transaction.savepoints.pop()
            return True
        elif ((isinstance(value, SavepointRollback)
                and value.name == self.name)
            or (self.rollback_on is not None
                and issubclass(type_, self.rollback_on))):
            database = self.transaction.database
            database.savepoint_rollback(
                self.transaction.connection, self.name)
            self.transaction.savepoints.pop()
            return True
        else:
            return False

    def rollback(self):
        raise SavepointRollback(self.name)


class SavepointRollback(Exception):

    def __init__(self, name=None):
        self.name = name


_MISSING_SAVEPOINT = object()


class SavepointAwareProperty:

    def __init__(self, factory):
        self.factory = factory

    def __set_name__(self, owner, name):
        self.public_name = name
        self.private_name = f'_sp_{name}'

    def __get__(self, obj, objtype=None):
        if not hasattr(obj, self.private_name):
            setattr(obj, self.private_name, {})
        store = getattr(obj, self.private_name)
        return store.setdefault(obj.current_savepoint, self.factory())

    def __set__(self, obj, value):
        if not hasattr(obj, self.private_name):
            setattr(obj, self.private_name, {})
        store = getattr(obj, self.private_name)
        store[obj.current_savepoint] = value

    def merge(self, transaction, from_, to):
        store = getattr(transaction, self.private_name, {})
        to_merge = store.pop(from_, _MISSING_SAVEPOINT)
        if to_merge is not _MISSING_SAVEPOINT:
            new_value = store.setdefault(to, self.factory())
            if isinstance(new_value, list):
                new_value += to_merge
            elif isinstance(new_value, (dict, set)):
                new_value.update(to_merge)
            else:
                raise TypeError


def with_savepoint(*, rollback_on=Exception):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with Transaction().savepoint(rollback_on=rollback_on):
                return func(*args, **kwargs)
        return wrapper
    return decorator


class _Local(local):

    def __init__(self):
        # Transaction stack control
        self.transactions = []
        self.tasks = []


class Transaction(object):
    '''
    Control the transaction
    '''

    _local = _Local()

    log_records = SavepointAwareProperty(list)
    create_records = SavepointAwareProperty(partial(defaultdict, set))
    delete_records = SavepointAwareProperty(partial(defaultdict, set))
    trigger_records = SavepointAwareProperty(partial(defaultdict, set))
    check_warnings = SavepointAwareProperty(partial(defaultdict, set))
    _atexit = SavepointAwareProperty(list)
    _datamanagers = SavepointAwareProperty(list)

    cache_keys = {
        'language', 'fuzzy_translation', '_datetime', '_datetime_exclude',
        }

    def __new__(cls, new=False):
        transactions = cls._local.transactions
        if new or not transactions:
            instance = super().__new__(cls)
            instance.database = None
            instance.readonly = False
            instance.connection = None
            instance.close = None
            instance.user = None
            instance.context = None
            instance.current_savepoint = None
            instance.savepoints = []
            instance.timestamp = None
            instance.started_at = None
            instance.coog_cache = None
            instance.cache = WeakValueDictionary()
            instance._cache_deque = deque(maxlen=_cache_transaction)
            transactions.append(instance)
        else:
            instance = transactions[-1]
        return instance

    @staticmethod
    def monotonic_time():
        try:
            return time.monotonic_ns()
        except AttributeError:
            return time.monotonic()

    @property
    def tasks(self):
        return self._local.tasks

    def _cache_key(self):
        keys = tuple(((key, self.context[key])
                for key in sorted(self.cache_keys)
                if key in self.context))
        return (self.current_savepoint, self.user, keys)

    def get_cache(self):
        from trytond.cache import LRUDict
        from trytond.pool import Pool
        cache = self.cache.setdefault(
            self._cache_key(),
            LRUDict(
                _cache_model,
                lambda name: LRUDict(
                    record_cache_size(self),
                    Pool().get(name)._record),
                default_factory_with_key=True))
        # Keep last used cache references to allow to pre-fill them
        self._cache_deque.append(cache)
        return cache

    def start(self, database_name, user, readonly=False, context=None,
            close=False, autocommit=False, timeout=None, **extras):
        '''
        Start transaction
        '''
        try:
            from trytond import backend
            assert self.user is None
            assert self.database is None
            assert self.close is None
            assert self.context is None
            # Compute started_at before connect to ensure
            # it is strictly before all transactions started after
            # but it may be also before transactions started before
            self.started_at = self.monotonic_time()
            if not database_name:
                database = backend.Database().connect()
            else:
                database = backend.Database(database_name).connect()
            Flavor.set(backend.Database.flavor)
            self.user = user
            self.database = database
            self.readonly = readonly
            self.close = close
            self.context = ImmutableDict(context or {})
            self.current_savepoint = None
            self.timestamp = {}
            self.counter = 0
            self._sub_transactions = []
            self._sub_transactions_to_close = []

            self.connection = database.get_connection(readonly=readonly,
                autocommit=autocommit, statement_timeout=timeout)
            count = 0
            while True:
                if count:
                    time.sleep(0.02 * (_retry - count))
                try:
                    lock_tables = extras.get('_lock_tables', [])
                    for table in lock_tables:
                        self.database.lock(self.connection, table)
                    self._locked_tables = set(lock_tables)
                    locked_records = defaultdict(set)
                    for table, ids in extras.get('_lock_records', {}).items():
                        self.database.lock_records(self.connection, table, ids)
                        locked_records[table].update(ids)
                    self._locked_records = locked_records
                except backend.DatabaseOperationalError:
                    if count < _retry:
                        self.connection.rollback()
                        count += 1
                        logger.debug("Retry: %i", count)
                        continue
                    raise
                break
            if database_name:
                from trytond.cache import Cache
                Cache.sync(self)
        except BaseException:
            self.stop(False)
            raise
        return self

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.stop(type is None)

    def stop(self, commit=False):
        from trytond import backend
        transactions = self._local.transactions
        try:
            if transactions.count(self) == 1:
                try:
                    try:
                        if commit and not self.readonly:
                            self.commit()
                        else:
                            self.rollback()
                    finally:
                        if self.connection:
                            self.database.put_connection(
                                self.connection, self.close)
                            to_put = {x.connection for x in
                                self._sub_transactions_to_close
                                if (backend.name == 'sqlite'
                                    or not x.connection.closed)}
                            for conn in to_put:
                                self.database.put_connection(
                                    conn, self.close)
                finally:
                    self.database = None
                    self.readonly = False
                    self.connection = None
                    self.close = None
                    self.user = None
                    self.context = None
                    self.current_savepoint = None
                    self.savepoints = []
                    self.timestamp = None

                for func, args, kwargs in self._atexit:
                    func(*args, **kwargs)
        finally:
            transactions.reverse()
            try:
                transactions.remove(self)
            finally:
                transactions.reverse()

    def set_context(self, context=None, **kwargs):
        if context is None:
            context = {}
        if not context and not kwargs:
            manager = _NoopManager(self)
        else:
            manager = _AttributeManager(context=self.context)
            ctx = self.context.copy()
            ctx.update(context)
            if kwargs:
                ctx.update(kwargs)
            self.context = ImmutableDict(ctx)
        return manager

    def reset_context(self):
        manager = _AttributeManager(context=self.context)
        self.context = ImmutableDict()
        return manager

    def set_user(self, user, set_context=False):
        if user != 0 and set_context:
            raise ValueError('set_context only allowed for root')
        manager = _AttributeManager(user=self.user,
                context=self.context)
        ctx = self.context.copy()
        if set_context:
            if user != self.user:
                ctx['user'] = self.user
        else:
            ctx.pop('user', None)
        self.context = ImmutableDict(ctx)
        self.user = user
        return manager

    def lock_table(self, table):
        # JCA (merge 6.8): restore previous behaviour until inlined commits can
        # be managed
        self.database.lock(self.connection, table)
        # if table not in self._locked_tables:
        #     raise _TransactionLockError(table)

    def lock_records(self, table, ids):
        if self.database.has_select_for():
            table = Table(table)
            for sub_records in grouped_slice(ids):
                where = reduce_ids(table.id, sub_records)
                query = table.select(
                    Literal(1), where=where, for_=For('UPDATE', nowait=True))
                with self.connection.cursor() as cursor:
                    cursor.execute(*query)

    def set_current_transaction(self, transaction):
        self._local.transactions.append(transaction)
        return transaction

    def new_transaction(self, autocommit=False, readonly=False, **extras):
        transaction = Transaction(new=True)
        return transaction.start(self.database.name, self.user,
            context=self.context, close=self.close, readonly=readonly,
            autocommit=autocommit, **extras)

    def _store_log_records(self):
        from trytond.pool import Pool
        if self.log_records:
            pool = Pool()
            Log = pool.get('ir.model.log')
            with without_check_access():
                Log.save(self.log_records)
        self._clear_log_records()

    def _clear_log_records(self):
        if self.log_records:
            self.log_records.clear()

    def _remove_warnings(self):
        from trytond.pool import Pool
        if self.check_warnings:
            pool = Pool()
            Warning_ = pool.get('res.user.warning')
            with without_check_access():
                warnings = Warning_.browse(
                    chain.from_iterable(self.check_warnings.values()))
                Warning_.delete(warnings)
        self._clear_warnings()

    def _clear_warnings(self):
        self.check_warnings.clear()

    def add_sub_transactions(self, sub_transactions):
        self._sub_transactions.extend(sub_transactions)

    def add_sub_transaction_to_close(self, sub_transaction):
        # Needed by sub_transaction_retry Coog decorator
        # We need to close connection that will not
        # be committed to prevent depletion of
        # the connection pool.
        self._sub_transactions_to_close.append(sub_transaction)

    def commit(self):
        assert self.current_savepoint is None

        from trytond.cache import Cache
        try:
            self._store_log_records()
            self._remove_warnings()
            if self._datamanagers:
                for datamanager in self._datamanagers:
                    datamanager.tpc_begin(self)
                for datamanager in self._datamanagers:
                    datamanager.commit(self)
                for datamanager in self._datamanagers:
                    datamanager.tpc_vote(self)
            # ABD: Some datamanager may returns transactions which should
            # be committed just before the main transaction
            for sub_transaction in self._sub_transactions:
                # Does not handle TPC or recursive transaction commit
                # This just commits the sub transactions to avoid any crashes
                # which could occur otherwise.
                sub_transaction.connection.commit()
            self.started_at = self.monotonic_time()
            for cache in self.cache.values():
                cache.clear()
            if self.coog_cache:
                self.coog_cache.clear()
            Cache.commit(self)
            self.connection.commit()
        except Exception:
            self.rollback()
            raise
        else:
            try:
                for datamanager in self._datamanagers:
                    datamanager.tpc_finish(self)
            except Exception:
                logger.critical('A datamanager raised an exception in'
                    ' tpc_finish, the data might be inconsistant',
                    exc_info=True)

    def rollback(self):
        from trytond.cache import Cache
        for cache in self.cache.values():
            cache.clear()
        if self.coog_cache:
            self.coog_cache.clear()
        for sub_transaction in self._sub_transactions:
            sub_transaction.rollback()
        for datamanager in self._datamanagers:
            datamanager.tpc_abort(self)
        Cache.rollback(self)
        self._clear_log_records()
        self._clear_warnings()
        if self.connection:
            self.connection.rollback()

    def savepoint(self, *, rollback_on=None):
        previous_cache = self.get_cache()
        savepoint = SavepointManager(self, rollback_on=rollback_on)
        current_cache = self.get_cache()
        current_cache.update(copy.deepcopy(previous_cache))
        return savepoint

    def join(self, datamanager):
        try:
            idx = self._datamanagers.index(datamanager)
            return self._datamanagers[idx]
        except ValueError:
            self._datamanagers.append(datamanager)
            return datamanager

    def atexit(self, func, *args, **kwargs):
        self._atexit.append((func, args, kwargs))

    @property
    def language(self):
        def get_language():
            from trytond.pool import Pool
            Config = Pool().get('ir.configuration')
            return Config.get_language()
        if self.context:
            return self.context.get('language') or get_language()
        return get_language()

    def remote_address(self):
        ip_address = ip_network = None
        if self.context.get('_request') and (
                remote_addr := self.context['_request'].get('remote_addr')):
            ip_address = ipaddress.ip_address(remote_addr)
            prefix = config.getint(
                'session', f'ip_network_{ip_address.version}')
            ip_network = ipaddress.ip_network(remote_addr)
            ip_network = ip_network.supernet(new_prefix=prefix)
        return ip_address, ip_network

    @property
    def check_access(self):
        return self.context.get('_check_access', False)

    @property
    def active_records(self):
        return self.context.get('active_test', True)
