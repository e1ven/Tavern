import json
import hashlib
import os
from keys import Keys
import collections
from collections import *
json.encoder.c_make_encoder = None
import pymongo
import pylzma
from serversettings import serversettings


class Envelope(object):

    class Payload(object):
        def __init__(self, initialdict):
            self.dict = OrderedDict(initialdict)

        def alphabetizeAllItems(self,oldobj):
            """
            To ensure our messages are reconstructable, the message, and all fields should be in alphabetical order
            """
            # Recursively loop through all the keys/items
            # If we can sort them, do so, if not, just return it.
            if isinstance(oldobj,collections.Mapping):
                oldlist = oldobj.keys()
                newdict = OrderedDict()
            
                for key in sorted(oldlist):
                    newdict[key] = self.alphabetizeAllItems(oldobj[key])
                return newdict

            elif isinstance(oldobj,collections.Sequence) and not isinstance(oldobj,str):
                newlist = []
                oldlist = sorted(oldobj)
                for row in newlist:
                    newlist.append(self.alphabetizeAllItems(row))
                return newlist

            else:
                return oldobj

        def format(self):
            self.dict = self.alphabetizeAllItems(self.dict)
            print("Formatted- New dict is -- " + str(self.dict))
        def hash(self):
            self.format()
            h = hashlib.sha512()
            h.update(self.text().encode('utf-8'))
            # server.logger.info "Hashing --" + self.text() + "--"
            return h.hexdigest()

        def text(self):
            self.format()
            newstr = json.dumps(self.dict, separators=(',', ':'))
            return newstr

        def validate(self):
            if 'author' not in self.dict:
                server.logger.info("No Author Information")
                return False
            else:
                if 'pubkey' not in self.dict['author']:
                    server.logger.info("No Pubkey line in Author info")
                    return False
            self.format()
            return True

    class Message(Payload):
        def validate(self):
            if not Envelope.Payload(self.dict).validate():
                server.logger.info("Super does not Validate")
                return False
            if 'subject' not in self.dict:
                server.logger.info("No subject")
                return False
            if 'body' not in self.dict:
                server.logger.info("No Body")
                return False
            if 'topic' not in self.dict:
                server.logger.info("No Topic")
                return False
            if 'formatting' not in self.dict:
                server.logger.info("No Formatting")
                return False
            if 'topic' in self.dict:
                if len(self.dict['topic']) > 200:
                    server.logger.info("Topic too long")
                    return False
            if 'subject' in self.dict:
                if len(self.dict['subject']) > 200:
                    server.logger.info("Subject too long")
                    return False
            return True

    class PrivateMessage(Payload):
        def validate(self):
            if not Envelope.Payload(self.dict).validate():
                server.logger.info("Super does not Validate")
                return False
            if 'to' not in self.dict:
                server.logger.info("No 'to' field")
                return False
            # if 'topic' in self.dict:
            #     server.logger.info("Topic not allowed in privmessage.")
            #     return False
            return True

    class Rating(Payload):
        def validate(self):
            if not Envelope.Payload(self.dict).validate():
                server.logger.info("Super fails")
                return False
            if 'rating' not in self.dict:
                server.logger.info("No rating number")
                return False
            if self.dict['rating'] not in [-1, 0, 1]:
                server.logger.info(
                    "Evelope ratings must be either -1, 1, or 0.")
                return False

            return True

    class UserTrust(Payload):
        def validate(self):
            if not Envelope.Payload(self.dict).validate():
                return False
            if 'trusted_pubkey' not in self.dict:
                server.logger.info("No trusted_pubkey to set trust for.")
                return False
            if self.dict['trust'] not in [-100, 0, 100]:
                server.logger.info(
                    "Message ratings must be either -100, 0, or 100")
                return False
            if 'topic' not in self.dict:
                server.logger.info(
                    "User trust must be per topic. Please include a topic.")
                return False
            return True

    def validate(self):
        #Validate an Envelope
        #Check headers
        if 'envelope' not in self.dict:
            server.logger.info("Invalid Envelope. No Header")
            return False

        if self.dict['envelope']['payload_sha512'] != self.payload.hash():
            server.logger.info("Possible tampering. SHA doesn't match. Abort.")
            return False

        #Ensure we have 1 and only 1 author signature stamp
        stamps = self.dict['envelope']['stamps']
        foundauthor = 0
        for stamp in stamps:
            if stamp['class'] == "author":
                foundauthor += 1
                # Ensure that the Author stamp matches the Author in the Payload section!
                if stamp['pubkey'] != self.dict['envelope']['payload']['author']['pubkey']:
                    server.logger.info(
                        "Author stamp must match payload author key.")
                    return False

        if foundauthor == 0:
            server.logger.info("No author stamp.")
            return False
        if foundauthor > 1:
            server.logger.info("Too Many author stamps")
            return False

        #Ensure Every stamp validates.
        stamps = self.dict['envelope']['stamps']
        for stamp in stamps:

            # Retrieve the key, ensure it's valid.
            stampkey = Keys(pub=stamp['pubkey'])
            if stampkey is None:
                server.logger.info("Key is invalid.")
                return False

            # Ensure it matches the signature.
            if stampkey.verify_string(stringtoverify=self.payload.text(), signature=stamp['signature']) != True:
                server.logger.info("Signature Failed to verify for stamp :: " +
                                   stamp['class'] + " :: " + stamp['pubkey'])
                return False

        # Check for a valid useragent
        try:
            if len(self.dict['envelope']['payload']['author']['useragent']['name']) < 1:
                server.logger.info("Bad Useragent name")
                return False
            if not isinstance(self.dict['envelope']['payload']['author']['useragent']['version'], int):
                if not isinstance(self.dict['envelope']['payload']['author']['useragent']['version'], float):
                    server.logger.info(
                        "Bad Useragent version must be a float or integer")
                    return False
        except:
            server.logger.info("Bad Useragent")
            return False

        #Do this last, so we don't waste time if the stamps are bad.
        if not self.payload.validate():
            server.logger.info("Payload does not validate.")
            return False

        return True

    def addcite(self, citedby):
        if not 'citedby' in self.dict['envelope']['local']:
            self.dict['envelope']['local']['citedby'] = []
        if citedby not in self.dict['envelope']['local']['citedby']:
            self.dict['envelope']['local']['citedby'].append(citedby)
        self.saveMongo()

    class binary(object):
        def __init__(self, sha512):
            self.dict = OrderedDict()
            self.dict['sha_512'] = sha512

    def __init__(self):
        self.dict = OrderedDict()
        self.dict['envelope'] = OrderedDict()
        self.dict['envelope']['payload'] = OrderedDict()
        self.dict['envelope']['local'] = OrderedDict()
        self.dict['envelope']['local']['citedby'] = []
        self.dict['envelope']['stamps'] = []

        self.payload = Envelope.Payload(self.dict['envelope']['payload'])

    def registerpayload(self):
        if 'payload' in self.dict['envelope']:
            if 'class' in self.dict['envelope']['payload']:
                if self.dict['envelope']['payload']['class'] == "message":
                    self.payload = Envelope.Message(
                        self.dict['envelope']['payload'])
                elif self.dict['envelope']['payload']['class'] == "rating":
                    self.payload = Envelope.Rating(
                        self.dict['envelope']['payload'])
                elif self.dict['envelope']['payload']['class'] == "usertrust":
                    self.payload = Envelope.UserTrust(
                        self.dict['envelope']['payload'])
                elif self.dict['envelope']['payload']['class'] == "privatemessage":
                    self.payload = Envelope.PrivateMessage(
                        self.dict['envelope']['payload'])

    def loadstring(self, importstring):
        self.dict = json.loads(importstring, object_pairs_hook=collections.OrderedDict, object_hook=collections.OrderedDict)
        self.registerpayload()

    def loadfile(self, filename):

        #Determine the file extension to see how to parse it.
        basename, ext = os.path.splitext(filename)
        filehandle = open(filename, 'rb')
        filecontents = filehandle.read()
        if (ext == '.7zTavernEnvelope'):
            #7zip'd JSON
            filecontents = pylzma.decompress(filecontents)
            filecontents = filecontents.decode('utf-8')
        filehandle.close()
        self.loadstring(filecontents)

    def loadmongo(self, mongo_id):
        from server import server
        env = server.db.unsafe.find_one('envelopes',
            {'_id': mongo_id})
        if env is None:
            return False
        else:
            self.dict = env
            self.registerpayload()
            return True

    def reloadfile(self):
        self.loadfile(self.payload.hash() + ".7zTavernEnvelope")
        self.registerpayload()

    def text(self):
        self.payload.format()
        self.dict['envelope']['payload'] = self.payload.dict
        self.dict['envelope']['payload_sha512'] = self.payload.hash()
        newstr = json.dumps(self.dict, separators=(',', ':'))
        return newstr

    def prettytext(self):
        self.payload.format()
        self.dict['envelope']['payload'] = self.payload.dict
        self.dict['envelope']['payload_sha512'] = self.payload.hash()
        newstr = json.dumps(self.dict, indent=2, separators=(', ', ': '))
        return newstr

    def savefile(self, directory='.'):
        self.payload.format()
        self.dict['envelope']['payload'] = self.payload.dict
        self.dict['envelope']['payload_sha512'] = self.payload.hash()

        #Compress the whole internal Envelope for saving.
        compressed = pylzma.compress(self.text(), dictionary=10, fastBytes=255)
        # server.logger.info "Compressed size " + str(sys.getsizeof(compressed))
        # server.logger.info "Full Size " + str(sys.getsizeof(self.dict))

        #We want to name this file to the SHA512 of the payload contents, so it is consistant across servers.
        filehandle = open(
            directory + "/" + self.payload.hash() + ".7zTavernEnvelope", 'wb')
        filehandle.write(compressed)
        filehandle.close()

    def saveMongo(self):
        self.payload.format()
        self.dict['envelope']['payload'] = self.payload.dict
        self.dict['envelope']['payload_sha512'] = self.payload.hash()

        from server import server
        print("Dump - Pre save -- " + self.payload.text())
        print("Saving message to mongo - My id is " + self.dict.get('_id','unknown'))
        self.dict['_id'] = self.payload.hash()
        print("assigned new id -" + self.payload.hash() )

        server.db.unsafe.save('envelopes',self.dict)

from server import server
