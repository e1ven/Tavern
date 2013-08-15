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
import magic
import imghdr
import Image
import gridfs
from bs4 import BeautifulSoup


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
            self.format()
            return True

    class MessageRevision(Payload):
        def validate(self):
            if not Envelope.Payload(self.dict).validate():
                server.logger.debug("Super does not Validate")
                return False
            if not 'regarding' in self.dict:
                server.logger.debug("Message Revisions must refer to an original message.")
                return False

            # See if we have the original. If so, is the right type?
            e = Envelope()
            if e.loadmongo(self.dict['regarding']):
                print("We have the original message this revision refers to")
                if e.dict['envelope']['payload']['class'] != 'message':
                    print("Message Revisions must refer to a message.")
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


            # See if we have the original. If so, is the right type?
            if 'regarding' in self.dict:
                e = Envelope()
                if e.loadmongo(self.dict['regarding']):
                    print("We have the original message this revision refers to")
                    if e.dict['envelope']['payload']['class'] != 'message':
                        print("Message can only reply to other messages.")
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
        """
        Ensures an envelope is valid, legal, and according to spec.
        """
        self.registerpayload()
        #Check headers
        if 'envelope' not in self.dict:
            server.logger.debug("Invalid Envelope. No Header")
            return False

        # Ensure we have 1 and only 1 author signature stamp
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

        # Ensure Every stamp validates.
        stamps = self.dict['envelope']['stamps']
        for stamp in stamps:

            if 'keydetails' not in stamp:
                server.logger.debug("Key information is unavailable.")
                return False
                
            if stamp['keydetails']['format'] != 'gpg':
                server.logger.debug("Key not in acceptable container format.")
                return False

            if stamp['keydetails']['algorithm'] not in ['ElGamal','RSA','DSA']:
                server.logger.debug(
                    "Key does not use an acceptable algorithm.")
                return False
            
            if stamp['keydetails']['algorithm'] in ['ElGamal','RSA','DSA']:
                if int(stamp['keydetails']['length']) < 2048:
                    server.logger.debug("Key is too small.")
                    return False
            elif stamp['keydetails']['algorithm'] is 'ECDSA':
                if int(stamp['keydetails']['length']) < 233:
                    server.logger.debug("Key is too small.")
                    return False

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
        

        # It's OK if they don't include a user-agent, but not if they include a bad one.
        if 'useragent' in self.dict['envelope']['payload']['author']:
            if not 'name' in  self.dict['envelope']['payload']['author']['useragent']:
                server.logger.debug("If you supply a user agent, it must have a valid name")
                return False
            if not isinstance(self.dict['envelope']['payload']['author']['useragent']['version'], int) and not isinstance(self.dict['envelope']['payload']['author']['useragent']['version'], float):
                    server.logger.debug(
                        "Bad Useragent version must be a float or integer")
                    return False
        else:
            server.logger.debug("Bad Useragent")
            return False

        #Do this last, so we don't waste time if the stamps are bad.
        if not self.payload.validate():
            server.logger.info("Payload does not validate.")
            return False

        return True

    def munge(self):
        """
        Set things in the local block of the message.
        """

        #If we don't have a local section, add one.
        #This isn't inside of validation since it's legal not to have one.
        #if 'local' not in c.dict['envelope']:
        self.dict['envelope']['local'] = OrderedDict()

        # Don't caclulate the SHA_512 each time. Store it in local, so we can reference it going forward.
        self.dict['envelope']['local']['payload_sha512'] = self.payload.hash()

        #Pull out serverstamps.
        stamps = self.dict['envelope']['stamps']

        highestPOW = 0
        for stamp in stamps:

            # Find the author of the message, save it where it's easy to find later.
            if stamp['class'] == "author":
                self.dict['envelope']['local']['author'] = stamp

            # Calculate highest proof of work difficuly.
            # Only use proof-of-work class sha256 for now.
            if 'proof-of-work' in stamp:
                if stamp['proof-of-work']['class'] == 'sha256':
                    if stamp['proof-of-work']['difficulty'] >  highestPOW:
                        highestPOW = stamp['proof-of-work']['difficulty']
            
        self.dict['envelope']['local']['highestPOW'] = highestPOW

        # Copy a lowercase/simplified version of the topic into 'local', so StarTrek and startrek show up together.
        if 'topic' in self.dict['envelope']['payload']:
            self.dict['envelope']['local']['sorttopic'] = server.sorttopic(
                self.dict['envelope']['payload']['topic'])


        # Get a short version of the subject, for display.
        if 'subject' in self.dict['envelope']['payload']:
            temp_short = self.dict['envelope']['payload'][
                'subject'][:50].rstrip()
            self.dict['envelope']['local']['short_subject'] = server.urlize(temp_short)
        # Get a short version of the body, to use as a preview.
        # First line only.
        if 'body' in self.dict['envelope']['payload']:
            short_body = self.dict['envelope']['payload'][
                'body'].split('\n', 1)[0][:60].strip()
            self.dict['envelope']['local'][
                'short_body'] = short_body


        # Process any binaries which are listed in the envelope
        if 'binaries' in self.dict['envelope']['payload']:
            self.mungebins()

        if 'body' in self.dict['envelope']['payload']:
            formattedbody = server.formatText(text=self.dict['envelope']['payload']['body'], formatting=self.dict['envelope']['payload']['formatting'])
            self.dict['envelope']['local']['formattedbody'] = formattedbody


            # Check for any Embeddable (Youtube, Vimeo, etc) Links.
            # Don't check a given message more than once.
            # Iterate through the list of possible embeddables.

            # cap the number of URLs we can embed.
            foundurls = 0                    
            if not 'embed' in self.dict['envelope']['local']:
                self.dict['envelope']['local']['embed'] = []


            soup = BeautifulSoup(formattedbody,"html.parser")
            for href in soup.findAll('a'):
                result = server.external.lookup(href.get('href'))
                if result is not None and foundurls < serversettings.settings['maxembeddedurls']:
                    self.dict['envelope']['local']['embed'].append(result)
                    foundurls += 1

        self.dict['envelope']['local']['author_wordhash'] = server.wordlist.wordhash(self.dict['envelope']['local']['author']['pubkey'])


        if '_id' in self.dict:
            del(self.dict['_id'])

    def mungebins(self):
        """
        Store detailed information for any binaries.
        Create Thumbnails for all images.
        """
        attachmentList = []
        for binary in self.dict['envelope']['payload']['binaries']:
            if 'sha_512' in binary:
                fname = binary['sha_512']
                try:
                    attachment = server.bin_GridFS.get_last_version(
                        filename=fname)
                    if 'filename' not in binary:
                        binary['filename'] = "unknown_file"
                    #In order to display an image, it must be of the right MIME type, the right size, it must open in
                    #Python and be a valid image.
                    attachment.seek(0)
                    detected_mime = magic.from_buffer(
                        attachment.read(serversettings.settings['max-upload-preview-size']), mime=True).decode('utf-8')
                    displayable = False
                    if attachment.length < serversettings.settings['max-upload-preview-size']:  # Don't try to make a preview if it's > 10M
                        if 'content_type' in binary:
                            if binary['content_type'].rsplit('/')[0].lower() == "image":
                                attachment.seek(0)
                                imagetype = imghdr.what(
                                    'ignoreme', h=attachment.read())
                                acceptable_images = [
                                    'gif', 'jpeg', 'jpg', 'png', 'bmp']
                                if imagetype in acceptable_images:
                                    #If we pass -all- the tests, create a thumb once.
                                    displayable = binary[
                                        'sha_512'] + "-thumb"
                                    if not server.bin_GridFS.exists(filename=displayable):
                                        attachment.seek(0)
                                        im = Image.open(attachment)

                                        # Check to see if we need to rotate the image
                                        # This is caused by iPhones saving the orientation

                                        if hasattr(im, '_getexif'):  # only present in JPEGs
                                                e = im._getexif()       # returns None if no EXIF data
                                                if e is not None:
                                                    exif = dict(e.items())
                                                    if 'Orientation' in exif:
                                                        orientation = exif[
                                                            'Orientation']

                                                        if orientation == 3:
                                                            image = im.transpose(Image.ROTATE_180)
                                                        elif orientation == 6:
                                                            image = im.transpose(Image.ROTATE_270)
                                                        elif orientation == 8:
                                                            image = im.transpose(Image.ROTATE_90)

                                        # resize if nec.
                                        if im.size[0] > 640:
                                            imAspect = float(im.size[1]) / float(im.size[0])
                                            newx = 640
                                            newy = int(640 * imAspect)
                                            im = im.resize((newx, newy), Image.ANTIALIAS)
                                        if im.size[1] > 480:
                                            imAspect = float(im.size[0]) / float(im.size[1])
                                            newy = 480
                                            newx = int(480 * imAspect)
                                            im = im.resize((newx, newy), Image.ANTIALIAS)

                                        thumbnail = server.bin_GridFS.new_file(filename=displayable)
                                        im.save(thumbnail, format='png')
                                        thumbnail.close()
                    
                    attachmentdesc = {'sha_512': binary['sha_512'], 'filename': binary['filename'], 'filesize': attachment.length, 'displayable': displayable, 'detected_mime': detected_mime}
                    attachmentList.append(attachmentdesc)
                except gridfs.errors.NoFile:
                    self.logger.debug("Error, attachment gone ;(")


        # Create an attachment list - Store the calculated filesize in it.
        # We can't trust the one the client gives us, but since it's in the payload, we can't modify it.
        self.dict['envelope']['local']['attachmentlist'] = attachmentList

        # Check for a medialink for FBOG, Pinterest, etc.
        # Leave off if it doesn't exist
        if len(attachmentList) > 0:
            medialink = None
            for attachment in attachmentList:
                if attachment['displayable'] is not False:
                    self.dict['envelope']['local']['medialink'] = medialink
                    break



    @TavernUtils.memorise(ttl=serversettings.settings['cache']['templates']['seconds'], maxsize=serversettings.settings['cache']['templates']['size'])
    def countChildren(self):
        print("Looking for childen for :" + self.payload.hash())
        results =  server.db.unsafe.count('envelopes',{"envelope.local.ancestors":self.payload.hash()})
        return results

    def addStamp(self,stampclass,keys,passkey=None,**kwargs):
        """
        Adds a stamp of type `class` to the current envelope
        """


        if passkey != None:
            signature = keys.signstring(self.payload.text(), passkey)
        else:
            signature = keys.signstring(self.payload.text())


        # Generate the full stamp obj we will insert.
        fullstamp = {}
        fullstamp['class'] = stampclass
        fullstamp['keydetails'] = keys.keydetails
        fullstamp['pubkey'] = keys.pubkey
        fullstamp['signature'] = signature
        fullstamp['time_added'] = TavernUtils.inttime()

        # Copy in any passed values
        for key in kwargs.keys():
            # Remove the kwargs we know we already added
            if key not in ["stampclass","keys","passkey"]:
                fullstamp[key] = kwargs[key]

        proof = {}
        proof['class'] = 'sha256'
        proof['difficulty'] = serversettings.settings['proof-of-work-difficulty']
        proof['proof'] = TavernUtils.proveWork(self.payload.hash(),proof['difficulty'])
        fullstamp['proof-of-work'] = proof

        self.dict['envelope']['stamps'].append(fullstamp)



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
        Note - This will NOT recurse. Ensure a edit is an edit to the original, not an edit of an edit.
        """
        newmessage = Envelope()

        if not 'edits' in self.dict['envelope']['local']:
            self.dict['envelope']['local']['edits'] = []

        # Check to see if we already have this edit
        for edit in self.dict['envelope']['local']['edits']:
            if edit['envelope']['local']['payload_sha512'] == editid:
                # We already have this message
                print("We've already stored this edit.")
                return False

        if newmessage.loadmongo(mongo_id=editid):

            # Ensure the two messages have the same author. If not, abort.
            # Do this here, rather in validate, so we can receive them in either order.
            if self.dict['envelope']['local']['author']['pubkey'] != newmessage.dict['envelope']['local']['author']['pubkey']:
                print("Invalid Revision. Author pubkey must match original message.")
                return False  

            self.dict['envelope']['local']['edits'].append(newmessage.dict)
            
            # Order by Priority, then date if they match
            # This will ensure that ['edits'][-1] is the one we want to display.
            self.dict['envelope']['local']['edits'].sort(key=lambda e: (e['envelope']['local']['priority'], (e['envelope']['local']['time_added'])))
            self.saveMongo()
            return True

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
                    server.logger.info("Rejecting message of class " + self.dict['envelope']['payload']['class'])
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
        return self.loadmongo(self.payload.hash())

    def reloadfile(self):
        return self.loadfile(self.payload.hash() + ".7zTavernEnvelope")

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
