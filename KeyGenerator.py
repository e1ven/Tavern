import multiprocessing
from multiprocessing.managers import BaseManager
import platform
from time import sleep

import json
import signal
import pdb
import os
import time
from Envelope import Envelope
import Server
server = Server.Server()
from lockedkey import LockedKey
import TavernUtils


class KeyGenerator(object):
    """
    Pre-generates GPG keys.
    """

    def __init__(self):
        """
        Initialize our main module, and create threads.
        """
        # Create a hopper for all the emails to reside in
        self.procs = []

    def start(self):
        """
        Start up all subprocs
        """
        count = 0

        self.stop()
        self.procs = []
        for proc in range(0, server.serversettings.settings['KeyGenerator']['workers']):
            newproc = multiprocessing.Process(target=self.GenerateAsNeeded, args=())
            self.procs.append(newproc)
            server.logger.info(" Created KeyGenerator - " + str(proc))

        for proc in self.procs:
            proc.start()
            server.logger.info(" Started KeyGenerator" + str(count))
            count += 1

    def stop(self):
        """
        Terminate all subprocs
        """
        count = 0
        server.logger.info("Stopping KeyGenerator")
        for proc in self.procs:
            proc.terminate()
            server.logger.info(" Stopped KeyGenerator " + str(count))
            count += 1
        server.logger.info("All KeyGenerator threads ceased.")

    def CreateUnusedLK(self):
        """
        Create a LockedKey with a random password.
        """
        lk = LockedKey()
        password = lk.generate(random=True)   
        unusedkey = {'key':lk,'password':password}
        return unusedkey

    def PopulateUnusedKeyCache(self):
        """
        Pre-generate several lockedKeys. Save them.
        This is faster.
        """
        while not server.unusedkeycache.full():
            unusedkey = self.CreateUnusedLK()
            server.unusedkeycache.put(unusedkey)


    def GenerateAsNeeded(self):
        """
        Watch to see if the queue gets low, and then add users
        """

        count = 0
        # Grab some emails from the stack
        while 1:
            self.PopulateUnusedKeyCache();
            sleeptime = server.serversettings.settings['KeyGenerator']['sleep']
            time.sleep(sleeptime)
