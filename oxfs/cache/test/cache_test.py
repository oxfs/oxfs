#!/usr/bin/env python

import unittest
from oxfs.cache import stat_cache, file_cache

class CacheTest(unittest.TestCase):
    def setUp(self):
        self.cache = stat_cache.LruCache(3)
        self.cache_fs = file_cache.CacheFs('/tmp', 10)

    def test_stat_cache(self):
        v1 = self.cache.fetch('k1')
        self.assertIsNone(v1)
        self.cache.insert('k1', 'v1')
        v1 = self.cache.fetch('k1')
        self.assertEqual('v1', v1)
        self.cache.insert('k2', 'v2')
        self.cache.insert('k3', 'v3')
        print(self.cache.cache)
        v1 = self.cache.fetch('k1')
        v3 = self.cache.fetch('k3')
        self.cache.insert('k4', 'v4')
        v2 = self.cache.fetch('k2')
        self.assertIsNone(v2)
        print(self.cache.cache)

    def test_cache_fs(self):
        self.cache_fs.put_cache_file('f1', 6)
        self.cache_fs.put_cache_file('f2', 3)
        self.cache_fs.put_cache_file('f3', 1)
        print(self.cache_fs.cache)
        self.cache_fs.get_cache_file('f2')
        self.cache_fs.get_cache_file('f1')
        print(self.cache_fs.cache)
        self.cache_fs.put_cache_file('f4', 4)
        print(self.cache_fs.cache)
