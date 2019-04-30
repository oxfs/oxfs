#!/usr/bin/env python

import time
from queue import Queue
from threading import Thread

class Task(object):
    def __init__(self, taskid, func, *args):
        self.func = func
        self.args = args
        self.taskid = taskid

class TaskExecutor(object):
    def __init__(self):
        self.running = True
        self.q = Queue()
        self.t = Thread(target=self.loop, args=())
        self.t.start()

    def shutdown(self):
        self.running = False

    def join(self):
        self.t.join()

    def loop(self):
        while self.running:
            # task = self.q.get(block=True, timeout=1000)
            while not self.q.empty():
                task = self.q.get()
                task.func(*task.args)

class TaskExecutorService(object):
    def __init__(self, max_workers):
        self.max_workers = max_workers
        self.workers = []
        for i in range(0, self.max_workers):
            self.workers.append(TaskExecutor())

    def submit(self, task):
        worker = self.workers[task.taskid % self.max_workers]
        worker.q.put(task)

    def shutdown(self):
        for x in self.workers:
            x.shutdown()
            x.join()

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
