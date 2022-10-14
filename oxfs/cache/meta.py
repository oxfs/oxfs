#!/usr/bin/env python

import collections
import threading


class Cache:
    def __init__(self, maxsize=2**18):
        self.lock = threading.Lock()
        self.maxsize = maxsize
        self.cache = collections.OrderedDict()

    def remove(self, k):
        with self.lock:
            self.cache.pop(k, None)

    def copy(self):
        with self.lock:
            return self.cache.copy()

    def get(self, k):
        with self.lock:
            v = self.cache.get(k, None)
            if v is not None:
                self.cache.move_to_end(k)
            return v

    def put(self, k, v):
        with self.lock:
            if len(self.cache) >= self.maxsize:
                self.cache.popitem(last=False)
            self.cache[k] = v
