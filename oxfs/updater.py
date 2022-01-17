#!/usr/bin/env python

from concurrent.futures import ThreadPoolExecutor
import hashlib
import logging
import os
import pathlib
import stat
import threading
import time

from errno import ENOENT
from oxfs.cache.fs import CacheManager
from oxfs.lock import FileOpsLock


class CacheUpdater:
    def __init__(self, oxfs, period):
        self.logger = logging.getLogger(__class__.__name__)
        self.oxfs = oxfs
        self.ops: FileOpsLock = oxfs.ops
        self.pool: ThreadPoolExecutor = oxfs.taskpool
        self.manager: CacheManager = oxfs.manager
        self.period = period
        self.running = True

    def run(self):
        self.thread = threading.Thread(target=self.loop, args=())
        self.thread.daemon = True
        self.thread.name = 'cache-updater'
        self.thread.start()

    def shutdown(self):
        self.running = False

    def loop(self):
        self.client, self.sftp = self.oxfs.open_sftp()
        while self.running:
            time.sleep(self.period)
            self.renew_lstat()
            self.renew_listdir()
        self.sftp.close()
        self.client.close()

    def skip_syncfile(self, path, cached, remote):
        cachefile = self.manager.cachefile(path)
        if cached == ENOENT or remote == ENOENT:
            self.manager.pop(cachefile)
            return True

        if not os.path.exists(cachefile):
            return True

        if cached['st_size'] != remote['st_size']:
            return False

        if os.lstat(cachefile).st_size != remote['st_size']:
            return False

        stdin, stdout, stderr = self.client.exec_command(
            'md5sum {}'.format(path))
        remote_md5sum = stdout.read().decode('utf-8').split(' ')[0]
        stdin.close(), stdout.close(), stderr.close()
        cached_md5sum = hashlib.md5(pathlib.Path(
            cachefile).read_bytes()).hexdigest()
        self.logger.info(cached_md5sum)
        self.logger.info(remote_md5sum)
        if cached_md5sum == remote_md5sum:
            return True

        return False

    def renew_lstat(self):
        attributes = self.oxfs.attributes
        cache = attributes.copy()
        for path, value in cache.items():
            if not self.ops.trylock(path):
                continue
            attr = ENOENT
            try:
                attr = self.oxfs.extract(self.sftp.lstat(path))
            except Exception as e:
                self.logger.debug(e)

            if type(value) == dict and stat.S_ISDIR(value['st_mode']):
                attributes.put(path, attr)
                self.ops.unlock(path)
                continue

            if value != attr:
                self.logger.info(path)
                if not self.skip_syncfile(path, value, attr):
                    self.manager.pop(self.manager.cachefile(path))
                    attributes.put(path, attr)
                    self.pool.submit(self.oxfs._getfile, path)

            self.ops.unlock(path)

    def renew_listdir(self):
        directories = self.oxfs.directories
        cache = directories.copy()
        for path, value in cache.items():
            entries = None
            try:
                entries = self.sftp.listdir(path)
                if sorted(value) != sorted(entries):
                    directories.put(path, entries)
            except Exception as e:
                self.logger.debug(e)
