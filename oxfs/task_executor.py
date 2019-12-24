#!/usr/bin/env python

import logging
import threading
from queue import Queue

class Task(object):
    def __init__(self, taskid, func, *args):
        self.logger = logging.getLogger('task_executor')
        self.func = func
        self.args = args
        self.taskid = taskid

    def execute(self, local_data):
        args = ()
        args += (local_data, )
        args += self.args
        try:
            self.func(*args)
        except Exception as e:
            self.logger.exception(e)


class TaskExecutor(object):
    def __init__(self):
        self.local_data = dict()
        self.queue = Queue()
        self.empty = threading.Event()
        self.running = True
        self.thread = threading.Thread(target=self.loop, args=())
        self.thread.start()

    def submit(self, task):
        self.empty.clear()
        self.queue.put(task)

    def loop(self):
        while self.running:
            task = self.queue.get()
            task.execute(self.local_data)
            while not self.queue.empty():
                task = self.queue.get()
                task.execute(self.local_data)
            self.empty.set()

    def join(self):
        self.thread.join()

    def _shutdown(self, local_data):
        self.running = False
        hook = local_data.get('exit_hook')
        if hook is not None:
            hook(self.local_data)

    def shutdown(self):
        task = Task(0, self._shutdown)
        self.submit(task)

    def wait(self):
        self.empty.wait()

class TaskExecutorService(object):
    def __init__(self, max_workers):
        self.max_workers = max_workers
        self.workers = []
        for i in range(0, self.max_workers):
            self.workers.append(TaskExecutor())

    def submit(self, task):
        worker = self.workers[task.taskid % self.max_workers]
        worker.submit(task)

    def shutdown(self):
        for worker in self.workers:
            worker.shutdown()

    def wait(self, taskid):
        worker = self.workers[taskid % self.max_workers]
        worker.wait()
