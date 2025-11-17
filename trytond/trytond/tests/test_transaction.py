# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest
from unittest.mock import Mock

from trytond import backend
from trytond.pool import Pool
from trytond.tests.test_tryton import (
    CONTEXT, DB_NAME, USER, TestCase, activate_module, with_transaction)
from trytond.transaction import (
    SavepointAwareProperty, SavepointRollback, Transaction)


def empty_transaction(*args, **kwargs):
    '''
    Just starts a transaction in the context manager and returns `True`
    and stops transaction for the given arguments.

    All positional arguments are passed to `start` method of transaction
    '''
    with Transaction().start(*args, **kwargs):
        return True


class TransactionTestCase(TestCase):
    'Test the Transaction Context manager'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        activate_module('tests')

    def test_nonexistdb(self):
        '''Attempt opening a transaction with a non existant DB
        and ensure that it stops cleanly and allows starting of next
        transaction'''
        self.assertRaises(
            Exception, empty_transaction, "Non existant DB", USER,
            context=CONTEXT)
        self.assertTrue(empty_transaction(DB_NAME, USER, context=CONTEXT))

    def test_set_user(self):
        'Test set_user'
        with Transaction().start(DB_NAME, USER, context=CONTEXT) \
                as transaction:
            self.assertEqual(transaction.user, USER)
            self.assertEqual(transaction.context.get('user'), None)

            with Transaction().set_user(0):
                self.assertEqual(transaction.user, 0)
                self.assertEqual(transaction.context.get('user'), None)

            with Transaction().set_user(0, set_context=True):
                self.assertEqual(transaction.user, 0)
                self.assertEqual(transaction.context.get('user'), USER)

                # Nested same set_user should keep original context user
                with Transaction().set_user(0, set_context=True):
                    self.assertEqual(transaction.user, 0)
                    self.assertEqual(transaction.context.get('user'), USER)

                # Unset user context
                with Transaction().set_user(0, set_context=False):
                    self.assertEqual(transaction.user, 0)
                    self.assertEqual(transaction.context.get('user'), None)

            # set context for non root
            self.assertRaises(ValueError,
                Transaction().set_user, 2, set_context=True)

            # not set context for non root
            with Transaction().set_user(2):
                self.assertEqual(transaction.user, 2)

    def test_stacked_transactions(self):
        'Test that transactions are stacked / unstacked correctly'
        with Transaction().start(DB_NAME, USER, context=CONTEXT) \
                as transaction:
            with transaction.new_transaction() as new_transaction:
                self.assertIsNot(new_transaction, transaction)
                self.assertIsNot(Transaction(), transaction)
                self.assertIs(Transaction(), new_transaction)
            self.assertIs(Transaction(), transaction)

    def test_two_phase_commit(self):
        # A successful transaction
        dm = Mock()
        with Transaction().start(DB_NAME, USER, context=CONTEXT) \
                as transaction:
            transaction.join(dm)

        dm.tpc_begin.assert_called_once_with(transaction)
        dm.commit.assert_called_once_with(transaction)
        dm.tpc_vote.assert_called_once_with(transaction)
        dm.tpc_abort.assert_not_called()
        dm.tpc_finish.assert_called_once_with(transaction)

        # Failing in the datamanager
        dm.reset_mock()
        dm.tpc_vote.side_effect = ValueError('Failing the datamanager')
        try:
            with Transaction().start(DB_NAME, USER, context=CONTEXT) \
                    as transaction:
                transaction.join(dm)
        except ValueError:
            pass

        dm.tpc_begin.assert_called_once_with(transaction)
        dm.commit.assert_called_once_with(transaction)
        dm.tpc_vote.assert_called_once_with(transaction)
        dm.tpc_abort.assert_called_once_with(transaction)
        dm.tpc_finish.assert_not_called()

        # Failing in tryton
        dm.reset_mock()
        try:
            with Transaction().start(DB_NAME, USER, context=CONTEXT) \
                    as transaction:
                transaction.join(dm)
                raise ValueError('Failing in tryton')
        except ValueError:
            pass

        dm.tpc_begin.assert_not_called()
        dm.commit.assert_not_called()
        dm.tpc_vote.assert_not_called()
        dm.tpc_abort.assert_called_once_with(transaction)
        dm.tpc_finish.assert_not_called()

    @unittest.skipUnless(backend.name == 'postgresql', "Test pg_settings")
    def test_postgresl_statement_timeout(self):
        get_timeout = (
            "SELECT setting FROM pg_settings "
            "WHERE name='statement_timeout'")

        with Transaction().start(DB_NAME, USER) as transaction:
            cursor = transaction.connection.cursor()
            cursor.execute(get_timeout)
            self.assertEqual('0', cursor.fetchone()[0])

        with Transaction().start(DB_NAME, USER, timeout=1) as transaction:
            cursor = transaction.connection.cursor()
            cursor.execute(get_timeout)
            self.assertEqual('1000', cursor.fetchone()[0])

    @unittest.skipUnless(backend.name == 'postgresql', "Use pg_sleep")
    def test_postgresql_statement_timeout_exception(self):
        with self.assertRaises(backend.DatabaseTimeoutError):
            with Transaction().start(DB_NAME, USER, timeout=1) as transaction:
                cursor = transaction.connection.cursor()
                cursor.execute("SELECT pg_sleep(2)")

    def test_remote_address(self):
        "Test remote address"
        for remote_addr, (ip_address, ip_network) in [
                ('192.168.0.10', ('192.168.0.10', '192.168.0.10/32')),
                ('64:ff9b:1::', ('64:ff9b:1::', '64:ff9b:1::/56')),
                ]:
            with self.subTest(remote_addr=remote_addr):
                with Transaction().start(DB_NAME, USER, context={
                            '_request': {
                                'remote_addr': remote_addr,
                                },
                            }) as transaction:
                    self.assertEqual(
                        tuple(map(str, transaction.remote_address())),
                        (ip_address, ip_network))

        with Transaction().start(DB_NAME, USER) as transaction:
            self.assertEqual(transaction.remote_address(), (None, None))


class SavepointTestCase(TestCase):
    'Test Savepoint context manager and decorator'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        activate_module('tests')

    def test_savepointawareproperty(self):
        "Test SavepointAwareProperty"

        class Transaction:
            p_list = SavepointAwareProperty(list)

            def __init__(self):
                self._sp_p_list = {}
                self.current_savepoint = 'foo'

        transaction = Transaction()
        self.assertEqual(transaction.p_list, [])

        transaction.p_list = [1, 2, 3]
        self.assertEqual(transaction.p_list, [1, 2, 3])

    def test_savepointawareproperty_change_savepoint(self):
        "Test SavepointAwareProperty when changing the savepoint"

        class Transaction:
            p_list = SavepointAwareProperty(list)

            def __init__(self):
                self._sp_p_list = {}
                self.current_savepoint = 'foo'

        transaction = Transaction()
        transaction.p_list = [1, 2, 3]

        transaction.current_savepoint = 'bar'
        transaction.p_list = ['a', 'b', 'c']

        transaction.current_savepoint = 'foo'
        self.assertEqual(transaction.p_list, [1, 2, 3])

        transaction.current_savepoint = 'bar'
        self.assertEqual(transaction.p_list, ['a', 'b', 'c'])

    def test_savepointawareproperty_merge(self):
        "Test SavepointAwareProperty merging"

        class Transaction:
            p_list = SavepointAwareProperty(list)
            p_dict = SavepointAwareProperty(dict)
            p_set = SavepointAwareProperty(set)

            def __init__(self):
                self._sp_p_list = {}
                self._sp_p_dict = {}
                self._sp_p_set = {}
                self.current_savepoint = 'foo'

        transaction = Transaction()
        transaction.p_list = [1, 2, 3]
        transaction.p_dict = {1: 'a', 2: 'b', 3: 'c'}
        transaction.p_set = set('abc')

        transaction.current_savepoint = 'bar'
        transaction.p_list = [4, 5, 6]
        transaction.p_dict = {4: 'd', 5: 'e', 6: 'f'}
        transaction.p_set = set('def')

        transaction_members = vars(Transaction)
        p_list = transaction_members['p_list']
        p_dict = transaction_members['p_dict']
        p_set = transaction_members['p_set']

        transaction.current_savepoint = 'foo'

        p_list.merge(transaction, 'bar', 'foo')
        self.assertEqual(transaction.p_list, [1, 2, 3, 4, 5, 6])
        p_dict.merge(transaction, 'bar', 'foo')
        self.assertEqual(
            transaction.p_dict,
            {1: 'a', 2: 'b', 3: 'c', 4: 'd', 5: 'e', 6: 'f'})
        p_set.merge(transaction, 'bar', 'foo')
        self.assertEqual(transaction.p_set, set('abcdef'))

    def test_release(self):
        "Test savepoint release"

        with Transaction().start(DB_NAME, USER):
            pool = Pool()
            Model = pool.get('test.savepoint')

            record = Model(value=1)
            record.save()
            record_id = record.id
            with Transaction().savepoint():
                record = Model(record_id)
                record.value = 2
                record.save()

        with Transaction().start(DB_NAME, USER):
            pool = Pool()
            Model = pool.get('test.savepoint')
            record = Model(record_id)
            self.assertEqual(record.value, 2)

    def test_rollback(self):
        "Test savepoint rollback"

        with Transaction().start(DB_NAME, USER):
            pool = Pool()
            Model = pool.get('test.savepoint')

            record = Model(value=1)
            record.save()
            record_id = record.id
            with Transaction().savepoint():
                record = Model(record_id)
                record.value = 2
                record.save()
                with Transaction().savepoint():
                    record = Model(record_id)
                    record.value = 3
                    record.save()
                    with Transaction().savepoint() as sp:
                        record = Model(record_id)
                        record.value = 4
                        record.save()
                        sp.rollback()

        with Transaction().start(DB_NAME, USER):
            pool = Pool()
            Model = pool.get('test.savepoint')
            record = Model(record_id)
            self.assertEqual(record.value, 3)

    def test_named_rollback(self):
        "Test rollbacking a named savepoint"
        with Transaction().start(DB_NAME, USER):
            pool = Pool()
            Model = pool.get('test.savepoint')

            record = Model(value=1)
            record.save()
            record_id = record.id
            with Transaction().savepoint():
                record = Model(record_id)
                record.value = 2
                record.save()
                with Transaction().savepoint() as sp:
                    record = Model(record_id)
                    record.value = 3
                    record.save()
                    with Transaction().savepoint():
                        record = Model(record_id)
                        record.value = 4
                        record.save()
                        raise SavepointRollback(name=sp.name)

        with Transaction().start(DB_NAME, USER):
            pool = Pool()
            Model = pool.get('test.savepoint')
            record = Model(record_id)
            self.assertEqual(record.value, 2)

    def test_context_manager_with_exception(self):
        "Test using a context manager rollbacking on some exceptions"
        with Transaction().start(DB_NAME, USER):
            pool = Pool()
            Model = pool.get('test.savepoint')

            record = Model(value=1)
            record.save()
            record_id = record.id

            with Transaction().savepoint(rollback_on=KeyError):
                record = Model(record_id)
                record.value = 2
                record.save()
                raise KeyError

        with Transaction().start(DB_NAME, USER):
            pool = Pool()
            Model = pool.get('test.savepoint')
            record = Model(record_id)
            self.assertEqual(record.value, 1)

    def test_rollback_ir_log(self):
        "Test rollbacking a named savepoint when ir.log are involved"

        with Transaction().start(DB_NAME, USER):
            pool = Pool()
            Model = pool.get('test.savepoint.logging')

            Model.new(1)
            with Transaction().savepoint():
                Model.new(2)
                with Transaction().savepoint() as sp:
                    Model.new(3)
                    with Transaction().savepoint():
                        Model.new(4)
                        sp.rollback()

        with Transaction().start(DB_NAME, USER):
            pool = Pool()
            Log = pool.get('ir.model.log')

            logs = Log.search([
                    ('event', '=', 'write'),
                    ])
            self.assertEqual(len(logs), 2)

    @with_transaction()
    def test_record_set_property(self):
        "Test setting a property on a record with a different savepoint"
        pool = Pool()
        Model = pool.get('test.savepoint')

        record = Model(value=1)
        record.save()
        with self.assertRaises(AssertionError):
            with Transaction().savepoint():
                record.value = 2

    @with_transaction()
    def test_rollback_cache_invalidation(self):
        "Test rollbacking a savepoint does not pollute the cache"
        pool = Pool()
        Model = pool.get('test.savepoint.cache_read')

        with Transaction().savepoint() as sp:
            record, = Model.create([{
                        'value': 1,
                        }])
            record_id = record.id
            # Filling the transaction cache
            Model.search([('value', '=', 1)])
            sp.rollback()

        cache = Transaction().get_cache()
        self.assertNotIn(record_id, cache[Model.__name__])

    @with_transaction()
    def test_cache_copy_on_savepoint(self):
        "Test the copy of the cache when using a savepoint"
        pool = Pool()
        Model = pool.get('test.savepoint')

        record = Model(value=1)
        record.save()
        record_id = record.id
        Model.search([('value', '=', 1)])

        transaction = Transaction()

        with transaction.savepoint():
            cache = transaction.get_cache()
            self.assertIn(record_id, cache[Model.__name__])

            record2 = Model(value=2)
            record2.save()
            record2_id = record2.id
            Model.search([('value', '=', 2)])

            with transaction.savepoint():
                cache = transaction.get_cache()
                self.assertIn(record_id, cache[Model.__name__])
                self.assertIn(record2_id, cache[Model.__name__])

    @with_transaction()
    def test_decorator(self):
        "Test with_savepoint decorator"
        pool = Pool()
        Model = pool.get('test.savepoint.decorator')

        Model.method(1)

        records = Model.search([('value', '=', 1)])
        self.assertNotEqual(records, [])

    @with_transaction()
    def test_decorator_rollback(self):
        "Test with_savepoint decorator doing a rollback"
        pool = Pool()
        Model = pool.get('test.savepoint.decorator')

        Model.method(2, AttributeError)

        records = Model.search([('value', '=', 2)])
        self.assertEqual(records, [])

    @with_transaction()
    def test_decorator_exception(self):
        "Test with_savepoint decorator accepting exceptions"
        pool = Pool()
        Model = pool.get('test.savepoint.decorator')

        Model.method_w_exception(3, ZeroDivisionError)

        records = Model.search([('value', '=', 3)])
        self.assertEqual(records, [])

    @with_transaction()
    def test_decorator_exception_rollback(self):
        "Test with_savepoint decorator raising an exception"
        pool = Pool()
        Model = pool.get('test.savepoint.decorator')

        with self.assertRaises(AttributeError):
            Model.method_w_exception(4, AttributeError)
