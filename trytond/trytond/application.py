# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import csv
import logging
import logging.config
import os
import threading
import datetime
# uwsgdecorators are not available when using gunicorn
try:
    import uwsgidecorators
except ModuleNotFoundError:
    uwsgidecorators = None
from io import StringIO

__all__ = ['app', 'application']

log_file = os.environ.get('WSGI_LOG_FILE')
log_level = os.environ.get('LOG_LEVEL', 'ERROR')
if log_file:
    logging.basicConfig(level=getattr(logging, log_level),
        filename=log_file)

# Logging must be set before importing
if logging_config := os.environ.get('TRYTOND_LOGGING_CONFIG'):
    logging.config.fileConfig(logging_config)
else:
    LF = ('%(process)s %(thread)s [%(asctime)s] %(levelname)s'
        ' %(name)s %(message)s')
    logging.basicConfig(level=getattr(logging, log_level), format=LF)
logging.captureWarnings(True)

if os.environ.get('TRYTOND_COROUTINE'):
    from gevent import monkey
    monkey.patch_all()

from trytond.pool import Pool  # noqa: E402
from trytond.wsgi import app  # noqa: E402

Pool.start_app_initialization()
Pool.start()
# TRYTOND_CONFIG it's managed by importing config
db_names = os.environ.get('TRYTOND_DATABASE_NAMES')
db_list = []
if db_names:
    # Read with csv so database name can include special chars
    reader = csv.reader(StringIO(db_names))
    threads = []
    for name in next(reader):
        db_list.append(name)
        thread = threading.Thread(target=lambda: Pool(name).init())
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()


# JCA: if for some reason the server works properly when starting with
# "trytond" but not with "uwsgi", you may be in the right place.
#
# When the pool initialization is completed (above), there should be no
# busy threads in the main process (psycopg2 threads can probably be ignored
# since they have no reason to be running if the server is doing nothing).
#
# If there are, uwsgi may fork the "wrong" one at the wrong time, and become
# unresponsive. Typical cause (what led me here the first time) would be a
# cache invalidation triggered in the side MemoryCache listeners. There should
# be NO CACHE INVALIDATION when the pool is initialized.
#
# If this is not the cause, good luck
#
# [EDIT]
# Now with gunicorn integration python file are imported after forking, no need
# to implement a post_fork

application = app

Pool.app_initialization_completed()
assert len(threads := threading.enumerate()) == 1, f"len({threads}) != 1"


def skip_on_gunicorn(func):
    def wrapper(func):
        if uwsgidecorators is None:
            return
        else:
            return uwsgidecorators.postfork(func)

    return wrapper(func)


@skip_on_gunicorn
def preload():
    from trytond.transaction import Transaction
    from trytond.cache import Cache
    for db_name in db_list:
        if db_name not in Cache._local.listeners:
            if not Cache._clean_last:
                Cache._clean_last = datetime.date.min
            with Transaction().start(db_name, 0, readonly=True):
                # Starting a transaction will trigger `Cache.sync`, which
                # should spawn a thread to listen for cache invalidation and
                # pool refresh events
                pass
        if db_name not in Cache._local.listeners:
            raise AssertionError
