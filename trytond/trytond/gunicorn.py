# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import os
import signal
import logging
import resource
import csv
import time
import datetime
from io import StringIO

MAX_RSS_MB = os.environ.get('TRYTOND_MAX_RSS_MB', 1024)
CHECK_INTERVAL = os.environ.get('TRYTOND_RSS_CHECK_INTERVAL', 30)  # seconds
_last_checked = {}
LF = '%(process)s %(thread)s [%(asctime)s] %(levelname)s %(name)s %(message)s'

logger = logging.getLogger()

db_names = os.environ.get('TRYTOND_DATABASE_NAMES')
db_list = []
if db_names:
    # Read with csv so database name can include special chars
    reader = csv.reader(StringIO(db_names))
    for name in next(reader):
        db_list.append(name)


def post_fork(server, worker):
    # This post_fork is useful only when the app is loaded before
    # forking. Which happen when preloa_app gunicorn config is set to True
    if getattr(server.cfg, 'preload_app', False) is not True:
        return
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


def post_request(worker, req, environ, resp):
    '''
    post_request() gunicorn hook called after a worker completed a request
    Since gunicorn doesn't feature uwsgi's --reload-on-rss to kill bloated
    workers
    '''
    now = time.time()

    pid = worker.pid
    # Only check every CHECK_INTERVAL seconds per worker
    if _last_checked.get(pid, 0) + CHECK_INTERVAL > now:
        return

    logger.info(f'Worker {pid} is being checked after '
        f'{now - _last_checked.get(pid, 0)} seconds')
    _last_checked[pid] = now
    usage = resource.getrusage(resource.RUSAGE_SELF)
    rss_mb = usage.ru_maxrss / (1024 ** 2)
    # To mimic uwsgi --reload-on-rss kill with inflated memory usage to
    # mitigate leaks
    logger.debug(f'Worker {pid} is currently using {rss_mb} MB')
    if rss_mb > MAX_RSS_MB:
        logger.info(f'Worker {pid} exceeded RSS limit: '
            f'{rss_mb} MB > {MAX_RSS_MB} MB. Exiting.')
        worker.alive = False
