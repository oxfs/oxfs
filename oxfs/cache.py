#!/usr/bin/env python

import threading

class MemoryCache(object):
    def __init__(self, prefix):
        self.prefix = prefix
        self.cache = dict()
        self.lock_guard = threading.Lock()

    def remove(self, k):
        with self.lock_guard:
            self.cache.pop(k, None)

    def fetch(self, k):
        with self.lock_guard:
            return self.cache.get(k, None)

    def insert(self, k, v):
        with self.lock_guard:
            self.cache[k] = v

    def append_value(self, k, v):
        with self.lock_guard:
            if self.cache.get(k, None) is not None:
                self.cache[k].append(v)
            else:
                self.cache[k] = [v]

    def pop_value(self, k, v):
        with self.lock_guard:
            if self.cache.get(k, None) is not None:
                self.cache[k].remove(v)
