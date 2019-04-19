#!/usr/bin/env python
from __future__ import print_function, absolute_import, division

import logging
import paramiko

from errno import ENOENT

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn


class OXFS(LoggingMixIn, Operations):
    '''
    A simple sftp filesystem with powerfull cache. Requires paramiko: http://www.lag.net/paramiko/

    You need to be able to login to remote host without entering a password.
    '''

    def __init__(self, host, username=None, port=22):
        self.logger = logging.basicConfig(level=logging.INFO)
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.load_system_host_keys()
        self.client.connect(host, port=port, username=username)
        self.sftp = self.client.open_sftp()
        self.files = dict()
        self.directories = dict()

    def chmod(self, path, mode):
        return self.sftp.chmod(path, mode)

    def chown(self, path, uid, gid):
        return self.sftp.chown(path, uid, gid)

    def create(self, path, mode):
        f = self.sftp.open(path, 'w')
        f.chmod(mode)
        f.close()
        return 0

    def destroy(self, path):
        self.sftp.close()
        self.client.close()

    def getattr(self, path, fh=None):
        if self.files.get(path):
            attr = self.files[path]
            if 'null' == attr:
                raise FuseOSError(ENOENT)
            return attr

        try:
            st = self.sftp.lstat(path)
        except:
            self.files[path] = 'null'
            raise FuseOSError(ENOENT)

        attr = self.attr2dict(st)
        self.files[path] = attr
        return attr

    def mkdir(self, path, mode):
        return self.sftp.mkdir(path, mode)

    def read(self, path, size, offset, fh):
        f = self.sftp.open(path)
        f.seek(offset, 0)
        buf = f.read(size)
        f.close()
        return buf

    def attr2dict(self, attr):
        return dict((key, getattr(attr, key)) for key in (
            'st_atime', 'st_gid', 'st_mode', 'st_mtime', 'st_size', 'st_uid'))

    def readdir(self, path, fh):
        if self.directories.get(path):
            return self.directories[path]

        attrs = self.sftp.listdir_attr(path)
        files = [(attr.filename, self.attr2dict(attr), 0) for attr in attrs]
        self.directories[path] = files
        return files + ['.', '..']

    def readlink(self, path):
        return self.sftp.readlink(path)

    def rename(self, old, new):
        return self.sftp.rename(old, new)

    def rmdir(self, path):
        return self.sftp.rmdir(path)

    def symlink(self, target, source):
        return self.sftp.symlink(source, target)

    def truncate(self, path, length, fh=None):
        return self.sftp.truncate(path, length)

    def unlink(self, path):
        return self.sftp.unlink(path)

    def utimens(self, path, times=None):
        return self.sftp.utime(path, times)

    def write(self, path, data, offset, fh):
        f = self.sftp.open(path, 'r+')
        f.seek(offset, 0)
        f.write(data)
        f.close()
        return len(data)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', dest='login')
    parser.add_argument('host')
    parser.add_argument('mount')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if not args.login:
        if '@' in args.host:
            args.login, _, args.host = args.host.partition('@')

    fuse = FUSE(
        OXFS(args.host, username=args.login),
        args.mount,
        foreground=True,
        nothreads=True,
        allow_other=True)
