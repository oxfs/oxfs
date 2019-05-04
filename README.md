
# Table of Contents

1.  [oxfs](#org3b9f42a)
    1.  [mount](#orga05af0b)
    2.  [setting](#org5cb9dd6)
        1.  [spacemacs](#orga8cf891)
        2.  [vim](#org24ce34a)


<a id="org3b9f42a"></a>

# oxfs

-   A simple sftp filesystem with powerfull cache.


<a id="orga05af0b"></a>

## mount

    $ mkdir remote
    $ oxfs -s user@xxx.xxx.xxx.xxx -m remote -p /tmp/oxfs


<a id="org5cb9dd6"></a>

## setting


<a id="orga8cf891"></a>

### spacemacs

    (setq make-backup-files nil) ; stop creating backup~ files
    (setq auto-save-default nil) ; stop creating #autosave# files
    (setq create-lockfiles nil)


<a id="org24ce34a"></a>

### vim

    set nobackup       "no backup files
    set nowritebackup  "only in case you don't want a backup file while editing
    set noswapfile     "no swap files

