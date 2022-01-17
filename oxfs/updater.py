#!/usr/bin/env python

import hashlib
import logging
import os
import pathlib
import stat
import threading
import time
import xxhash

from errno import ENOENT
from oxfs.task_executor import Task


class CacheUpdater:
    def __init__(self, fs, cache_timeout):
        self.fs = fs
        self.att = fs.attributes
        self.dir = fs.directories
        self.pool = fs.taskpool
        self.manager = fs.manager
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
            self.att_check()
            self.dir_check()
            time.sleep(self.timeout)

        self.sftp.close()
        self.client.close()

    # 1. size check
    # 2. modify time check
    # 3. md5sum check
    def can_skip(self, path, cached, remote):
        self.logger.info(str(path))
        self.logger.info(str(cached))
        self.logger.info(str(remote))
        cachefile = self.manager.cachefile(path)
        if cached == ENOENT or remote == ENOENT:
            self.manager.pop(cachefile)
            return True

        if not os.path.exists(cachefile):
            return True

        if cached['st_size'] != remote['st_size']:
            return False

        cached_md5sum = hashlib.md5(pathlib.Path(
            cachefile).read_bytes()).hexdigest()
        stdin, stdout, stderr = self.client.exec_command(
            'md5sum {}'.format(path))
        remote_md5sum = stdout.read().decode('utf-8').split(' ')[0]
        stdin.close(), stdout.close(), stderr.close()
        self.logger.info(cached_md5sum)
        self.logger.info(remote_md5sum)
        if cached_md5sum == remote_md5sum:
            return True

        return False

    def att_check(self):
        cache = self.att.copy()
        for path, value in cache.items():
            att = ENOENT
            try:
                att = self.fs.extract(self.sftp.lstat(path))
            except Exception as e:
                self.logger.info(e)

            if type(value) == dict and stat.S_ISDIR(value['st_mode']):
                self.att.put(path, att)
                continue

            if value != att:
                self.logger.info(path)
                if not self.can_skip(path, value, att):
                    self.manager.pop(self.manager.cachefile(path))
                    self.att.put(path, att)
                    task = Task(xxhash.xxh64(path).intdigest(),
                                self.fs.getfile, path)
                    self.pool.submit(task)

    def dir_check(self):
        cache = self.dir.copy()
        for path, value in cache.items():
            entries = None
            try:
                entries = self.sftp.listdir(path)
                if sorted(value) != sorted(entries):
                    self.logger.info(path)
                    self.dir.put(path, entries)
            except Exception as e:
                self.logger.info(e)
