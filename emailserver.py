import smtplib

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
from server import server

class EmailServer(object):
    """
    Sends email from the mongo queue of emails.
    """ 
        
    def __init__(self):            
        """ 
        Initialize our main module, and create threads.
        """
        # Create a hopper for all the emails to reside in
        self.emails = multiprocessing.Queue()
        self.optouts = []
        self.procs = []
        if 'email' not in server.ServerSettings:
            self.makedefaults()


    def makedefaults(self):
        """
        Stick default settings in a file.
        """
        server.ServerSettings['email'] = {}
        server.ServerSettings['email']['sender'] = "noreply <noreply@example.com>"
        server.ServerSettings['email']['smtpserver'] = 'smtp.example.com'
        server.ServerSettings['email']['username'] = "user@example.com"
        server.ServerSettings['email']['password'] = "password"
        server.ServerSettings['email']['workers'] = multiprocessing.cpu_count() - 1
        server.ServerSettings['email']['saveinterval'] = 1000
        server.ServerSettings['email']['debug'] = True
        server.ServerSettings['email']['SSL'] = False
        server.ServerSettings['email']['port'] = 25
        server.ServerSettings['email']['newmailevery'] = 100
        server.ServerSettings['email']['sleeptime'] = 5
        server.ServerSettings['email']['authrequired'] = True

        server.saveconfig()

    def loadmail(self):
        """
        Load in the emails
        """

        for email in server.mongos['default']['optout-emails'].find():
            self.optouts.append(email['address'])


        # Move messages to an in-memory queue which can go to multiple processes
        for email in server.mongos['default']['notifications_queue'].find({'type':'email'}):
            if email['address'] not in self.optouts:
                self.emails.put(email)
            server.mongos['default']['notifications_queue'].remove(email)


    def start(self):
        """
        Start up all subprocs
        """
        count = 0

        self.kill()
        self.procs = []
        for proc in range(0,server.ServerSettings['email']['workers']):
            newproc = multiprocessing.Process(target=self.sendmail, args=())
            self.procs.append(newproc)
            server.logger.info(" Created Process - " + str(proc))

        for proc in self.procs:
             proc.start()
             server.logger.info(" Started " + str(count))
             count += 1

    def kill(self):
        """
        Terminate all subprocs
        """
        count = 0
        server.logger.info("stopping")
        for proc in self.procs:
             proc.terminate()
             server.logger.info(" Stopped " + str(count))
             count += 1
        server.logger.info("You are now free to turn off your computer.")


    def sendmail(self):
        """
        Actually connect to the server, and push out the message.
        """

    
        count = 0
        # Grab some emails from the stack
        while True:
            if not self.emails.empty():
                currentemail = self.emails.get(False)
                msg = MIMEMultipart('alternative')
                msg['Subject'] = currentemail['subject']
                msg['From'] = server.ServerSettings['email']['sender']
                msg['To'] = currentemail['address']

                # Create a  a new mail every X messages
                newmailevery = server.ServerSettings['email']['newmailevery']

                # Record the MIME types of both parts - text/plain and text/html.
                part1 = MIMEText(currentemail['text'], 'plain')
                part2 = MIMEText(currentemail['html'], 'html')

                # Attach parts into message container.
                # Do this in the Process, so it's local
                msg.attach(part1)
                msg.attach(part2)

                # Re-establish a connection every X.
                if count % newmailevery == 0:
                    if count > 0:
                        conn.close()
                    server.logger.info("Establishing Connection to emailserver " + server.ServerSettings['email']['smtpserver'])
                    if server.ServerSettings['email']['SSL'] == True:
                      conn = smtplib.SMTP_SSL(host=server.ServerSettings['email']['smtpserver'],port=server.ServerSettings['email']['port'])
                    else:
                      conn = smtplib.SMTP(host=server.ServerSettings['email']['smtpserver'],port=server.ServerSettings['email']['port'])

                    if server.ServerSettings['email']['authrequired'] == True:
                        conn.login(server.ServerSettings['email']['username'], server.ServerSettings['email']['password'])

                try:
                    conn.sendmail(server.ServerSettings['email']['sender'], currentemail['address'], msg.as_string())   
                finally:
                    count +=1
                    server.logger.info ("This thread has sent " + str(count))
            else:
                    sleeptime = server.ServerSettings['email']['sleeptime']
                    server.logger.info("Sleeping - " + str(sleeptime) + " seconds")
                    time.sleep(sleeptime)
        conn.close()  
