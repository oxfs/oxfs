## Oxfs

<p>
<img alt="GitHub" src="https://img.shields.io/github/license/RainMark/oxfs">
<img alt="PyPI" src="https://img.shields.io/pypi/v/oxfs">
<img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/oxfs">
<img alt="PyPI - Wheel" src="https://img.shields.io/pypi/wheel/oxfs">
<img alt="GitHub last commit" src="https://img.shields.io/github/last-commit/RainMark/oxfs">
</p>

Oxfs is a user-space network file system similar to SSHFS, and the underlying data transfer is based on the SFTP protocol. Oxfs introduces an asynchronous refresh policy to solve the jamming problem caused by the mismatch between network speed and user operation file speed. When Oxfs writes a file, it first writes to the local cache file and submits an asynchronous update task to update the content to the remote host. Similarly, when reading a file, it is preferred to read from a local cache file. Oxfs's data cache eventually falls to disk, and even if it is remounted, the history cache can still be used.

### Get Started

#### Ubuntu/Debian

```bash
$ sudo apt-get install python3.7
$ python3.7 -m pip install oxfs --user
```

#### macOS

```bash
$ brew install python3
$ mkdir ~/.venv
$ python3 -m venv ~/.venv/oxfs
$ source ~/.venv/oxfs/bin/activate
$ pip install oxfs
```

### Mount

```bash
$ oxfs --host mark@x.x.x.x --remote-path /home/mark --mount-point mark --cache-path ~/.oxfs --logging /tmp/oxfs.log --daemon
$ cd mark
```

### Exit

```bash
$ umount mark
```

### More

```bash
$ oxfs
usage: oxfs [-h] [--host HOST] [--ssh-port SSH_PORT]
            [--apiserver-port APISERVER_PORT] [--mount-point MOUNT_POINT]
            [--remote-path REMOTE_PATH] [--cache-path CACHE_PATH]
            [--logging LOGGING] [--daemon] [-v]

optional arguments:
  -h, --help            show this help message and exit
  --host HOST           ssh host (example: root@127.0.0.1)
  --ssh-port SSH_PORT   ssh port (defaut: 22)
  --apiserver-port APISERVER_PORT
                        apiserver port (default: 10010)
  --mount-point MOUNT_POINT
                        mount point
  --remote-path REMOTE_PATH
                        remote path (default: /)
  --cache-path CACHE_PATH
                        cache path
  --logging LOGGING     logging file
  --daemon              daemon
  -v, --verbose         debug info
```

### Performance

#### Environment

- Ping Latency: 190 ms
- VPS: BandwagonHost (SPECIAL 10G KVM PROMO V3 - LOS ANGELES - CN2)
- VPS Operating System: Centos 7 x86_64 bbr
- Host: Intel® Core™ i5-4210U CPU @ 1.70GHz × 4 , SSD 125.5 GB
- Host Operating System: Ubuntu 18.04.2 LTS x86_64 reno

####  Method

```bash
$ iozone -R -b output.xls -p -c -r 1k -s 20m -l 1 -u 1
```

- Oxfs vs Sshfs

![](benchmark/oxfs-vs-sshfs.png)

- Sshfs performance
  - Sshfs enable the kernel cache by default, that's why re-read so fast.

![](benchmark/sshfs.png)

- Oxfs performance
  - Oxfs enable the fuse auto_cache.

![](benchmark/oxfs.png)

### Changelog

- release/0.3.0
  - [New] Add daemon support.
  - [New] Upgrade to flask-restx.
  - [Removed] Remove short argument.
  - [Fixed] Fix bugs with git operations.
  - [Fixed] Fix empty file write failed bug.
  - [Fixed] Fix mount permission issue.
- release/0.2.0
  - [New] Add restful API to refresh the cache.
- release/0.1.2
  - [Removed] Remove auto_unmount fuse parameter, some osxfuse do not support it.
  - [Deprecated] Disable the daemon parameter, turn on it in the future.

- release/0.1.1
  - [Added] enable the auto_cache by default.

- release/0.1.0
  - [Fixed] Fix the multi-thread bugs for rename operation.
