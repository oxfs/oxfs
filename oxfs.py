#!/usr/bin/env python

import os, sys
import logging
import argparse
import xxhash
import paramiko
import threading
from errno import ENOENT

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ProcessPoolExecutor
from fuse import FUSE, FuseOSError, Operations, LoggingMixIn
from cache import MemoryCache

class OXFS(LoggingMixIn, Operations):
    '''
    A simple sftp filesystem with powerfull cache. Requires paramiko: http://www.lag.net/paramiko/

    You need to be able to login to remote host without entering a password.
    '''

    def __init__(self, host, user, cache_path, port=22):
        self.logger = logging.getLogger('oxfs')

        self.host = host
        self.port = port
        self.user = user
        self.cache_path = cache_path

        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.load_system_host_keys()
        self.client.connect(self.host, port=self.port, username=self.user)
        self.sftp = self.client.open_sftp()

        # self.taskpool = ThreadPoolExecutor(1)
        self.taskpool = ProcessPoolExecutor(1)
        self.attributes = MemoryCache(prefix='attributes')
        self.directories = MemoryCache(prefix='directories')

        if not os.path.exists(self.cache_path):
            os.makedirs(self.cache_path)

    def submit(self, func, *args):
        t = threading.Thread(target=func, args=args)
        t.start()
        t.join()

    def open_sftp(self):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.load_system_host_keys()
        client.connect(self.host, port=self.port, username=self.user)
        return client, client.open_sftp()

    def cachefile(self, path):
        return os.path.join(self.cache_path, xxhash.xxh64_hexdigest(path))

    def trylock(self, path):
        lockfile = '{}.lock'.format(self.cachefile(path))
        if os.path.exists(lockfile):
            return False
        open(lockfile, 'w').close()
        return True

    def unlock(self, path):
        lockfile = '{}.lock'.format(self.cachefile(path))
        os.remove(lockfile)

    def getfile(self, path):
        if not self.trylock(path):
            self.logger.info('getfile lock failed {}'.format(path))
            return False

        self.logger.info('getfile {}'.format(path))
        client, sftp = self.open_sftp()
        cachefile = self.cachefile(path)
        with open(cachefile, 'wb') as outfile:
            with self.sftp.open(path, 'rb') as infile:
                outfile.write(infile.read())

        sftp.close()
        client.close()
        self.unlock(path)
        return True

    def extract(self, attr):
        return dict((key, getattr(attr, key)) for key in (
            'st_atime', 'st_gid', 'st_mode', 'st_mtime', 'st_size', 'st_uid'))

    def chmod(self, path, mode):
        status = self.sftp.chmod(path, mode)

        self.attributes.remove(path)
        # self.taskpool.submit(self.getattr, path)
        return status

    def chown(self, path, uid, gid):
        return self.sftp.chown(path, uid, gid)

    def create(self, path, mode):
        f = self.sftp.open(path, 'w')
        f.chmod(mode)
        f.close()

        self.attributes.remove(path)
        # self.taskpool.submit(self.getattr, path)
        self.directories.remove(os.path.dirname(path))
        # self.taskpool.submit(self.readdir, os.path.dirname(path))
        return 0

    def destroy(self, path):
        # self.taskpool.shutdown(wait=True)
        self.sftp.close()
        self.client.close()

    def getattr(self, path, fh=None):
        attr = self.attributes.fetch(path)
        if attr is not None:
            if 'filenotexist' == attr:
                raise FuseOSError(ENOENT)
            return attr

        self.logger.info('sftp getattr {}'.format(path))
        try:
            attr = self.extract(self.sftp.lstat(path))
            self.attributes.insert(path, attr)
            return attr
        except:
            self.attributes.insert(path, 'filenotexist')
            raise FuseOSError(ENOENT)

    def mkdir(self, path, mode):
        self.logger.info('mkdir {}'.format(path))
        status = self.sftp.mkdir(path, mode)
        self.attributes.remove(path)
        # self.taskpool.submit(self.getattr, path)
        self.directories.remove(os.path.dirname(path))
        # self.taskpool.submit(self.readdir, os.path.dirname(path))
        self.logger.info('after call mkdir')
        return status

    def read(self, path, size, offset, fh):
        cachefile = self.cachefile(path)
        if os.path.exists(cachefile):
            with open(cachefile, 'r') as infile:
                infile.seek(offset, 0)
                return infile.read(size)

        # self.taskpool.submit(self.getfile, path)
        self.submit(self.getfile, path)
        with self.sftp.open(path, 'r') as infile:
            infile.seek(offset, 0)
            return infile.read(size)

    def readdir(self, path, fh=None):
        entries = self.directories.fetch(path)
        if entries is None:
            entries = self.sftp.listdir(path)
            self.directories.insert(path, entries)
            self.logger.info('sftp readdir {} = {}'.format(path, entries))

        return entries + ['.', '..']

    def readlink(self, path):
        return self.sftp.readlink(path)

    def rename(self, old, new):
        status = self.sftp.rename(old, new)
        self.attributes.remove(old)
        # self.taskpool.submit(self.getattr, new)

        self.directories.remove(os.path.dirname(old))
        # self.taskpool.submit(self.readdir, os.path.dirname(old))

    def rmdir(self, path):
        status = self.sftp.rmdir(path)
        self.attributes.remove(path)
        # self.taskpool.submit(self.getattr, path)
        self.directories.remove(os.path.dirname(path))
        # self.taskpool.submit(self.readdir, os.path.dirname(path))
        self.logger.info('after call rmdir')
        return status

    def symlink(self, target, source):
        'creates a symlink `target -> source` (e.g. ln -sf source target)'

        status = self.sftp.symlink(source, target)
        # self.taskpool.submit(self.getattr, target)
        self.directories.remove(os.path.dirname(target))
        # self.taskpool.submit(self.readdir, os.path.dirname(target))
        return status

    def truncate(self, client, path, length, fh=None):
        client, sftp = self.open_sftp()
        sftp.truncate(path, length)
        sftp.close()
        client.close()
        return True

    def truncate(self, path, length, fh=None):
        cachefile = self.cachefile(path)
        if not os.path.exists(cachefile):
            raise FuseOSError(ENOENT)

        status = os.truncate(cachefile, length)
        self.attributes.insert(path, self.extract(os.lstat(cachefile)))
        # self.taskpool.submit(self.truncate, self.client, path, length)
        self.submit(self.truncate, self.client, path, length)
        return status

    def unlink(self, path):
        status = self.sftp.unlink(path)
        self.attributes.remove(path)
        # self.taskpool.submit(self.getattr, path)
        self.directories.remove(os.path.dirname(path))
        # self.taskpool.submit(self.readdir, os.path.dirname(path))
        return status

    def utimens(self, path, times=None):
        status = self.sftp.utime(path, times)
        self.attributes.remove(path)
        # self.taskpool.submit(self.getattr, path)
        return status

    def write(self, client, path, data, offset, fh=None):
        self.logger.info('sftp write {}'.format(path))
        client, sftp = self.open_sftp()
        with sftp.open(path, 'r+') as outfile:
            outfile.seek(offset, 0)
            outfile.write(size)

        sftp.close()
        client.close()
        return len(data)

    def write(self, path, data, offset, fh):
        cachefile = self.cachefile(path)
        if not os.path.exists(cachefile):
            raise FuseOSError(ENOENT)

        with open(cachefile, 'r+') as outfile:
            outfile.seek(offset, 0)
            outfile.write(data)

        self.attributes.insert(path, self.extract(os.lstat(cachefile)))
        # self.taskpool.submit(self.write, self.client, path, data, offset, fh)
        self.submit(self.write, self.client, path, data, offset, fh)
        return len(data)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', dest='host')
    parser.add_argument('-m', dest='mount_point')
    parser.add_argument('-p', dest='cache_path')
    args = parser.parse_args()

    if not args.host:
        sys.exit()
    if not args.mount_point:
        sys.exit()
    if not args.cache_path:
        sys.exit()

    if '@' not in args.host:
        logging.error('invalid host arguments.')
        sys.exit()

    user, _, args.host = args.host.partition('@')
    fuse = FUSE(OXFS(args.host, user=user, cache_path=args.cache_path),
                args.mount_point,
                foreground=True,
                nothreads=True,
                allow_other=True)
