#!/usr/bin/env python

import logging
import os
import sys
import threading
import time
import xxhash

from errno import ENOENT
from oxfs.task_executor import Task

class CacheUpdater:
    def __init__(self, fs, cache_timeout):
        self.fs = fs
        self.attributes = fs.attributes
        self.directories = fs.directories
        self.taskpool = fs.taskpool
        self.timeout = cache_timeout
        self.running = True
        self.logger = logging.getLogger('cache_updater')

    def run(self):
        self.thread = threading.Thread(target=self.loop, args=())
        self.thread.daemon = True
        self.thread.name = 'cache_updater'
        self.thread.start()

    def shutdown(self):
        self.running = False

    def loop(self):
        self.client, self.sftp = self.fs.open_sftp()
        while self.running:
            self.update_attributes()
            self.update_directories()
            time.sleep(self.timeout)

        self.sftp.close()
        self.client.close()

    def unlink(self, path):
        cachefile = self.fs.cachefile(path)
        if os.path.exists(cachefile):
            os.unlink(cachefile)
            return True
        return False

    def update_attributes(self):
        cache = self.attributes.cache.copy()
        for path, value in cache.items():
            self.logger.info(path)
            attr = ENOENT
            try:
                attr = self.fs.extract(self.sftp.lstat(path))
            except Exception as e:
                self.logger.info(e)

            if value != attr:
                self.attributes.insert(path, attr)
                if self.unlink(path):
                    task = Task(xxhash.xxh64(path).intdigest(), self.fs.getfile, path)
                    self.taskpool.submit(task)

    def update_directories(self):
        cache = self.directories.cache.copy()
        for path, value in cache.items():
            self.logger.info(path)
            entries = None
            try:
                entries = self.sftp.listdir(path)
                if sorted(value) != sorted(entries):
                    self.directories.insert(path, entries)
            except Exception as e:
                self.logger.info(e)
