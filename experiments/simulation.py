import sys,os
# Allow imports from ..
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), os.pardir)))
import Server
import random
import os
from Envelope import Envelope
import hashlib
from User import User
from collections import OrderedDict
import ServerSettings
import time

#     rnd = random.SystemRandom().getrandbits(1024)
        # bytestr = initial.encode('utf-8')
        # intstr = int.from_bytes(bytestr,byteorder='big')
        # needed_bits = 1024 - intstr.bit_length()
        # padded_bitstr = intstr << needed_bits

        # working_str = 0
        # secret_machine = random.randrange(0,20)



class Node():
    def __init__(self):
        self.server = None
        self.servernum = None
        self.users = []

class Simulation():

    def setup(self):
        num_nodes = 10

        messages_per_server = 100

        # Ensure we have conf files for all our simulated nodes.
        # In particular, we want to make sure they all write to separate databases.

        for i in range(0,num_nodes):
            ss = ServerSettings.ServerSettings(settingsfile='tmpnode-'+str(i))
            # Give them each a unique DB
            ss.settings['dbname'] = 'tmp' + str(i)
            ss.settings['hostname'] = 'tmp' + str(i)
            ss.saveconfig()
            del(ss)

        # Create array of Nodes
        nodes = []
        for i in range(0,num_nodes):

            print("Creating server " + str(i))
            node = Node()
            node.server = Server.Server(settingsfile='tmpnode-'+str(i),slot=i)

            node.server.debug = False
            node.server.logger.setLevel("INFO")
            node.servernum = i
            nodes.append(node)



        for node in nodes:

            node.server.start()

            print("We have node - " + str(node.servernum))
            SHA512 = hashlib.sha512()
            SHA512.update(node.server.ServerKeys.pubkey.encode('utf-8'))
            print("Our keyhash is - " + SHA512.hexdigest())

            for count in range(0,messages_per_server):
                e = Envelope(srv=node.server)

                # Inserting the time so that each message is different.
                e.payload.dict['body'] = """This env was inserted into server: """ + str(node.servernum) + """
                at """ + str(time.time()) + """
                This is message #""" + str(count) + """
                Thanks!!
                """
                e.payload.dict['formatting'] = "markdown"
                e.payload.dict['class'] = "message"
                e.payload.dict['topic'] = "testmessage"
                e.payload.dict['subject'] = "Test from server: " + str(node.servernum)

                user = User()
                user.generate(AllowGuestKey=False)

                e.payload.dict['author'] = OrderedDict()
                e.payload.dict['author']['replyto'] = user.Keys['posted'][-1].pubkey
                e.payload.dict['author']['friendlyname'] = user.UserSettings['friendlyname']

                e.addStamp(stampclass='author',friendlyname=user.UserSettings['friendlyname'],keys=user.Keys['master'],passkey=user.passkey)

                msgid = node.server.receiveEnvelope(env=e)
                print("Sent " + msgid + "to server- " + str(node.servernum))

        # # Optionally shuffle.
        # random.shuffle(nodes)

        # for node in nodes:
        #     working_str = working_str ^ node['randombits']

        # # Convert back to string
        # unpadded_str = working_str >> needed_bits
        # reformed = unpadded_str.to_bytes(int(unpadded_str.bit_length()/8)+1,byteorder='big').decode('utf-8')

        # print(reformed)
        # print(reformed == initial)

def main():
    sim = Simulation()
    sim.setup()

if __name__ == "__main__":
    main()

