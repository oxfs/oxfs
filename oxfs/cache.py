#!/usr/bin/env python

class MemoryCache(object):
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
            self.cache[k] = [v]

    def pop_value(self, k, v):
        if self.cache.get(k, None) is not None:
            self.cache[k].remove(v)
