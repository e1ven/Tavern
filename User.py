import os
import json
from Envelope import *
import time
from keys import *
from collections import OrderedDict
import pymongo
from Server import server
import scrypt
import base64
from lockedkey import lockedKey
from TavernUtils import memorise
from ServerSettings import serversettings

import math
class User(object):

    def __init__(self):
        self.UserSettings = {}
        self.UserSettings['keys'] = {}
        self.UserSettings['keys']['master'] = {}
        self.UserSettings['followedUsers'] = []
        self.UserSettings['followedTopics'] = []
        self.Keys = {}

    def isLoggedIn(self):
        if self.UserSettings['keys']['master']['pubkey'] == serversettings.settings['guestacct']['keys']['master']['pubkey']:
            return False
        if 'encryptedprivkey' in self.UserSettings['keys']['master']:
            if self.UserSettings['keys']['master']['encryptedprivkey'] is not None:
                return True
        return False

    def randstr(self, length):
        # Random.randint isn't secure, use the OS urandom instead.
        return ''.join(chr(int.from_bytes(os.urandom(1), 'big')) for i in range(length))

    def hash_password(self, password, maxtime=5, datalength=64):
        pword = scrypt.encrypt(
            self.randstr(datalength), password, maxtime=maxtime)
        return base64.b64encode(pword).decode('utf-8')

    def verify_password(self, guessed_password, hashed_password=None, maxtime=50):
        try:
            if hashed_password is None:
                hashed_password = self.UserSettings['hashedpass']
            pword = base64.b64decode(hashed_password.encode('utf-8'))
            scrypt.decrypt(pword, guessed_password, maxtime)
            return True
        except scrypt.error:
            return False

    @memorise(parent_keys=['UserSettings.keys.master.pubkey'], ttl=serversettings.settings['cache']['user-note']['seconds'], maxsize=serversettings.settings['cache']['user-note']['size'])
    def getNote(self, noteabout):
        """
        Retrieve any note by user A about user B
        """
        # Make sure the key we're asking about is formatted right.
        # I don't trust myself ;)

        key = Keys(pub=noteabout)
        noteabout = key.pubkey
        # Retrieve the note from mongo
        note = server.db.unsafe.find_one(
            'notes', {"user": self.Keys['master'].pubkey, "noteabout": noteabout})
        if note is not None:
            return note['note']
        else:
            if noteabout == self.Keys['master'].pubkey: 
                # I'm asking about myself, and I haven't set a note yet.
                return "This is you!"
            else:
                return None

    def setNote(self, noteabout, note=""):
        # Format the Key.
        key = Keys(pub=noteabout)
        noteabout = key.pubkey

        newnote = {"user": self.Keys['master'].pubkey, "noteabout":
                   noteabout, "note": note}

        # Retrieve any existing note, so that the _id is the same. Then, we'll gut it, and put in our own values.
        newnote = server.db.unsafe.find_one(
            'notes', {"user": self.Keys['master'].pubkey, "noteabout": noteabout})
        if newnote is None:
                newnote = {"user": self.Keys['master'].pubkey,
                           "noteabout": noteabout, "note": note}
        newnote['note'] = note
        server.db.unsafe.save('notes', newnote)
        self.getNote(noteabout=noteabout, forcerecache=True)

    @memorise(parent_keys=['UserSettings.keys.master.pubkey'], ttl=serversettings.settings['cache']['user-trust']['seconds'], maxsize=serversettings.settings['cache']['user-trust']['size'])
    def gatherTrust(self, askingabout, incomingtrust=250):
        """
        Return how much I trust a given ID, rather than a given post.
        This is determined by several factors, but the base algorithm is:
            [Keys and Spam Ranking]
            [Have I rated this person]
            [Have any friends rated this person]
            [Have any FOF or FOFOF rated this person]
            [Each generation of friends gets their trust multiplied by .4, since you trust them less and less]
        """

        # Ensure we have proper formatting for the key we're examining, so we find it in the DB.
        key = Keys(pub=askingabout)
        askingabout = key.pubkey

        # Our opinion of everyone starts off Neutral
        trust = 0

        # Set the maximum amount of trust we can return.
        # This is set to 40% of incoming - Incoming starts at 250, to ensure that this goes to 100 for myself.
        maxtrust = .4 * incomingtrust

        # We trust ourselves implicitly
        if askingabout == self.Keys['master'].pubkey:
            server.logger.info("I trust me.")
            return round(incomingtrust)

        # Don't recurse forever, please.
        # Stop after 4 Friends-of-Friends = 100,40,16,6,0,0,0,0,0,0,0,0,0,0,0,0 etc
        if incomingtrust <= 2:
            return 0

        # Query mongo to retrieve the most recent rating for a specific user.
        myvote = server.db.unsafe.find_one(collection='envelopes', query={"envelope.payload.class": "usertrust", "envelope.payload.trusted_pubkey": str(askingabout), "envelope.payload.trust": {"$exists": "true"}, "envelope.local.author.pubkey": str(self.Keys['master'].pubkey)}, sortkey="envelope.local.time_added", sortdirection='descending')

        if myvote:
            # If I directly rated this user, Mazel tov, that was easy.
            server.logger.info("I rated this user directly.")
            trust = int(myvote['envelope']['payload']['trust'])

        else:
            # If we didn't directly rate the user, let's see if any of our friends have rated him.

            # First, let's get a list of the friends we trust
            alltrusted = server.db.unsafe.find('envelopes', {"envelope.payload.class": "usertrust", "envelope.payload.trust": {"$gt": 0}, "envelope.local.author.pubkey": self.Keys['master'].pubkey})
            combinedFriendTrust = 0
            friendcount = 0

            # Now, iterate through each of those people, and see if they rated him. Check THEIR friends.
            # This will be slow for the first search, but the function uses a decorator for caching.
            for trusted in alltrusted:
                friendcount += 1

                # Load in our friend from the DB.
                u = User()
                u.load_mongo_by_pubkey(
                    trusted['envelope']['payload']['trusted_pubkey'])
                # How much do we trust our Friend...
                # We're only going to be here if we directly rated them, which set it out at 100
                # But if they're from a bad neighborhood, or if they constantly recommend people we downvote, we might decide we don't like them anymore.
                # That's why we want to weigh their recomendation by how much we trust them.
                amountITrustThisFriend = u.gatherTrust(askingabout=trusted['envelope']['payload']['trusted_pubkey'],incomingtrust=maxtrust)
                amountMyFriendTrustsAskingAbout = u.gatherTrust(
                    askingabout=askingabout, incomingtrust=maxtrust)

                # I can never trust my friends unusual amounts.
                if amountITrustThisFriend > 100:
                    amountITrustThisFriend = 100
                if amountITrustThisFriend < 1:
                    amountITrustThisFriend = 1

                combinedFriendTrust += round((amountITrustThisFriend/100) * amountMyFriendTrustsAskingAbout)

            if friendcount > 0:
                trust = combinedFriendTrust / friendcount
            server.logger.info("total friend average" + str(trust))

        # Ensure that this element of the trust doesn't go out of range, and unduly effect others.
        if trust > maxtrust:
            trust = maxtrust
        if trust < (-1 * maxtrust):
            trust = (-1 * maxtrust)


        # OK, so now we have a rating for this user, either directly or indirectly.
        # Let's add other characteristics.



        # For instance, If we've upvoted this guy, that should weigh in, somewhat.
        # We'll weigh the vote by log2, to discourage vote-farming.
        ratingtally = 0
        allratings = server.db.unsafe.find('envelopes', {"envelope.payload.class": "messagerating", "envelope.payload.rating": {"$exists": "true"}, "envelope.local.regardingAuthor": askingabout})
        for rating in allratings:
            ratingtally += rating['envelope']['payload']['rating']
        
        # Reduce it using log2, carefully saving the direction.
        if ratingtally < 0:
            weighted = math.log2(ratingtally * -1) * -1
        elif ratingtally > 0:
            weighted = math.log2(ratingtally)
        else:
            weighted = 0

        trust += weighted

        # Ensure that this element of the trust doesn't go out of range, and unduly effect others.
        if trust > maxtrust:
            trust = maxtrust
        if trust < (-1 * maxtrust):
            trust = (-1 * maxtrust)


        # We should also reduce their trust everytime we disagree with a recommendation.
        # We still like them, but we don't trust their judgement.
        ## TODO - How can we do this without spending ALL the CPU?


        # Add up the trusts from our friends, and cap at MaxTrust
        if trust > maxtrust:
            trust = maxtrust
        if trust < (-1 * maxtrust):
            trust = (-1 * maxtrust)

        trust = round(trust)
        print("trust is :" + str(trust))
        return trust

    def translateTrustToWords(self, trust):
        if trust == 250:
            return "are"
        if trust > 75:
            return "strongly trust"
        elif trust > 50:
            return "moderately trust"
        elif trust > 10:
            return "slightly trust"
        elif trust > -10:
            return "are neutral toward"
        elif trust > -50:
            return "slightly distrust"
        elif trust > -75:
            return "moderately distrust"
        else:
            return "strongly distrust"

    @memorise(parent_keys=['UserSettings.keys.master.pubkey'], ttl=serversettings.settings['cache']['message-ratings']['seconds'], maxsize=serversettings.settings['cache']['message-ratings']['size'])
    def getRatings(self, postInQuestion):
        """
        Get the ratings of a specific message
        """
        #Move this. Maybe to Server??
        allvotes = server.db.unsafe.find('envelopes', {"envelope.payload.class": "messagerating", "envelope.payload.rating": {"$exists": "true"}, "envelope.payload.regarding": postInQuestion})
        combinedrating = 0
        for vote in allvotes:
            author = vote['envelope']['local']['author']['pubkey']
            rating = vote['envelope']['payload']['rating']
            authorTrust = self.gatherTrust(askingabout=author)

            # Now that we know how much we trust the author, pay attention to their rating in proportion to how much we trust them.
            if authorTrust > 0:
                authorPCT = authorTrust/100
                combinedrating += rating *  authorPCT

        # Stamp based ratings give a baseline, like SpamAssassin.
        e = server.db.unsafe.find_one('envelopes',
                                      {"envelope.local.payload_sha512": postInQuestion})

        if e is not None:
            if 'stamps' in e['envelope']:
                stamps = e['envelope']['stamps']
                for stamp in stamps:
                    # if it was posted directly to OUR server, we can ip limit it, give it a +1
                    if stamp['class'] == "origin":
                        if stamp['pubkey'] == server.ServerKeys.pubkey:
                            combinedrating += 1

        return combinedrating

    def followTopic(self, topic):
        if topic not in self.UserSettings['followedTopics']:
            self.UserSettings['followedTopics'].append(topic)

    def unFollowTopic(self, topic):
        # Compare the lowercase/sorted values
        for followedtopic in self.UserSettings['followedTopics']:
            if server.sorttopic(followedtopic) == server.sorttopic(topic):
                self.UserSettings['followedTopics'].remove(followedtopic)


                
    def generate(self, email=None, username=None, forceUnique=False,forcePrivKey=False,password=None):
        """
        Create a Tavern user, filling in any missing information for existing users.
        Only creates keys if asked to.
        """

        # Ensure that these values are filled in.
        # Either by Saved values, Passed-in values, or by Null objects.

        if username is not None:
            self.UserSettings['username'] = username
        elif not 'username' in self.UserSettings:
            self.UserSettings['username'] = "Anonymous"

        if email is not None:
            self.UserSettings['email'] = email
        elif not 'email' in self.UserSettings:
            self.UserSettings['email'] = "email@example.org"

        if password is not None:
            self.UserSettings['hashedpass'] = self.hash_password(password)


        if not 'keys' in self.UserSettings:
            self.UserSettings['keys'] = {}
        if not 'master' in self.UserSettings['keys']:
            self.UserSettings['keys']['master'] = {}

        # Ensure we have a valid public key, one way or another.
        # If forceUnique is off, then use the server default acct.

        if forceUnique == False:
            # With the default server key, there will be no way to privkey/way to post.
            if not 'pubkey' in self.UserSettings['keys']['master']:
                self.UserSettings['keys']['master']['pubkey'] = serversettings.settings['guestacct']['keys']['master']['pubkey']
            if not 'master' in self.Keys:
                self.Keys['master'] = Keys(pub=self.UserSettings['keys']['master']['pubkey'])
        else:         
            # Make a real key if we don't have one.
            validkey = False
            if 'encryptedprivkey' in self.UserSettings['keys']['master']:
                if self.UserSettings['keys']['master']['encryptedprivkey'] is not None:
                    # We have a master key! We don't need to load it yet, but don't overwrite it!
                    self.Keys['master'] = Keys(pub=self.UserSettings['keys']['master']['pubkey'])
                    validkey = True

            if validkey == False: 
                # We don't have a privkey.. Fix that.

                self.Keys['master'] = lockedKey()
                self.Keys['master'].generate(password=password)
                self.Keys['master'].format_keys()

                self.UserSettings['keys']['master']['pubkey'] = self.Keys['master'].pubkey
                self.UserSettings['keys']['master']['encryptedprivkey'] = self.Keys['master'].encryptedprivkey
                self.UserSettings['keys']['master']['time_privkey'] = int(time.time())

        if not 'time_created' in self.UserSettings:
            self.UserSettings['time_created'] = int(time.time())

        if not 'display_useragent' in self.UserSettings:
            self.UserSettings['display_useragent'] = False

        if not 'theme' in self.UserSettings:
            self.UserSettings['theme'] = 'default'

        if not 'followedTopics' in self.UserSettings:
            self.UserSettings['followedTopics'] = []

        if not 'allowembed' in self.UserSettings:
            self.UserSettings['allowembed'] = 0

        if self.UserSettings['followedTopics'] == []:
            self.followTopic("StarTrek")
            self.followTopic("Python")
            self.followTopic("Egypt")
            self.followTopic("Funny")

        if not 'maxposts' in self.UserSettings:
            self.UserSettings['maxposts'] = 100

        if not 'maxreplies' in self.UserSettings:
            self.UserSettings['maxreplies'] = 100

        if not 'friendlyname' in self.UserSettings:
            self.UserSettings['friendlyname'] = "Anonymous"

        if not 'include_location' in self.UserSettings:
            self.UserSettings['include_location'] = False

        if not 'ignoreedits' in self.UserSettings:
            self.UserSettings['ignoreedits'] = False

        self.UserSettings['author_wordhash'] = server.wordlist.wordhash(self.UserSettings['keys']['master']['pubkey'])

    def changepass(self, oldpasskey, newpass):
        """
        Change the User's password
        """
        # Re-encrypt our Privkey
        self.Keys['master'].changepass(oldpasskey=oldpasskey, newpass=newpass)
        self.UserSettings['keys']['master']['encryptedprivkey'] = self.Keys['master'].encryptedprivkey

        hashedpass = self.hash_password(newpass)
        self.UserSettings['hashedpass'] = hashedpass
        self.UserSettings['lastauth'] = int(time.time())

        self.savemongo()

    def load_string(self, incomingstring):
        self.UserSettings = json.loads(incomingstring, object_pairs_hook=collections.OrderedDict, object_hook=collections.OrderedDict)

        if 'encryptedprivkey' in self.UserSettings['keys']['master']:
            self.Keys['master'] = lockedKey(pub=self.UserSettings['keys']['master']['pubkey'], encryptedprivkey=self.UserSettings['keys']['master']['encryptedprivkey'])
            server.logger.info("Reconstructed with encryptedprivkey")
        else:
            self.masterkeys = Keys(pub=self.UserSettings['keys']['master']['pubkey'])
            server.logger.info("reconstructed user without privkey")
        self.generate()

    def load_file(self, filename):
        filehandle = open(filename, 'r')
        filecontents = filehandle.read()
        self.load_string(filecontents)

    def savefile(self, filename=None):
        self.masterkeys.format_keys()
        if filename is None:
            filename = self.UserSettings['username'] + ".TavernUser"
        filehandle = open(filename, 'w')
        filehandle.write(json.dumps(self.UserSettings, separators=(',', ':')))
        filehandle.close()

    def load_mongo_by_pubkey(self, pubkey):
        """
        Returns a user object for a given pubkey
        """
        user = server.db.safe.find_one('users',
                                       {"keys.master.pubkey": pubkey})
        if user is None:
            # If the user doesn't exist in our service, he's only someone we've heard about.
            # We won't know their privkey, so just return their pubkey back out.
            self.Keys['master'] = Keys(pub=pubkey)
        else:
            # If we *do* find you locally, load in both Priv and Pubkeys
            # And load in the user settings.
            self.UserSettings = user
            self.Keys['master'] = lockedKey(pub=self.UserSettings['keys']['master']['pubkey'],encryptedprivkey=self.UserSettings['keys']['master']['encryptedprivkey'])
        self.UserSettings['keys']['master']['pubkey'] = self.Keys['master'].pubkey

    def load_mongo_by_username(self, username):
        #Local server Only
        user = server.db.safe.find_one('users',
                                       {"username": username})
        self.UserSettings = user
        self.Keys['master'] = lockedKey(pub=self.UserSettings['keys']['master']['pubkey'], encryptedprivkey=self.UserSettings['keys']['master']['encryptedprivkey'])
        self.UserSettings['keys']['master']['pubkey'] = self.Keys['master'].pubkey

    def savemongo(self):
        if not 'encryptedprivkey' in self.UserSettings['keys']['master']:
            raise Exception("Asked to save a bad user")

        self.Keys['master'].format_keys()
        self.UserSettings['keys']['master']['privkey'] = None
        self.UserSettings['passkey'] = None
        self.UserSettings['keys']['master']['pubkey'] = self.Keys['master'].pubkey
        self.UserSettings['_id'] = self.Keys['master'].pubkey
        server.db.safe.save('users', self.UserSettings)
