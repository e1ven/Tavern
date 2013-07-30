from collections import OrderedDict
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import multiprocessing
from multiprocessing.managers import BaseManager
import platform
from time import sleep

import json
import signal
import pdb
import os
import time
import random
from Envelope import Envelope
from Server import server
from ServerSettings import serversettings
from User import User
import TavernUtils


class UserGenerator(object):
    """
    Ensures we always have spare users to assign quickly.
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
        for proc in range(0, serversettings.settings['UserGenerator']['workers']):
            newproc = multiprocessing.Process(target=self.GenerateAsNeeded, args=())
            self.procs.append(newproc)
            server.logger.info(" Created UserGenerator - " + str(proc))

        for proc in self.procs:
            proc.start()
            server.logger.info(" Started UserGenerator" + str(count))
            count += 1

    def stop(self):
        """
        Terminate all subprocs
        """
        count = 0
        server.logger.info("Stopping UserGenerator")
        for proc in self.procs:
            proc.terminate()
            server.logger.info(" Stopped UserGenerator " + str(count))
            count += 1
        server.logger.info("All UserGenerator threads ceased.")


    # create a random-string user.
    def CreateUnusedUser(self):
        u = User()
        server.logger.debug("Making keys with a random password.")
        # Generate a random password with a random number of characters
        numcharacters = 100 + TavernUtils.randrange(1, 100)
        password = TavernUtils.randstr(numcharacters)
        u.generate(skipkeys=False, password=password)
        unuseduser = {'user':u,'password':password}
        return unuseduser

    # Pregenerate a few users, so we can hand them out quickly.
    def PopulateUnusedUserCache(self):
        while not server.unusedusercache.full():
            unuseduser = self.CreateUnusedUser()
            server.unusedusercache.put(unuseduser)


    def GenerateAsNeeded(self):
        """
        Watch to see if the queue gets low, and then add users
        """

        count = 0
        # Grab some emails from the stack
        while True:
            self.PopulateUnusedUserCache();
            sleeptime = serversettings.settings['UserGenerator']['sleep']
            time.sleep(sleeptime)
