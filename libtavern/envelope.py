import json
import os
import lzma
from collections import OrderedDict

# To detect/resize images
import magic

from bs4 import BeautifulSoup

import libtavern.baseobj
import libtavern.key
import libtavern.utils
import libtavern.topic

class Envelope(libtavern.baseobj.Baseobj):
    """
    An Envelope is the core unit of exchange in Tavern Ecosystem.
    Each bit of content - A Message, PM, or rating, is a type of envelope.
    The Envelope can contain any arbitrary data, but contains two elements.

        A Payload - The Payload is the content of the envelope, and can never be altered.
        An example of a Payload is the subject/body of a forum post.
        A hash of the payload is used to identify the entire envelope.

        Stamps- Stamps are signed bits of text which are added onto an envelope.
        They are assertions about the message, signed with a public key.
        An example might be 'This envelope passed through my server -Bob', or
            'This envelope contains a URL that is a virus -Mary', or
            'This envelope was posted with Tavernriffic 1.2.3'

    """

    def get_original(self):
        """
        Returns the original message, without any edits
        """
        env = Envelope()
        env.loadmongo(mongo_id=env.dict['envelope']['payload']['regarding'])
        return env


    def validate(self):
        """Ensures an envelope is valid, legal, and according to spec."""
        self.registerpayload()
        # Check headers
        if 'envelope' not in self.dict:
            self.server.logger.debug("Invalid Envelope. No Header")
            return False

        # Ensure we have 1 and only 1 author signature stamp
        stamps = self.dict['envelope']['stamps']
        foundauthor = 0
        for stamp in stamps:
            if stamp['class'] == "author":
                foundauthor += 1

        if foundauthor == 0:
            if self.dict['envelope']['payload']['class'] != 'privatemessage':
                self.server.logger.debug("No author stamp.")
                return False
        if foundauthor > 1:
            self.server.logger.debug("Too Many author stamps")
            return False

        # Ensure Every stamp validates.
        stamps = self.dict['envelope']['stamps']
        for stamp in stamps:

            if 'keyformat' not in stamp:
                self.server.logger.debug("Key format is not specififed.")
                return False

            if stamp['keyformat'] != 'gpg':
                self.server.logger.debug(
                    "Key not in acceptable container format.")
                return False

            # Retrieve the key, ensure it's valid.
            stampkey = libtavern.key.Key(pub=stamp['pubkey'])
            if stampkey is None:
                self.server.logger.debug("Key is invalid.")
                return False

            if stampkey.keydetails['algorithm'] not in ['ElGamal', 'RSA', 'DSA']:
                self.server.logger.debug(
                    "Key does not use an acceptable algorithm.")
                return False

            if stampkey.keydetails['algorithm'] in ['ElGamal', 'RSA', 'DSA']:
                if int(stampkey.keydetails['length']) < 3072:
                    self.server.logger.debug("Key is too small.")
                    return False

            elif stampkey.keydetails['algorithm'] == 'ECDSA':
                if int(stampkey.keydetails['length']) < 233:
                    self.server.logger.debug("Key is too small.")
                    return False

            for uid in stampkey.keydetails['uids']:
                if uid not in [None, 'TAVERN', '']:
                    self.server.logger.debug(
                        "Key UID is potentially leaking information.")
                    return False

            # Ensure it matches the signature.
            if not stampkey.verify_string(stringtoverify=self.payload.text(), signature=stamp['signature']):
                self.server.logger.debug("Signature Failed to verify for stamp :: " +
                                         stamp['class'] + " :: " + stamp['pubkey'])
                return False

            # If they specify a proof-of-work in the stamp, make sure it's
            # valid.
            if 'proof-of-work' in stamp:
                    proof = stamp['proof-of-work']['proof']
                    difficulty = stamp['proof-of-work']['difficulty']
                    if stamp['proof-of-work']['class'] == 'sha256':
                        result = libtavern.utils.checkWork(
                            self.payload.hash(),
                            proof,
                            difficulty)
                        if result is False:
                            self.server.logger.debug(
                                "Proof of work cannot be verified.")
                            return False
                    else:
                        self.server.logger.debug(
                            "Proof of work in unrecognized format. Ignoring.")

        # It's OK if they don't include a user-agent, but not if they include a
        # bad one.
        # if 'useragent' in self.dict['envelope']['payload']['author']:
        #     if not 'name' in self.dict['envelope']['payload']['author']['useragent']:
        #         self.server.logger.debug(
        #             "If you supply a user agent, it must have a valid name")
        #         return False
        #     if not isinstance(self.dict['envelope']['payload']['author']['useragent']['version'], int) and not isinstance(self.dict['envelope']['payload']['author']['useragent']['version'], float):
        #             self.server.logger.debug(
        #                 "Bad Useragent version must be a float or integer")
        #             return False

        # Do this last, so we don't waste time if the stamps are bad.
        if not self.payload.validates():
            self.server.logger.info("Payload does not validate.")
            return False

        return True

    def munge(self):
        """Set things in the local block of the message."""

        # If we don't have a local section, add one.
        # This isn't inside of validation since it's legal not to have one.
        # if 'local' not in c.dict['envelope']:
        self.dict['envelope']['local'] = OrderedDict()

        # Don't caclulate the SHA_512 each time. Store it in local, so we can
        # reference it going forward.
        self.dict['envelope']['local']['payload_sha512'] = self.payload.hash()

        # Pull out serverstamps.
        stamps = self.dict['envelope']['stamps']

        highestPOW = 0

        for stamp in stamps:

            # Find the author of the message, save it where it's easy to find
            # later.
            if stamp['class'] == "author":
                self.dict['envelope']['local']['author'] = stamp

            # Calculate highest proof of work difficuly.
            # Only use proof-of-work class sha256 for now.
            if 'proof-of-work' in stamp:
                if stamp['proof-of-work']['class'] == 'sha256':
                    if stamp['proof-of-work']['difficulty'] > highestPOW:
                        highestPOW = stamp['proof-of-work']['difficulty']

        self.dict['envelope']['local']['highestPOW'] = highestPOW

        # Copy a lowercase/simplified version of the topic into 'local', so
        # StarTrek and startrek show up together.
        if 'topic' in self.dict['envelope']['payload']:
            self.dict['envelope']['local']['sorttopic'] = libtavern.topic.sorttopic(
                self.dict['envelope']['payload']['topic'])

        # Get a short version of the subject, for display.
        if 'subject' in self.dict['envelope']['payload']:
            temp_short = self.dict['envelope']['payload'][
                'subject'][:50].rstrip()
            self.dict['envelope']['local'][
                'short_subject'] = self.server.urlize(temp_short)
        # Get a short version of the body, to use as a preview.
        # First line only.
        if 'body' in self.dict['envelope']['payload']:
            short_body = self.dict['envelope']['payload'][
                'body'].split('\n', 1)[0][:60].strip()
            self.dict['envelope']['local'][
                'short_body'] = short_body

        # Process any attachments which are listed in the envelope
        if 'attachments' in self.dict['envelope']['payload']:
            self.mungebins()

        if 'body' in self.dict['envelope']['payload']:
            formattedbody = self.server.formatText(
                text=self.dict['envelope']['payload']['body'],
                formatting=self.dict['envelope']['payload']['formatting'])
            self.dict['envelope']['local']['formattedbody'] = formattedbody

            # Check for any Embeddable (Youtube, Vimeo, etc) Links.
            # Don't check a given message more than once.
            # Iterate through the list of possible embeddables.
            # cap the number of URLs we can embed.
            foundurls = 0
            if not 'embed' in self.dict['envelope']['local']:
                self.dict['envelope']['local']['embed'] = []

            soup = BeautifulSoup(formattedbody, "html.parser")
            for href in soup.findAll('a'):
                result = self.server.external.lookup(href.get('href'))
                if result is not None and foundurls < self.server.serversettings.settings['maxembeddedurls']:
                    self.dict['envelope']['local']['embed'].append(result)
                    foundurls += 1

        if 'author' in self.dict['envelope']['local']:
            self.dict['envelope']['local']['author_wordhash'] = self.server.wordlist.wordhash(
                self.dict['envelope']['local']['author']['pubkey'])
        if not 'priority' in self.dict['envelope']['local']:
            self.dict['envelope']['local']['priority'] = 0

        if '_id' in self.dict:
            del(self.dict['_id'])

    def mungebins(self):
        """
        Store details for all attachments, and create thumbnails for images.
        """

        attachmentlist = []
        for attachment in self.dict['envelope']['payload']['attachments']:
            try:
                with self.server.bin_GridFS.get_last_version(filename=attachment['sha512']) as attachment:
                    desc = {}
                    desc['sha512'] = attachment['sha512']
                    desc['filename'] = attachment.get('filename','Unknown_File')
                    desc['detected_mime'] = magic.from_buffer(attachment.read(), mime=True).decode('utf-8')
                    desc['displayable'] = libtavern.utils.make_thumbnail(attachment,attachment['sha_512'] + '-thumb',desc['detected_mime'])
                    desc['filesize'] = attachment.length
                    attachmentlist.append(attachmentdesc)
            except:
                continue

            # Use the first displayable attachment as a link for Pinterest and FB
            if not self.dict['envelope']['local'].get('medialink') and desc['displayable']:
                self.dict['envelope']['local']['medialink'] = desc['displayable']

        self.dict['envelope']['local']['attachmentlist'] = attachmentlist


    #@libtavern.utils.memorise(parent_keys=['dict.envelope.local.payload_sha512'], ttl=self.server.serversettings.settings['cache']['templates']['seconds'], maxsize=self.server.serversettings.settings['cache']['templates']['size'])
    def countChildren(self):
        #print("Looking for childen for :" + self.payload.hash())
        results = self.server.db.unsafe.count(
            'envelopes',
            {"envelope.local.ancestors": self.payload.hash()})
        return results

    def addStamp(self, stampclass, keys, passkey=None, **kwargs):
        """Adds a stamp of type `class` to the current envelope."""

        signature = keys.signstring(self.payload.text(),passkey=passkey)

        # Generate the full stamp obj we will insert.
        fullstamp = {}
        fullstamp['class'] = stampclass
        fullstamp['keyformat'] = keys.keydetails['format']
        fullstamp['pubkey'] = keys.pubkey
        fullstamp['signature'] = signature
        fullstamp['time_added'] = libtavern.utils.gettime(format='timestamp')

        # Copy in any passed values
        for key in kwargs.keys():
            # Remove the kwargs we know we already added
            if key not in ["stampclass", "keys", "passkey"]:
                fullstamp[key] = kwargs[key]

        proof = {}
        proof['class'] = 'sha256'
        proof[
            'difficulty'] = self.server.serversettings.settings[
            'proof-of-work-difficulty']
        proof['proof'] = libtavern.utils.proveWork(
            self.payload.hash(),
            proof['difficulty'])
        fullstamp['proof-of-work'] = proof

        self.dict['envelope']['stamps'].append(fullstamp)

    def add_ancestor(self, ancestorid):
        """A new Ancestor has been found (parent, parent's parent, etc) for
        this message.

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
                    self.dict['envelope']['local'][
                        'ancestors'].append(listedancestor)

            # Now, tell our children, if we have any
            if 'citedby' in self.dict['envelope']['local']:
                for childid in self.dict['envelope']['local']['citedby']:
                    child = Envelope()
                    if child.loadmongo(mongo_id=childid):
                        child.add_ancestor(ancestorid)
                        child.saveMongo()

            self.saveMongo()

    def add_cite(self, citedby):
        """Another message has referenced this one.

        Mark it in the local area.

        """
        if not 'citedby' in self.dict['envelope']['local']:
            self.dict['envelope']['local']['citedby'] = []
        if citedby not in self.dict['envelope']['local']['citedby']:
            self.dict['envelope']['local']['citedby'].append(citedby)

        self.saveMongo()

    def __init2__(self):
        self.dict = OrderedDict()
        self.dict['envelope'] = OrderedDict()
        self.dict['envelope']['payload'] = OrderedDict()
        self.dict['envelope']['local'] = OrderedDict()
        self.dict['envelope']['local']['citedby'] = []
        self.dict['envelope']['stamps'] = []

        self.payload = PayloadBase(self.dict['envelope']['payload'])

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
                    self.server.logger.info(
                        "Rejecting message of class " +
                        self.dict[
                            'envelope'][
                            'payload'][
                            'class'])
                    return False
            return True

    def loaddict(self, importdict):
        newstr = json.dumps(importdict, separators=(',', ':'))
        return self.loadstring(newstr)

    def loadstring(self, importstring):
        self.dict = json.loads(
            importstring,
            object_pairs_hook=OrderedDict,
            object_hook=OrderedDict)
        return self.registerpayload()

    def loadfile(self, filename):

        # Determine the file extension to see how to parse it.
        basename, ext = os.path.splitext(filename)
        max_size = 102400
        with lzma.open(filename, 'rt', encoding='utf-8') as filehandle:
            filecontents = filehandle.read()
            self.loadstring(filecontents)

    def loadmongo(self, mongo_id):
        env = self.server.db.unsafe.find_one('envelopes', {'_id': mongo_id})
        if env is None:
            return False
        else:
            return self.loaddict(env)

    def reloadmongo(self):
        return self.loadmongo(self.payload.hash())

    def reloadfile(self):
        return self.loadfile(self.payload.hash() + ".7zTavernEnvelope")

    def flatten(self, striplocal=False):
        self.registerpayload()
        self.payload.format()
        if striplocal:
            if 'local' in self.dict['envelope']:
                del self.dict['envelope']['local']
        self.dict['envelope']['payload'] = self.payload.dict
        self.dict['envelope']['local']['payload_sha512'] = self.payload.hash()
        return self

    def text(self, striplocal=False):
        self.flatten()
        newstr = json.dumps(self.dict, separators=(',', ':'))
        return newstr

    def prettytext(self, striplocal=False):
        self.flatten()
        newstr = json.dumps(self.dict, indent=2, separators=(', ', ': '))
        return newstr

    def savefile(self, directory='.'):
        self.flatten()

        # We want to name this file to the SHA512 of the payload contents, so
        # it is consistant across servers.
        with lzma.open(filename= directory + "/" + self.payload.hash() + ".7zTavernEnvelope", mode='w', encoding='utf-8') as filehandle:
            filehandle.write(self.text())

    def saveMongo(self):
        self.flatten()

        self.dict['_id'] = self.payload.hash()
        self.server.db.unsafe.save('envelopes', self.dict)

class attachment(object):

    def __init__(self, sha512):
        self.dict = OrderedDict()
        self.dict['sha512'] = sha512
