#!/usr/bin/env python

class MemoryCache(object):
    '''
    The mechanism used by the CPython interpreter to assure that only one thread executes Python bytecode at a time. This simplifies the CPython implementation by making the object model (including critical built-in types such as dict) implicitly safe against concurrent access.
    See: https://docs.python.org/3/glossary.html#term-global-interpreter-lock
    '''
    def __init__(self, prefix):
        self.prefix = prefix
        self.cache = dict()

    def remove(self, k):
        self.cache.pop(k, None)

    def fetch(self, k):
        return self.cache.get(k, None)

    def insert(self, k, v):
        self.cache[k] = v

    def append_value(self, k, v):
        if self.cache.get(k, None) is not None:
            self.cache[k].append(v)
        else:
            self.cache[k] = [v, ]

    def pop_value(self, k, v):
        if self.cache.get(k, None) is not None:
            self.cache[k].remove(v)
