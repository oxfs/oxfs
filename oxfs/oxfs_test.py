#!/usr/bin/env python

import os
from oxfs import OXFS

if '__main__' == __name__:
    oxfs = OXFS('198.181.37.111', 'root', '/tmp/oxfs')

    try:
        response = oxfs.getattr('/root/Test/testfile')
        print(response)
    except Exception as e:
        print(e)

    try:
        response = oxfs.readdir('/root/Test')
        print(response)
    except Exception as e:
        print(e)

    try:
        response = oxfs.create('/root/Test/testfile', 775)
        print(response)
    except Exception as e:
        print(e)

    try:
        response = oxfs.readdir('/root/Test')
        print(response)
    except Exception as e:
        print(e)

    try:
        response = oxfs.getattr('/root/Test/testfile')
        print(response)
    except Exception as e:
        print(e)

    try:
        data = 'foo'
        response = oxfs.write('/root/Test/testfile', data.encode(), 0, None)
        print(response)

        response = oxfs.write('/root/Test/testfile', data.encode(), 3, None)
        print(response)
    except Exception as e:
        print(e)

    try:
        response = oxfs.getattr('/root/Test/testfile')
        print(response)
    except Exception as e:
        print(e)

    try:
        response = oxfs.readdir('/root/Test')
        print(response)
    except Exception as e:
        print(e)

    try:
        response = oxfs.read('/root/Test/testfile', 1, 0, None)
        print(response)
        response = oxfs.read('/root/Test/testfile', 10, 0, None)
        print(response)
    except Exception as e:
        print(e)

    os.system('rm -rf /tmp/oxfs/*')
    oxfs.destroy('/')
