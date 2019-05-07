
# Table of Contents

1.  [oxfs](#org0c701db)
    1.  [mount](#org3592eb9)
    2.  [setting](#orgd787a39)
        1.  [vim](#org8ada354)
        2.  [emacs](#orge6c462e)


<a id="org0c701db"></a>

# oxfs

-   A simple sftp filesystem with powerful cache.


<a id="org3592eb9"></a>

## mount

    $ oxfs --help
     usage: oxfs [-h] [-s HOST] [-m MOUNT_POINT] [-r REMOTE_PATH] [-p CACHE_PATH]
                 [-l LOGGING] [-d] [-v]
    
     optional arguments:
       -h, --help            show this help message and exit
       -s HOST, --host HOST  ssh host (for example: root@127.0.0.0.1)
       -m MOUNT_POINT, --mount_point MOUNT_POINT
                             mount point
       -r REMOTE_PATH, --remote_path REMOTE_PATH
                             remote path, default: /
       -p CACHE_PATH, --cache_path CACHE_PATH
                             oxfs files cache path
       -l LOGGING, --logging LOGGING
                             set log file, default: /tmp/oxfs.log
       -d, --daemon          run in background
       -v, --verbose         print verbose info
    
    $ mkdir remote
    $ oxfs -s user@xxx.xxx.xxx.xxx -m remote -r /home/oxfs -p /tmp/oxfs


<a id="orgd787a39"></a>

## setting


<a id="org8ada354"></a>

### vim

    set nobackup       "no backup files
    set nowritebackup  "only in case you don't want a backup file while editing
    set noswapfile     "no swap files


<a id="orge6c462e"></a>

### emacs

    (setq make-backup-files nil) ; stop creating backup~ files
    (setq auto-save-default nil) ; stop creating #autosave# files
    (setq create-lockfiles nil)

