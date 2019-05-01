#!/usr/bin/env python

import time
from task_executor import Task, TaskExecutorService

if '__main__' == __name__:
    pool = TaskExecutorService(3)
    def myprint(msg):
        print(msg)

    def mysleep(length, msg):
        time.sleep(length)
        print(msg)

    taskid = int(time.time() * 1000)
    task = Task(taskid, myprint, 'xxx')
    pool.submit(task)

    taskid = int(time.time() * 1000)
    sleep_task = Task(taskid, mysleep, 2, 'wake up')
    pool.submit(sleep_task)

    taskid = int(time.time() * 1000)
    task = Task(taskid, myprint, 'xxx')
    pool.submit(task)

    pool.shutdown()
