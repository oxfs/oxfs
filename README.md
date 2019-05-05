
# Table of Contents

1.  [oxfs](#org981004c)
    1.  [mount](#org187fda0)
    2.  [setting](#org34809f6)
        1.  [vim](#orgaf019e8)
        2.  [emacs](#org3765feb)


<a id="org981004c"></a>

# oxfs

-   A simple sftp filesystem with powerful cache.


<a id="org187fda0"></a>

## mount

    $ mkdir remote
    $ oxfs -s user@xxx.xxx.xxx.xxx -m remote -p /tmp/oxfs


<a id="org34809f6"></a>

## setting


<a id="orgaf019e8"></a>

### vim

    set nobackup       "no backup files
    set nowritebackup  "only in case you don't want a backup file while editing
    set noswapfile     "no swap files


<a id="org3765feb"></a>

### emacs

    (setq make-backup-files nil) ; stop creating backup~ files
    (setq auto-save-default nil) ; stop creating #autosave# files
    (setq create-lockfiles nil)

