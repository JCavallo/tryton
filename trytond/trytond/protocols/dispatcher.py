# -*- coding: utf-8 -*-
# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import http.client
import logging
import pydoc
import time
import traceback

from sql import Table

from trytond import __series__, backend, security
from trytond.config import config, get_hostname
from trytond.error_handling import error_wrap
from trytond.exceptions import (
    ConcurrencyException, LoginException, RateLimitException, UserError,
    UserWarning)
from trytond.rpc import RPCReturnException
from trytond.tools import is_instance_method
from trytond.tools.logging import format_args
from trytond.transaction import Transaction, TransactionError
from trytond.worker import run_task
from trytond.wsgi import app

from .wrappers import HTTPStatus, Response, abort, with_pool

__all__ = ['register_authentication_service']

logger = logging.getLogger(__name__)

# JCA: log slow RPC (> log_time_threshold)
slow_threshold = config.getfloat('web', 'log_time_threshold', default=-1)
if slow_threshold >= 0:
    slow_logger = logging.getLogger('trytond.rpc.performance')

# JCA: Format json logs
format_json_parameters = config.getboolean('web', 'format_parameters_logs',
    default=False)
format_json_result = config.getboolean('web', 'format_result_logs',
    default=False)
if format_json_parameters or format_json_result:
    import datetime
    import base64
    import json
    from decimal import Decimal

    class DEBUGEncoder(json.JSONEncoder):

        serializers = {}

        @classmethod
        def register(cls, klass, encoder):
            assert klass not in cls.serializers
            cls.serializers[klass] = encoder

        def default(self, obj):
            marshaller = self.serializers.get(type(obj),
                super(DEBUGEncoder, self).default)
            return marshaller(obj)

    DEBUGEncoder.register(datetime.datetime,
        lambda x: 'DateTime(%s-%s-%s %s:%s:%s.%s)' % (x.year, x.month, x.day,
            x.hour, x.minute, x.second, x.microsecond))
    DEBUGEncoder.register(datetime.date, lambda x: 'Date(%s-%s-%s)' % (
            x.year, x.month, x.day))
    DEBUGEncoder.register(datetime.time, lambda x: 'Time(%s:%s:%s.%s)' % (
            x.hour, x.minute, x.second, x.microsecond))
    DEBUGEncoder.register(datetime.timedelta, lambda x: 'TimeDelta(%s seconds)' % (
            x.total_seconds()))
    DEBUGEncoder.register(Decimal, lambda x: 'Decimal(%s)' % str(x))
    DEBUGEncoder.register(bytes, lambda x: 'Bytes(%s)' % base64.encodebytes(x))
    DEBUGEncoder.register(bytearray,
        lambda x: 'Bytes(%s)' % base64.encodebytes(x))


ir_configuration = Table('ir_configuration')
ir_lang = Table('ir_lang')
ir_module = Table('ir_module')
res_user = Table('res_user')

# JCA: log slow RPC
def log_exception(method, *args, **kwargs):
    kwargs['exc_info'] = False
    method(*args, **kwargs)
    for elem in traceback.format_exc().split('\n'):
        method(elem)


@app.route('/<string:database_name>/', methods=['POST'])
def rpc(request, database_name):
    methods = {
        'common.db.login': login,
        'common.db.logout': logout,
        'common.db.reset_password': reset_password,
        'system.listMethods': list_method,
        'system.methodHelp': help_method,
        'system.methodSignature': lambda *a: 'signatures not supported',
        }
    return methods.get(request.rpc_method, _dispatch)(
        request, database_name, *request.rpc_params)


def login(request, database_name, user, parameters, language=None):
    context = {
        'language': language,
        '_request': request.context,
        }
    try:
        session = security.login(
            database_name, user, parameters, context=context)
        code = HTTPStatus.UNAUTHORIZED
    except backend.DatabaseOperationalError:
        logger.error('fail to connect to %s', database_name, exc_info=True)
        abort(HTTPStatus.NOT_FOUND)
    except RateLimitException:
        session = None
        code = HTTPStatus.TOO_MANY_REQUESTS
    if not session:
        abort(code)
    allow_subscribe = config.getboolean(
        'bus', 'allow_subscribe', default=False)
    bus_url_host = config.get('bus', 'url_host', default=request.host_url)
    return (*session, bus_url_host if allow_subscribe else None)


@app.auth_required
def logout(request, database_name):
    auth = request.authorization
    security.logout(
        database_name, auth.get('userid'), auth.get('session'),
        context={'_request': request.context})


def reset_password(request, database_name, user, language=None):
    authentications = config.get(
        'session', 'authentications', default='password').split(',')
    if not any('password' in m.split('+') for m in authentications):
        abort(HTTPStatus.FORBIDDEN)
    context = {
        'language': language,
        '_request': request.context,
        }
    try:
        security.reset_password(database_name, user, context=context)
    except backend.DatabaseOperationalError:
        logger.error('fail to connect to %s', database_name, exc_info=True)
        abort(HTTPStatus.NOT_FOUND)
    except RateLimitException:
        abort(HTTPStatus.TOO_MANY_REQUESTS)


@app.route('/', methods=['POST'])
def root(request, *args):
    methods = {
        'common.server.version': lambda *a: __series__,
        'common.db.list': db_list,
        'common.authentication.services': authentication_services,
        }
    return methods[request.rpc_method](request, *request.rpc_params)


@app.route('/', methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def options(request, path=None):
    return Response(status=HTTPStatus.NO_CONTENT)


def db_exist(request, database_name):
    try:
        backend.Database(database_name).connect()
        return True
    except Exception:
        return False


def db_list(request, *args):
    if not config.getboolean('database', 'list'):
        abort(HTTPStatus.FORBIDDEN)
    context = {'_request': request.context}
    hostname = get_hostname(request.host)
    with Transaction().start(
            None, 0, context=context, readonly=True, close=True,
            ) as transaction:
        return transaction.database.list(hostname=hostname)


def authentication_services(request):
    return _AUTHENTICATION_SERVICES


def register_authentication_service(name, url):
    _AUTHENTICATION_SERVICES.append((name, url))


_AUTHENTICATION_SERVICES = []


@app.auth_required
@with_pool
def list_method(request, pool):
    methods = []
    for type in ('model', 'wizard', 'report'):
        for object_name, obj in pool.iterobject(type=type):
            for method in obj.__rpc__:
                methods.append(type + '.' + object_name + '.' + method)
    return methods


def get_object_method(request, pool):
    method = request.rpc_method
    type, _ = method.split('.', 1)
    name = '.'.join(method.split('.')[1:-1])
    method = method.split('.')[-1]
    return pool.get(name, type=type), method


@app.auth_required
@with_pool
def help_method(request, pool):
    obj, method = get_object_method(request, pool)
    return pydoc.getdoc(getattr(obj, method))


@error_wrap
@app.auth_required
@with_pool
def _dispatch(request, pool, *args, **kwargs):
    obj, method = get_object_method(request, pool)
    if method in obj.__rpc__:
        rpc = obj.__rpc__[method]
    else:
        abort(
            HTTPStatus.BAD_REQUEST,
            description=f"Method {method} is not available on {obj.__name__}")

    if request.authorization.type == 'session':
        session = request.authorization.get('session')

    user = request.user_id
    if rpc.fresh_session and session:
        context = {'_request': request.context}
        if not security.check_timeout(
                pool.database_name, user, session, context=context):
            abort(http.client.UNAUTHORIZED)

    log_message = '%s.%s%s from %s@%s%s in %i ms'
    username = request.authorization.username
    if isinstance(username, bytes):
        username = username.decode('utf-8')
    log_args = (
        obj.__name__, method,
        format_args(args, kwargs, verbose=logger.isEnabledFor(logging.DEBUG)),
        username, request.remote_addr, request.path)

    def duration():
        return (time.monotonic() - started) * 1000
    started = time.monotonic()

    # JCA: log slow RPC
    if slow_threshold >= 0:
        slow_msg = '%s.%s (%s s)'
        slow_args = (obj, method)
        slow_start = time.time()

    # JCA: Format parameters
    if format_json_parameters and logger.isEnabledFor(logging.DEBUG):
        try:
            for line in json.dumps(args, indent=2, sort_keys=True,
                    cls=DEBUGEncoder).split('\n'):
                logger.debug('Parameters: %s' % line)
        except Exception:
            logger.debug('Could not format parameters in log', exc_info=True)

    # AKE: add session to transaction context
    token, session = None, None
    if request.authorization.type == 'session':
        session = request.authorization.get('session')
    elif request.authorization.type == 'token':
        token = {
            'key': request.authorization.get('token'),
            'user': user,
            'party': request.authorization.get('party_id'),
            }

    retry = config.getint('database', 'retry')
    count = 0
    transaction_extras = {}
    while True:
        if count:
            time.sleep(0.02 * count)
        with Transaction().start(
                pool.database_name, user,
                readonly=rpc.readonly, timeout=rpc.timeout,
                **transaction_extras) as transaction:
            try:
                c_args, c_kwargs, transaction.context, transaction.timestamp \
                    = rpc.convert(obj, *args, **kwargs)
                # AKE: add session to transaction context
                transaction.context.update({
                        'session': session,
                        'token': token,
                        })
                transaction.context['_request'] = request.context
                meth = rpc.decorate(getattr(obj, method))
                if (rpc.instantiate is None
                        or not is_instance_method(obj, method)):
                    result = rpc.result(meth(*c_args, **c_kwargs))
                else:
                    assert rpc.instantiate == 0
                    inst = c_args.pop(0)
                    if hasattr(inst, method):
                        result = rpc.result(meth(inst, *c_args, **c_kwargs))
                    else:
                        result = [rpc.result(meth(i, *c_args, **c_kwargs))
                            for i in inst]
            except TransactionError as e:
                transaction.rollback()
                transaction.tasks.clear()
                e.fix(transaction_extras)
                continue
            except backend.DatabaseTimeoutError:
                logger.warning(log_message, *log_args, exc_info=True)
                abort(HTTPStatus.REQUEST_TIMEOUT)
            except backend.DatabaseOperationalError:
                if count < retry and not rpc.readonly:
                    transaction.rollback()
                    transaction.tasks.clear()
                    count += 1
                    logger.debug("Retry: %i", count)
                    continue
                logger.exception(log_message, *log_args, duration())

                # JCA: log slow RPC
                if slow_threshold >= 0:
                    slow_args += (str(time.time() - slow_start),)
                    log_exception(slow_logger.error, slow_msg, *slow_args)
                raise
            except RPCReturnException as e:
                transaction.rollback()
                transaction.tasks.clear()
                result = e.result()
            except (ConcurrencyException, UserError, UserWarning,
                    LoginException):
                logger.info(
                    log_message, *log_args, duration(),
                    exc_info=logger.isEnabledFor(logging.DEBUG))

                # JCA: log slow RPC
                if slow_threshold >= 0:
                    slow_args += (str(time.time() - slow_start),)
                    log_exception(slow_logger.debug, slow_msg, *slow_args)

                raise
            except Exception:
                logger.exception(log_message, *log_args, duration())

                # JCA: log slow RPC
                if slow_threshold >= 0:
                    slow_args += (str(time.time() - slow_start),)
                    log_exception(slow_logger.error, slow_msg, *slow_args)
                raise
            # Need to commit to unlock SQLite database
            transaction.commit()
        while transaction.tasks:
            task_id = transaction.tasks.pop()
            run_task(pool, task_id)
        if session:
            context = {'_request': request.context}
            security.reset(pool.database_name, session, context=context)
        logger.info(log_message, *log_args, duration())

        # JCA: Allow to format json result
        if format_json_result and logger.isEnabledFor(logging.DEBUG):
            try:
                for line in json.dumps(result, indent=2,
                        sort_keys=True, cls=DEBUGEncoder).split('\n'):
                    logger.debug('Result: %s' % line)
            except Exception:
                logger.debug('Could not format parameters in log',
                    exc_info=True)
        else:
            logger.debug('Result: %s', result)

        # JCA: log slow RPC
        if slow_threshold >= 0:
            slow_diff = time.time() - slow_start
            slow_args += (str(slow_diff),)
            if slow_diff > slow_threshold:
                slow_logger.info(slow_msg, *slow_args)
            else:
                slow_logger.debug(slow_msg, *slow_args)

        response = app.make_response(request, result)
        if rpc.readonly and rpc.cache:
            response.headers.extend(rpc.cache.headers())
        return response
