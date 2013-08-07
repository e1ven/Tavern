import json
import hashlib
import os
from keys import Keys
import collections
from collections import *
json.encoder.c_make_encoder = None
import pymongo
import pylzma
from ServerSettings import serversettings
import TavernUtils
from operator import itemgetter

class Envelope(object):

    class Payload(object):
        def __init__(self, initialdict):
            self.dict = OrderedDict(initialdict)

        def alphabetizeAllItems(self, oldobj):
            """
            To ensure our messages are reconstructable, the message, and all fields should be in alphabetical order
            """
            # Recursively loop through all the keys/items
            # If we can sort them, do so, if not, just return it.
            if isinstance(oldobj, collections.Mapping):
                oldlist = oldobj.keys()
                newdict = OrderedDict()

                for key in sorted(oldlist):
                    newdict[key] = self.alphabetizeAllItems(oldobj[key])
                return newdict

            elif isinstance(oldobj, collections.Sequence) and not isinstance(oldobj, str):
                newlist = []
                oldlist = sorted(oldobj)
                for row in oldlist:
                    newlist.append(self.alphabetizeAllItems(row))
                return newlist

            else:
                return oldobj

        def format(self):
            self.dict = self.alphabetizeAllItems(self.dict)

        def hash(self):
            self.format()
            h = hashlib.sha512()
            h.update(self.text().encode('utf-8'))
            return h.hexdigest()

        def text(self):
            self.format()
            newstr = json.dumps(self.dict, separators=(',', ':'))
            return newstr

        def validate(self):
            if 'author' not in self.dict:
                server.logger.debug("No Author Information")
                return False
            else:
                if 'pubkey' not in self.dict['author']:
                    server.logger.debug("No Pubkey line in Author info")
                    return False
            self.format()
            print("formatted")
            return True

    class MessageRevision(Payload):
        def validate(self):
            if not Envelope.Payload(self.dict).validate():
                server.logger.debug("Super does not Validate")
                return False
            if not 'regarding' in self.dict:
                server.logger.debug("Message Revisions must refer to an original message.")
                return False
            return True

    class Message(Payload):
        def validate(self):
            if not Envelope.Payload(self.dict).validate():
                server.logger.debug("Super does not Validate")
                return False
            if 'subject' not in self.dict:
                server.logger.debug("No subject")
                return False
            if 'body' not in self.dict:
                server.logger.debug("No Body")
                return False
            if 'topic' not in self.dict:
                server.logger.debug("No Topic")
                return False
            if 'formatting' not in self.dict:
                server.logger.debug("No Formatting")
                return False
            if self.dict['formatting'] not in ['markdown', 'plaintext']:
                server.logger.debug("Formatting not in pre-approved list")
                return False
            if 'topic' in self.dict:
                if len(self.dict['topic']) > 200:
                    server.logger.debug("Topic too long")
                    return False
            if 'subject' in self.dict:
                if len(self.dict['subject']) > 200:
                    server.logger.debug("Subject too long")
                    return False
            return True

    class PrivateMessage(Payload):
        def validate(self):
            if not Envelope.Payload(self.dict).validate():
                server.logger.debug("Super does not Validate")
                return False
            if 'to' not in self.dict:
                server.logger.debug("No 'to' field")
                return False
            # if 'topic' in self.dict:
            #     server.logger.debug("Topic not allowed in privmessage.")
            #     return False
            return True

    class Rating(Payload):
        def validate(self):
            if not Envelope.Payload(self.dict).validate():
                server.logger.debug("Super fails")
                return False
            if 'rating' not in self.dict:
                server.logger.debug("No rating number")
                return False
            if self.dict['rating'] not in [-1, 0, 1]:
                server.logger.debug(
                    "Evelope ratings must be either -1, 1, or 0.")
                return False

            return True

    class UserTrust(Payload):
        def validate(self):
            if not Envelope.Payload(self.dict).validate():
                return False
            if 'trusted_pubkey' not in self.dict:
                server.logger.debug("No trusted_pubkey to set trust for.")
                return False
            if self.dict['trust'] not in [-100, 0, 100]:
                server.logger.debug(
                    "Message ratings must be either -100, 0, or 100")
                return False
            if 'topic' not in self.dict:
                server.logger.debug(
                    "User trust must be per topic. Please include a topic.")
                return False
            return True

    def validate(self):
        #Validate an Envelope
        #Check headers
        if 'envelope' not in self.dict:
            server.logger.debug("Invalid Envelope. No Header")
            return False

        #Ensure we have 1 and only 1 author signature stamp
        stamps = self.dict['envelope']['stamps']
        foundauthor = 0
        for stamp in stamps:
            if stamp['class'] == "author":
                foundauthor += 1
                # Ensure that the Author stamp matches the Author in the Payload section!
                if stamp['pubkey'] != self.dict['envelope']['payload']['author']['pubkey']:
                    server.logger.debug(
                        "Author stamp must match payload author key.")
                    return False

        if foundauthor == 0:
            server.logger.debug("No author stamp.")
            return False
        if foundauthor > 1:
            server.logger.debug("Too Many author stamps")
            return False

        #Ensure Every stamp validates.
        stamps = self.dict['envelope']['stamps']
        for stamp in stamps:

            # Retrieve the key, ensure it's valid.
            stampkey = Keys(pub=stamp['pubkey'])
            if stampkey is None:
                server.logger.debug("Key is invalid.")
                return False

            # Ensure it matches the signature.
            if stampkey.verify_string(stringtoverify=self.payload.text(), signature=stamp['signature']) != True:
                server.logger.debug("Signature Failed to verify for stamp :: " +
                                   stamp['class'] + " :: " + stamp['pubkey'])
                return False


            # If they specify a proof-of-work in the stamp, make sure it's valid.
            if 'proof-of-work' in stamp:
                    proof = stamp['proof-of-work']['proof']
                    difficulty = stamp['proof-of-work']['difficulty']
                    if stamp['proof-of-work']['class'] == 'sha256':
                        result = TavernUtils.checkWork(self.payload.hash(),proof,difficulty)
                        if result == False:
                            server.logger.debug("Proof of work cannot be verified.")
                            return False
                    else:
                        server.logger.debug("Proof of work in unrecognized format. Ignoring.")
                        

        # Check for a valid useragent
        try:
            if len(self.dict['envelope']['payload']['author']['useragent']['name']) < 1:
                server.logger.debug("Bad Useragent name")
                return False
            if not isinstance(self.dict['envelope']['payload']['author']['useragent']['version'], int):
                if not isinstance(self.dict['envelope']['payload']['author']['useragent']['version'], float):
                    server.logger.debug(
                        "Bad Useragent version must be a float or integer")
                    return False
        except:
            server.logger.debug("Bad Useragent")
            return False

        #Do this last, so we don't waste time if the stamps are bad.
        if not self.payload.validate():
            server.logger.info("Payload does not validate.")
            return False

        return True


    @TavernUtils.memorise(ttl=serversettings.settings['cache']['templates']['seconds'], maxsize=serversettings.settings['cache']['templates']['size'])
    def countChildren(self):
        print("Looking for childen for :" + self.payload.hash())
        results =  server.db.unsafe.count('envelopes',{"envelope.local.ancestors":self.payload.hash()})
        print(results)
        return results


    def addAncestor(self,ancestorid):
        """
        A new Ancestor has been found (parent, parent's parent, etc) for this message.
        Set it locally, and tell all my children, if I have any
        """
        ancestor = Envelope()
        if ancestor.loadmongo(mongo_id=ancestorid):
            

            if not 'ancestors' in self.dict['envelope']['local']:
                self.dict['envelope']['local']['ancestors'] = []

            if not 'ancestors' in ancestor.dict['envelope']['local']:
                ancestorlist = []
            else:
                ancestorlist = ancestor.dict['envelope']['local']['ancestors']

            if ancestorid not in ancestorlist:
                ancestorlist.append(ancestorid)

            for listedancestor in ancestorlist:
                if listedancestor not in self.dict['envelope']['local']['ancestors']:
                    self.dict['envelope']['local']['ancestors'].append(listedancestor)

            # Now, tell our children, if we have any
            if 'citedby' in self.dict['envelope']['local']:
                for childid in self.dict['envelope']['local']['citedby']:
                    child = Envelope()
                    if child.loadmongo(mongo_id=childid):
                        child.addAncestor(ancestorid)
                        child.saveMongo()

            self.saveMongo()

    def addcite(self, citedby):
        """
        Another message has referenced this one. Mark it in the local area.
        """
        if not 'citedby' in self.dict['envelope']['local']:
            self.dict['envelope']['local']['citedby'] = []
        if citedby not in self.dict['envelope']['local']['citedby']:
            self.dict['envelope']['local']['citedby'].append(citedby)
        self.saveMongo()

    def addEdit(self,editid):
        """
        Another message has come in that says it's an edit of this one.
        """
        newmessage = Envelope()
        if newmessage.loadmongo(mongo_id=editid):

            # Store the hash of the edit in this message.
            if not 'edits' in self.dict['envelope']['local']:
                self.dict['envelope']['local']['edits'] = []

            # Store the hash, and the 'date' the message gives us.
            if 'time_added' in newmessage.dict['envelope']['local']:
                dt = newmessage.dict['envelope']['local']['time_added']
            else:
                dt = TavernUtils.inttime()

            edit = (newmessage.payload.hash(), dt)
            self.dict['envelope']['local']['edits'].append(edit)

            # Sort by time received
            self.dict['envelope']['local']['edits'] = sorted(self.dict['envelope']['local']['edits'], key=itemgetter(1))

            # If the new text is newer than the original message, change the display text.
            if newmessage.dict['envelope']['local']['time_added'] > self.dict['envelope']['local']['time_added']:
                if 'editedbody' in newmessage.dict['envelope']['local']:
                    self.dict['envelope']['local']['editedbody'] = newmessage.dict['envelope']['local']['editedbody']
                else:
                    self.dict['envelope']['local']['editedbody'] = server.formatEnvelope(newmessage.dict)['envelope']['local']['formattedbody']
            self.saveMongo()

            # If we're saving this edit onto another edit, propogate up to tell the original message.
            if self.dict['envelope']['payload']['class'] == "messagerevision":
                parentmessage = Envelope()
                if parentmessage.loadmongo(mongo_id=self.dict['envelope']['payload']['regarding']):
                    print("Going upstream.")
                    parentmessage.addEdit(editid)


    def addcite(self, citedby):
        """
        Another message has referenced this one. Mark it in the local area.
        """
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
                elif self.dict['envelope']['payload']['class'] == "messagerating":
                    self.payload = Envelope.Rating(
                        self.dict['envelope']['payload'])
                elif self.dict['envelope']['payload']['class'] == "usertrust":
                    self.payload = Envelope.UserTrust(
                        self.dict['envelope']['payload'])
                elif self.dict['envelope']['payload']['class'] == "privatemessage":
                    self.payload = Envelope.PrivateMessage(
                        self.dict['envelope']['payload'])
                elif self.dict['envelope']['payload']['class'] == "messagerevision":
                    self.payload = Envelope.MessageRevision(
                        self.dict['envelope']['payload'])
                else:
                    server.logger.info("Rejecting message of class " + self.dict['envelope']['payload'])
                    return False
            return True
    
    def loaddict(self,importdict):
        newstr = json.dumps(importdict, separators=(',', ':'))
        return self.loadstring(newstr) 

    def loadstring(self, importstring):
        self.dict = json.loads(importstring, object_pairs_hook=collections.OrderedDict, object_hook=collections.OrderedDict)
        return self.registerpayload()

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
        from Server import server
        env = server.db.unsafe.find_one('envelopes',{'_id': mongo_id})
        if env is None:
            return False
        else:
            return self.loaddict(env)

    def reloadmongo(self):
        self.loadmongo(self.payload.hash())
        return self.registerpayload()

    def reloadfile(self):
        self.loadfile(self.payload.hash() + ".7zTavernEnvelope")
        return self.registerpayload()

    def text(self,striplocal=False):
        self.payload.format()
        if striplocal==True:
            if 'local' in self.dict['envelope']:
                del self.dict['envelope']['local']

        self.dict['envelope']['payload'] = self.payload.dict
        self.dict['envelope']['local']['payload_sha512'] = self.payload.hash()
        newstr = json.dumps(self.dict, separators=(',', ':'))
        return newstr

    def prettytext(self,striplocal=False):
        self.payload.format()
        if striplocal==True:
            if 'local' in self.dict['envelope']:
                del self.dict['envelope']['local']
                
        self.dict['envelope']['payload'] = self.payload.dict
        self.dict['envelope']['local']['payload_sha512'] = self.payload.hash()
        newstr = json.dumps(self.dict, indent=2, separators=(', ', ': '))
        return newstr

    def savefile(self, directory='.'):
        self.payload.format()
        self.dict['envelope']['payload'] = self.payload.dict
        self.dict['envelope']['local']['payload_sha512'] = self.payload.hash()

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
        self.dict['envelope']['local']['payload_sha512'] = self.payload.hash()

        from Server import server
        self.dict['_id'] = self.payload.hash()
        server.db.unsafe.save('envelopes', self.dict)

from Server import server
