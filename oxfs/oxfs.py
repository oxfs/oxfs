#!/usr/bin/env python

import argparse
import base64
import getpass
import logging
import multiprocessing
import os
import paramiko
import platform
import subprocess
import sys
import xxhash

from errno import ENOENT
from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

from oxfs.apiserver import OxfsApi
from oxfs.cache import meta, fs
from oxfs.cache.meta import synchronized
from oxfs.task_executor import TaskExecutorService, Task
from oxfs.updater import CacheUpdater


class Oxfs(LoggingMixIn, Operations):
    '''
    A dead simple, fast SFTP file system. Home: https://oxfs.io/

    You need to be able to login to remote host without entering a password.
    '''

    def __init__(self, host, user, cache_path, remote_path, port=22, password=None):
        self.logger = logging.getLogger('oxfs')
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
        self.manager = fs.CacheManager(self.cache_path)

    def start_thread_pool(self, parallel):
        self.taskpool = TaskExecutorService(parallel)

    def start_apiserver(self, port):
        self.apiserver = OxfsApi(self)
        self.apiserver.run(port)

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

    def current_thread_sftp(self, thread_local_data):
        sftp = thread_local_data.get('sftp')
        if sftp is not None:
            return sftp

        client, sftp = self.open_sftp()
        thread_local_data['sftp'] = sftp
        thread_local_data['client'] = client
        # thread terminate hook
        thread_local_data['exit_hook'] = self.sftp_destroy
        return thread_local_data['sftp']

    def sftp_destroy(self, thread_local_data):
        client = thread_local_data.get('client')
        sftp = thread_local_data.get('sftp')
        if sftp is not None:
            sftp.close()
            client.close()

    def cachefile(self, path, renew=True):
        key = self.manager.cachefile(path)
        if renew:
            self.manager.renew(key)
        return key

    def remotepath(self, path):
        return os.path.normpath(os.path.join(self.remote_path, path[1:]))

    @synchronized
    def trylock(self, path):
        lockfile = path + '.lock'
        if os.path.exists(lockfile):
            return False
        open(lockfile, 'wb').close()
        return True

    @synchronized
    def unlock(self, path):
        lockfile = path + '.lock'
        os.remove(lockfile)

    def getfile(self, thread_local_data, path):
        cachefile = self.cachefile(path, False)
        if os.path.exists(cachefile):
            return False

        sftp = self.current_thread_sftp(thread_local_data)
        st = sftp.lstat(path)
        if st.st_size > self.manager.maxsize:
            return False

        if not self.trylock(cachefile):
            self.logger.info('getfile lock failed {}'.format(path))
            return False

        self.logger.info('getfile {}'.format(path))
        tmpfile = cachefile + '.tmpfile'
        sftp.get(path, tmpfile)
        os.rename(tmpfile, cachefile)
        self.manager.put(cachefile)
        self.unlock(cachefile)
        return True

    def extract(self, attr):
        return dict((key, getattr(attr, key)) for key in (
            'st_atime', 'st_gid', 'st_mode', 'st_mtime', 'st_size', 'st_uid'))

    def chmod(self, path, mode):
        path = self.remotepath(path)
        status = self.sftp.chmod(path, mode)
        self.attributes.remove(path)
        return status

    def chown(self, path, uid, gid):
        path = self.remotepath(path)
        status = self.sftp.chown(path, uid, gid)
        self.attributes.remove(path)
        return status

    def create(self, path, mode):
        path = self.remotepath(path)
        self.logger.info('create {}, ignore mode {}'.format(path, mode))
        cachefile = self.cachefile(path, False)
        open(cachefile, 'wb').close()
        self.sftp.open(path, 'wb').close()
        self.attributes.remove(path)
        self.directories.remove(os.path.dirname(path))
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
            self.logger.info('sftp getattr {}, attr {}'.format(path, attr))
            return attr
        except:
            self.attributes.put(path, ENOENT)
            raise FuseOSError(ENOENT)

    def mkdir(self, path, mode):
        path = self.remotepath(path)
        self.logger.info('mkdir {}'.format(path))
        status = self.sftp.mkdir(path, mode)
        self.attributes.remove(path)
        self.directories.remove(os.path.dirname(path))
        return status

    def valid(self, cache, path):
        try:
            return os.lstat(cache).st_size == self.attributes.get(path)['st_size']
        except:
            return False

    def read(self, path, size, offset, fh):
        path = self.remotepath(path)
        cachefile = self.cachefile(path)
        if self.valid(cachefile, path):
            with open(cachefile, 'rb') as infile:
                infile.seek(offset, 0)
                return infile.read(size)

        task = Task(xxhash.xxh64(path).intdigest(), self.getfile, path)
        self.taskpool.submit(task)
        with self.sftp.open(path, 'rb') as infile:
            infile.seek(offset, 0)
            return infile.read(size)

    def readdir(self, path, fh=None):
        path = self.remotepath(path)
        entries = self.directories.get(path)
        if entries is None:
            entries = self.sftp.listdir(path)
            self.directories.put(path, entries)
            self.logger.info('sftp readdir {} = {}'.format(path, entries))

        return entries + ['.', '..']

    def readlink(self, path):
        path = self.remotepath(path)
        return self.sftp.readlink(path)

    def rename(self, old, new):
        old = self.remotepath(old)
        new = self.remotepath(new)
        self.logger.info('rename {} {}'.format(old, new))
        self.taskpool.wait(xxhash.xxh64(old).intdigest())
        try:
            self.unlink(new)
        except Exception as e:
            self.logger.debug(e)

        status = self.sftp.rename(old, new)
        self.attributes.remove(old)
        self.attributes.remove(new)
        self.directories.remove(os.path.dirname(old))
        self.directories.remove(os.path.dirname(new))
        return status

    def rmdir(self, path):
        path = self.remotepath(path)
        self.logger.info('rmdir {}'.format(path))
        status = self.sftp.rmdir(path)
        self.attributes.remove(path)
        self.directories.remove(os.path.dirname(path))
        return status

    def symlink(self, target, source):
        target = self.remotepath(target)
        source = self.remotepath(source)
        'creates a symlink `target -> source` (e.g. ln -sf source target)'
        self.logger.info('sftp symlink {} {}'.format(source, target))
        self.sftp.symlink(source, target)
        self.attributes.remove(target)
        self.directories.remove(os.path.dirname(target))
        return 0

    def _truncate(self, thread_local_data, path, length):
        self.logger.info('sftp truncate {}'.format(path))
        sftp = self.current_thread_sftp(thread_local_data)
        return sftp.truncate(path, length)

    def truncate(self, path, length, fh=None):
        realpath = self.remotepath(path)
        cachefile = self.cachefile(realpath, False)
        if not os.path.exists(cachefile):
            self.sync_getfile(path, cachefile)

        status = os.truncate(cachefile, length)
        self.manager.put(cachefile)
        self.logger.info(self.extract(os.lstat(cachefile)))
        self.attributes.put(realpath, self.extract(os.lstat(cachefile)))
        task = Task(xxhash.xxh64(realpath).intdigest(),
                    self._truncate, realpath, length)
        self.taskpool.submit(task)
        return status

    def unlink(self, path):
        path = self.remotepath(path)
        self.logger.info('unlink {}'.format(path))
        self.manager.pop(self.cachefile(path, False))
        self.sftp.unlink(path)
        self.attributes.remove(path)
        self.directories.remove(os.path.dirname(path))
        return 0

    def utimens(self, path, times=None):
        path = self.remotepath(path)
        self.logger.info('utimens {}'.format(path))
        status = self.sftp.utime(path, times)
        self.attributes.remove(path)
        return status

    def _write(self, thread_local_data, path, data, offset):
        sftp = self.current_thread_sftp(thread_local_data)
        with sftp.open(path, 'rb+') as outfile:
            outfile.seek(offset, 0)
            outfile.write(data)

        return len(data)

    def sync_getfile(self, path, cachefile):
        realpath = self.remotepath(path)
        if self.getattr(path)['st_size'] == 0:
            self.create(cachefile, 'wb')
            return
        task = Task(xxhash.xxh64(realpath).intdigest(),
                    self.getfile, realpath)
        self.taskpool.submit(task)
        self.taskpool.wait(xxhash.xxh64(realpath).intdigest())

    def write(self, path, data, offset, fh):
        realpath = self.remotepath(path)
        cachefile = self.cachefile(realpath, False)
        if not os.path.exists(cachefile):
            self.sync_getfile(path, cachefile)

        with open(cachefile, 'rb+') as outfile:
            outfile.seek(offset, 0)
            outfile.write(data)

        self.attributes.put(realpath, self.extract(os.lstat(cachefile)))
        task = Task(xxhash.xxh64(realpath).intdigest(),
                    self._write, realpath, data, offset)
        self.taskpool.submit(task)
        self.manager.put(cachefile)
        return len(data)

    def destroy(self, path):
        self.updater.shutdown()
        self.taskpool.shutdown()
        self.sftp.close()
        self.client.close()

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
        self.apiserver_port = 10010
        self.cache_timeout = 30
        self.parallel = multiprocessing.cpu_count()
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

        if args.apiserver_port:
            self.apiserver_port = args.apiserver_port

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
    parser.add_argument('--apiserver-port', dest='apiserver_port', type=int,
                        help='apiserver port (default: 10010)')
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
    fs.start_apiserver(config.apiserver_port)
    fs.start_cache_updater(config)
    fs.fuse_main(config.mount_point)


if __name__ == '__main__':
    main()
