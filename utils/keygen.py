import multiprocessing
from multiprocessing.managers import BaseManager
from multiprocessing import Queue

import platform
from time import sleep

import json
import signal
import pdb
import os
import time
import tavern


class KeyGenerator(object):

    """
    Pre-generates GPG keys.
    """

    def __init__(self):
        """Initialize our main module, and create threads."""
        # Create a hopper for all the emails to reside in
        self.procs = []
        self.server = tavern.Server()
        print("Init KeyGen")

    def start(self):
        """Start up all subprocs."""
        count = 0

        self.stop()
        self.procs = []
        for proc in range(0, self.server.serversettings.settings['KeyGenerator']['workers']):
            newproc = multiprocessing.Process(target=self.GenerateAsNeeded, args=())
            self.procs.append(newproc)
            print(" Created KeyGenerator - " + str(proc))

        for proc in self.procs:
            proc.start()
            print(" Started KeyGenerator" + str(count))
            count += 1

    def stop(self):
        """Terminate all subprocs."""
        count = 0
        self.server.logger.info("Stopping KeyGenerator")
        for proc in self.procs:
            proc.terminate()
            self.server.logger.info(" Stopped KeyGenerator " + str(count))
            count += 1
        self.server.logger.info("All KeyGenerator threads ceased.")

    def CreateUnusedLK(self):
        """Create a LockedKey with a random password."""
        lk = tavern.LockedKey()
        password = lk.generate(random=True)
        unusedkey = {'encryptedprivkey': lk.encryptedprivkey, 'pubkey': lk.pubkey, 'password': password}
        return unusedkey

    def GenerateAsNeeded(self):
        """Watch to see if the queue gets low, and then add users."""

        while True:

            # Create a LK, and push it up.
            # If the queue is full, we'll block, so we just wait.
            unusedkey = self.CreateUnusedLK()
            self.server.unusedkeycache.put(unusedkey, block=True)
            # print(self.server.unusedkeycache.qsize())
