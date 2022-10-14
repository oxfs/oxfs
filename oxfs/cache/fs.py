#!/usr/bin/env python

import collections
import logging
import os
import threading
import xxhash


class CacheManager:
    def __init__(self, cache_path, max_disk_size_mb=2**10):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cache_path = cache_path
        self.maxsize = max_disk_size_mb << 20
        self.size = 0
        self.cache = collections.OrderedDict()  # key: file name, value: file size
        self.lock = threading.Lock()
        self.initialize()

    def initialize(self):
        if not os.path.exists(self.cache_path):
            os.makedirs(self.cache_path)
            return
        names = os.listdir(self.cache_path)
        for name in names:
            path = os.path.join(self.cache_path, name)
            self.cache[path] = os.lstat(path).st_size

    def copy(self):
        with self.lock:
            return self.cache.copy()

    def unlink(self, path):
        try:
            os.unlink(path)
        except:
            pass

    def pop(self, key):
        with self.lock:
            self.cache.pop(key, None)
        self.unlink(key)

    def cachefile(self, path):
        return os.path.join(self.cache_path, xxhash.xxh64_hexdigest(path))

    def renew(self, key):
        with self.lock:
            if self.cache.get(key, None) is not None:
                self.cache.move_to_end(key)

    def put(self, key):
        files = []
        with self.lock:
            old = self.cache.pop(key, None)
            if old is not None:
                self.size -= old
            size = os.lstat(key).st_size
            self.size += size
            self.cache[key] = size
            self.cache.move_to_end(key)
            while self.size > self.maxsize:
                k, s = self.cache.popitem(last=False)
                self.size -= s
                files.append(k)
        for f in files:
            self.unlink(f)
