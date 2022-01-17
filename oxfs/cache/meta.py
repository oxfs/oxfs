#!/usr/bin/env python

import collections
import threading


def synchronized(func):
    func.__lock__ = threading.Lock()

    def synced_func(*args, **kws):
        with func.__lock__:
            return func(*args, **kws)

    return synced_func


class SimpleCache:
    '''
    The mechanism used by the CPython interpreter to assure that only one thread executes Python bytecode at a time. This simplifies the CPython implementation by making the object model (including critical built-in types such as dict) implicitly safe against concurrent access.
    See: https://docs.python.org/3/glossary.html#term-global-interpreter-lock
    '''

    def __init__(self):
        self.cache = dict()

    def remove(self, k):
        self.cache.pop(k, None)

    def get(self, k):
        return self.cache.get(k, None)

    def put(self, k, v):
        self.cache[k] = v


class LruCache:
    def __init__(self, maxsize=2**18):
        self.maxsize = maxsize
        self.cache = collections.OrderedDict()

    @synchronized
    def remove(self, k):
        self.cache.pop(k, None)

    @synchronized
    def copy(self):
        return self.cache.copy()

    @synchronized
    def get(self, k):
        v = self.cache.get(k, None)
        if v is not None:
            self.cache.move_to_end(k)
        return v

    @synchronized
    def put(self, k, v):
        if len(self.cache) >= self.maxsize:
            self.cache.popitem(last=False)
        self.cache[k] = v
