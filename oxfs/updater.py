#!/usr/bin/env python

import hashlib
import logging
import os
import pathlib
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

    # 1. size check
    # 2. modify time check
    # 3. md5sum check
    def can_skip_update(self, path, local, remote):
        self.logger.info(str(path))
        self.logger.info(str(local))
        self.logger.info(str(remote))
        if local == ENOENT or remote == ENOENT:
            self.unlink(path)
            return True

        if local['st_size'] != remote['st_size']:
            return False

        if local['st_mtime'] >= remote['st_mtime']:
            return True

        cachefile = self.fs.cachefile(path)
        if not os.path.exists(cachefile):
            return True

        # skip md5sum check for small files (<1k)
        if remote['st_size'] < 1024:
            return False

        local_md5sum = hashlib.md5(pathlib.Path(cachefile).read_bytes()).hexdigest()
        stdin, stdout, stderr = self.client.exec_command('md5sum {}'.format(path))
        remote_md5sum = stdout.read().decode('utf-8').split(' ')[0]
        stdin.close(), stdout.close(), stderr.close()
        self.logger.info(local_md5sum)
        self.logger.info(remote_md5sum)
        if local_md5sum == remote_md5sum:
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
                if not self.can_skip_update(path, value, attr):
                    self.unlink(path)
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
