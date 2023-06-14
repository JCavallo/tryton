import string
import random
import logging
from threading import local


__all__ = [
    'ServerContext',
    ]


def generate_context(key=None, value=None, length=20):
    def generate_random_string():
        return ''.join(random.SystemRandom().choice(
            string.ascii_uppercase + string.digits) for _ in range(length))
    if not key:
        key = generate_random_string()
    if not value:
        value = generate_random_string()
    return {key: value}


TEST_CONTEXT = generate_context(value=True)
TEST_CONTEXT_KEY = list(TEST_CONTEXT.keys())[0]


class _AttributeManager(object):
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __enter__(self):
        return ServerContext()

    def __exit__(self, type, value, traceback):
        context = ServerContext()
        for name, value in self.kwargs.items():
            setattr(context, name, value)


class _Local(local):
    instance = None


class ServerContext(object):
    'Trytond context controller'
    _local = _Local()

    def __new__(cls):
        instance = cls._local.instance
        if not instance:
            cls._local.instance = super(ServerContext, cls).__new__(cls)
            logging.getLogger().debug('New Server Context instance created')
            cls._local.instance.context = {}
        return cls._local.instance

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._local.instance = None

    def get(self, *args, **kwargs):
        return self.context.get(*args, **kwargs)

    def set_context(self, context=None, **kwargs):
        if context is None:
            context = {}
        manager = _AttributeManager(context=self.context)
        self.context = self.context.copy()
        self.context.update(context)
        if kwargs:
            self.context.update(kwargs)
        return manager

    def reset_context(self):
        manager = _AttributeManager(context=self.context)
        self.context = {}
        return manager
