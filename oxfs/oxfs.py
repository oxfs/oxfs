#!/usr/bin/env python

import argparse
import base64
import getpass
import logging
import multiprocessing
import os
import threading
import paramiko
import platform
import subprocess
import sys

from concurrent.futures import ThreadPoolExecutor
from errno import ENOENT
from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

from oxfs.cache import meta, fs
from oxfs.lock import FileOpsLock
from oxfs.updater import CacheUpdater


class Oxfs(LoggingMixIn, Operations):
    '''
    A dead simple, fast SFTP file system. Home: https://oxfs.io/

    You need to be able to login to remote host without entering a password.
    '''

    def __init__(self, host, user, cache_path, remote_path, port=22, password=None):
        self.logger = logging.getLogger(__class__.__name__)
        self.sys = platform.system()
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.cache_path = cache_path
        self.remote_path = os.path.normpath(remote_path)
        self.client, self.sftp = self.open_sftp()
        self.attributes = meta.LruCache()
        self.directories = meta.LruCache()
        self.manager = fs.CacheManager(self.cache_path, max_disk_size_mb=40)
        self.ops = FileOpsLock()

    def start_thread_pool(self, parallel):
        self.tls = dict()
        self.taskpool = ThreadPoolExecutor(
            max_workers=parallel, thread_name_prefix='oxfs-pool')

    def start_cache_updater(self, config):
        self.updater = CacheUpdater(self, config.cache_timeout)
        if config.auto_cache:
            self.updater.run()

    def spawnvpe(self):
        p = sys.argv
        if self.password:
            p.append('--password')
            p.append(base64.b64encode(self.password.encode()).decode())

        p.remove('--daemon')
        subprocess.Popen(p, env=os.environ)

    def getpass(self):
        if self.password:
            return self.password
        prompt = '''{}@{}'s password: '''.format(self.user, self.host)
        self.password = getpass.getpass(prompt)
        return self.password

    def open_sftp(self):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.load_system_host_keys()
        if not self.password:
            try:
                client.connect(self.host, port=self.port, username=self.user)
                return client, client.open_sftp()
            except paramiko.ssh_exception.AuthenticationException:
                self.getpass()

        try:
            client.connect(self.host, port=self.port,
                           username=self.user, password=self.getpass())
        except paramiko.ssh_exception.AuthenticationException as e:
            print('Permission denied.')
            self.logger.exception(e)
            sys.exit(1)
        return client, client.open_sftp()

    def current_thread_sftp(self):
        tid = threading.get_ident()
        curr = self.tls.get(tid)
        if curr is None:
            curr = dict()
            self.tls[tid] = curr

        sftp = curr.get('sftp')
        if sftp is not None:
            return sftp

        client, sftp = self.open_sftp()
        curr['sftp'] = sftp
        curr['client'] = client
        return sftp

    def cachefile(self, path, renew=True):
        key = self.manager.cachefile(path)
        if renew:
            self.manager.renew(key)
        return key

    def remotepath(self, path):
        return os.path.normpath(os.path.join(self.remote_path, path[1:]))

    def syncfile(self, sftp, path):
        cachefile = self.cachefile(path, False)
        st = sftp.lstat(path)
        if st.st_size > self.manager.maxsize:
            return False

        self.logger.info('syncfile {}'.format(path))
        tmpfile = cachefile + '.tmpfile'
        sftp.get(path, tmpfile)
        os.rename(tmpfile, cachefile)
        self.manager.put(cachefile)
        return True

    def _getfile(self, path):
        if self.ops.trylock(path):
            cachefile = self.cachefile(path, False)
            if not os.path.exists(cachefile):
                self.syncfile(self.current_thread_sftp(), path)
            self.ops.unlock(path)

    @staticmethod
    def extract(attr):
        return dict((key, getattr(attr, key)) for key in (
            'st_atime', 'st_gid', 'st_mode', 'st_mtime', 'st_size', 'st_uid'))

    def chmod(self, path, mode):
        path = self.remotepath(path)
        self.sftp.chmod(path, mode)
        self.attributes.remove(path)

    def chown(self, path, uid, gid):
        path = self.remotepath(path)
        try:
            self.sftp.chown(path, uid, gid)
        except Exception as e:
            self.logger.error(e)
        self.attributes.remove(path)

    def create(self, path, mode):
        path = self.remotepath(path)
        cachefile = self.cachefile(path, False)
        self.ops.lock(path)
        open(cachefile, 'wb').close()
        self.sftp.open(path, 'wb').close()
        self.attributes.remove(path)
        self.directories.remove(os.path.dirname(path))
        self.ops.unlock(path)
        return 0

    def getattr(self, path, fh=None):
        path = self.remotepath(path)
        attr = self.attributes.get(path)
        if attr is not None:
            if ENOENT == attr:
                raise FuseOSError(ENOENT)
            return attr

        try:
            attr = self.extract(self.sftp.lstat(path))
            self.attributes.put(path, attr)
            self.logger.debug('sftp getattr {}, attr {}'.format(path, attr))
            return attr
        except:
            self.attributes.put(path, ENOENT)
            raise FuseOSError(ENOENT)

    def mkdir(self, path, mode):
        path = self.remotepath(path)
        self.sftp.mkdir(path, mode)
        self.attributes.remove(path)
        self.directories.remove(os.path.dirname(path))
        return 0

    def read(self, path, size, offset, fh):
        path = self.remotepath(path)
        cachefile = self.cachefile(path)
        if self.ops.trylock(path):
            if os.path.exists(cachefile):
                with open(cachefile, 'rb') as infile:
                    infile.seek(offset, 0)
                    readed = infile.read(size)
                self.ops.unlock(path)
                return readed
            self.ops.unlock(path)

        if not self.ops.locked(path):
            self.taskpool.submit(self._getfile, path)

        with self.sftp.open(path, 'rb') as infile:
            infile.seek(offset, 0)
            return infile.read(size)

    def readdir(self, path, fh=None):
        path = self.remotepath(path)
        entries = self.directories.get(path)
        if entries is None:
            entries = self.sftp.listdir(path)
            self.directories.put(path, entries)

        return entries + ['.', '..']

    def readlink(self, path):
        path = self.remotepath(path)
        return self.sftp.readlink(path)

    def rename(self, old, new):
        old = self.remotepath(old)
        new = self.remotepath(new)
        self.logger.info('rename {} {}'.format(old, new))
        self.sftp.rename(old, new)

        self.ops.lock(old)
        self.manager.pop(self.cachefile(old, False))
        self.attributes.remove(old)
        self.directories.remove(os.path.dirname(old))
        self.ops.unlock(old)

        self.ops.lock(new)
        self.manager.pop(self.cachefile(new, False))
        self.attributes.remove(new)
        self.directories.remove(os.path.dirname(new))
        self.ops.unlock(new)
        return 0

    def rmdir(self, path):
        path = self.remotepath(path)
        self.sftp.rmdir(path)
        self.attributes.remove(path)
        self.directories.remove(os.path.dirname(path))
        return 0

    def symlink(self, target, source):
        target = self.remotepath(target)
        source = self.remotepath(source)
        # 'creates a symlink `target -> source` (e.g. ln -sf source target)'
        self.sftp.symlink(source, target)
        self.attributes.remove(target)
        self.directories.remove(os.path.dirname(target))
        return 0

    def truncate(self, path, length, fh=None):
        path = self.remotepath(path)
        cachefile = self.cachefile(path, False)
        self.ops.lock(path)
        if not os.path.exists(cachefile):
            self.syncfile(self.sftp, path)

        os.truncate(cachefile, length)
        self.attributes.put(path, self.extract(os.lstat(cachefile)))
        self.ops.unlock(path)
        self.manager.put(cachefile)
        self.sftp.truncate(path, length)

    def unlink(self, path):
        path = self.remotepath(path)
        self.sftp.unlink(path)
        self.ops.lock(path)
        self.manager.pop(self.cachefile(path, False))
        self.attributes.remove(path)
        self.directories.remove(os.path.dirname(path))
        self.ops.unlock(path)
        return 0

    def utimens(self, path, times=None):
        path = self.remotepath(path)
        self.sftp.utime(path, times)
        self.attributes.remove(path)
        return 0

    def _write(self, path, data, offset):
        sftp = self.current_thread_sftp()
        with sftp.open(path, 'rb+') as outfile:
            outfile.seek(offset, 0)
            outfile.write(data)

    def write(self, path, data, offset, fh):
        path = self.remotepath(path)
        cachefile = self.cachefile(path, False)
        self.ops.lock(path)
        if not os.path.exists(cachefile):
            self.syncfile(self.sftp, path)

        with open(cachefile, 'rb+') as outfile:
            outfile.seek(offset, 0)
            outfile.write(data)

        self.attributes.put(path, self.extract(os.lstat(cachefile)))
        self.ops.unlock(path)
        self.taskpool.submit(self._write, path, data, offset)
        self.manager.put(cachefile)
        return len(data)

    def destroy(self, path):
        self.updater.shutdown()
        self.taskpool.shutdown()
        self.sftp.close()
        self.client.close()
        for curr in self.tls.values():
            client = curr.get('client')
            sftp = curr.get('sftp')
            if sftp is not None:
                sftp.close()
                client.close()

    def fuse_main(self, mount_point):
        self.__class__.__name__ = 'oxfs'
        if 'Darwin' == self.sys:
            fuse = FUSE(self, mount_point, foreground=True, nothreads=True,
                        allow_other=True, auto_cache=True,
                        uid=os.getuid(), gid=os.getgid(),
                        defer_permissions=True, kill_on_unmount=True,
                        noappledouble=True, noapplexattr=True,
                        nosuid=True, nobrowse=True, volname=self.host)
        elif 'Linux' == self.sys:
            fuse = FUSE(self, mount_point, foreground=True, nothreads=True,
                        allow_other=True, auto_cache=True,
                        uid=os.getuid(), gid=os.getgid(),
                        auto_unmount=True)
        else:
            self.logger.error('not supported system, {}'.format(self.sys))
            sys.exit()


class Config:
    def __init__(self, parser):
        self.parser = parser
        self.host = None
        self.user = None
        self.mount_point = None
        self.cache_path = None
        self.daemon = False
        self.auto_cache = False

        self.password = None
        self.ssh_port = 22
        self.cache_timeout = 30
        self.parallel = multiprocessing.cpu_count() * 4
        self.remote_path = '/'
        self.filename = None
        self.level = logging.WARN
        self.fmt = '[%(asctime)s][%(levelname)s][%(filename)s -- %(funcName)s():%(lineno)s][%(message)s]'

    def parse(self):
        args = self.parser.parse_args()
        if not args.host:
            self.parser.print_help()
            sys.exit()
        if not args.mount_point:
            self.parser.print_help()
            sys.exit()
        if not args.cache_path:
            self.parser.print_help()
            sys.exit()

        if '@' not in args.host:
            self.parser.print_help()
            sys.exit()

        self.user, _, self.host = args.host.partition('@')
        self.cache_path = os.path.abspath(args.cache_path)
        self.mount_point = os.path.abspath(args.mount_point)

        if args.remote_path:
            self.remote_path = args.remote_path

        if args.ssh_port:
            self.ssh_port = args.ssh_port

        if args.password:
            self.password = base64.b64decode(args.password.encode()).decode()

        if args.cache_timeout:
            self.cache_timeout = args.cache_timeout

        if args.parallel:
            self.parallel = args.parallel

        if args.logging:
            self.filename = args.logging

        if args.auto_cache:
            self.auto_cache = True

        if args.verbose:
            self.level = logging.INFO

        if args.daemon:
            self.daemon = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', dest='host',
                        help='ssh host (example: root@127.0.0.1)')
    parser.add_argument('--password', dest='password',
                        help=argparse.SUPPRESS)
    parser.add_argument('--ssh-port', dest='ssh_port', type=int,
                        help='ssh port (defaut: 22)')
    parser.add_argument('--cache-timeout', dest='cache_timeout', type=int,
                        help='cache timeout (default: 30s)')
    parser.add_argument('--parallel', dest='parallel', type=int,
                        help='parallel (default: equal to cpu count)')
    parser.add_argument('--mount-point', dest='mount_point',
                        help='mount point')
    parser.add_argument('--remote-path', dest='remote_path',
                        help='remote path (default: /)')
    parser.add_argument('--cache-path', dest='cache_path',
                        help='cache path')
    parser.add_argument('--logging', dest='logging',
                        help='logging file')
    parser.add_argument('--daemon', dest='daemon', action='store_true',
                        help='daemon')
    parser.add_argument('--auto-cache', dest='auto_cache', action='store_true',
                        help='auto update cache')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                        help='debug info')

    config = Config(parser)
    config.parse()

    logging.basicConfig(level=config.level,
                        format=config.fmt,
                        filename=config.filename)

    fs = Oxfs(host=config.host,
              user=config.user,
              cache_path=config.cache_path,
              remote_path=config.remote_path,
              port=config.ssh_port,
              password=config.password)

    if config.daemon:
        fs.spawnvpe()
        sys.exit()

    fs.start_thread_pool(config.parallel)
    fs.start_cache_updater(config)
    fs.fuse_main(config.mount_point)


if __name__ == '__main__':
    main()
