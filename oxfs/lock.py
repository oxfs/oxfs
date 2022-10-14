#!/usr/bin/env python

import threading
import xxhash


class Lock:
    def __init__(self, max_locks=2048):
        self.locks = [threading.Lock() for _ in range(0, max_locks)]

    def lockid(self, path):
        return xxhash.xxh64_intdigest(path) % len(self.locks)

    def lock(self, path):
        self.locks[self.lockid(path)].acquire()

    def unlock(self, path):
        self.locks[self.lockid(path)].release()

    def trylock(self, path):
        return self.locks[self.lockid(path)].acquire(False)

    def locked(self, path):
        return self.locks[self.lockid(path)].locked()
