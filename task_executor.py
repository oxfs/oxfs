#!/usr/bin/env python

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
            task = self.q.get()
            task.func(*task.args)
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
