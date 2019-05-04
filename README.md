
# Table of Contents

1.  [oxfs](#org8a75fd8)
    1.  [mount oxfs](#org4459aff)
    2.  [suggest setting](#org688b047)
        1.  [spacemacs](#org6be2793)
        2.  [vim](#org62f2338)


<a id="org8a75fd8"></a>

# oxfs

-   A simple sftp filesystem with powerfull cache.


<a id="org4459aff"></a>

## mount oxfs

```
    $ sudo python3 oxfs.py -s user@xxx.xxx.xxx.xxx -m mount -p /tmp/oxfs
```

<a id="org688b047"></a>

## suggest setting


<a id="org6be2793"></a>

### spacemacs

```elisp
    (setq make-backup-files nil) ; stop creating backup~ files
    (setq auto-save-default nil) ; stop creating #autosave# files
    (setq create-lockfiles nil)
```


<a id="org62f2338"></a>

### vim

```vim
    set nobackup       "no backup files
    set nowritebackup  "only in case you don't want a backup file while editing
    set noswapfile     "no swap files
```

