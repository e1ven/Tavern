import os
import json
from Envelope import *
import time
from key import Key
from collections import OrderedDict
import pymongo
import scrypt
import base64
from lockedkey import LockedKey
from TavernUtils import memorise
import time
import datetime
import calendar
import hashlib
import math
import Server


class User(object):

    def __init__(self):
        self.UserSettings = {}
        self.UserSettings['followedUsers'] = []
        self.UserSettings['followedTopics'] = []
        self.UserSettings['status'] = {}
        self.UserSettings['keys'] = {}
        self.UserSettings['keys']['master'] = {}
        self.passkey = None
        self.Keys = {}
        self.Keys['posted'] = []
        self.Keys['secret'] = []
        self.Keys['master'] = None
        self.server = Server.Server()

    def find_commkey(self):
        """
        Retrieves the current public communication key.
        This will retrieve the key using only public information.
        """

        posts = self.server.getUsersPosts(self.Keys['master'].pubkey)
        if len(posts) > 0:
            return posts[0].dict['envelope']['payload']['author']['replyto']
        else:
            return None

    def get_pmkey(self, talkingto=None):
        """
        Generate a Private Message to person X.
        This is create a new Secret Key for the message, and add it to our pool.
        This helps avoid analysis, and helps ensure that if our master key is compromised,
        our older communications don't leak.
        """

        if self.passkey is None:
            raise Exception("Must have a valid passkey to run this method")

        # Step 1, Create a new Key for this person.
        newkey = LockedKey()
        newkey.generate(passkey=self.passkey, autoexpire=True)
        self.Keys['secret'].append(newkey)
        self.savemongo()
        return newkey

    def get_keys(self, ret='all', excludeMaster=True):
        """
        Retrieve a list of all of our Keys objects.
        Optionally exclude the 'master' key.
        """
        # Allow both Keys['foo'] and Keys['foo']['bar'] styles
        allkeys = []
        for keyclass in self.Keys:
            l2 = self.Keys[keyclass]
            if excludeMaster is True:
                if keyclass == 'master':
                    l2 = None
            if isinstance(l2, (Key, LockedKey)):
                if l2.isValid():
                    allkeys.append(l2)
                else:
                    print("Expired Key")
            elif hasattr(l2, '__iter__'):
                if not isinstance(l2, (str, bytes)):
                    for key in l2:
                        if key.isValid():
                            allkeys.append(key)
                        else:
                            print("Expired Key")

        # Allow routines to request only what they need.
        # So, for instance, with ret=pubkey, it'll return an array of pubkeys

        print(len(allkeys))
        if ret == 'all':
            return allkeys
        else:
            retarray = []
            for key in allkeys:
                retarray.append(vars(key)[ret])
            return retarray

    def verify_password(self, guessed_password, maxtime=50):
        """
        Verify if we can unlock the master key.
        If we can, allow auth to the this user.
        """

        passkey = self.Keys['master'].get_passkey(guessed_password)
        if scrypt.decrypt(pword, guessed_password, maxtime):
            return True
        else:
            return False

    # @memorise(parent_keys=['Keys.master.pubkey'], ttl=serversettings.settings['cache']['user-note']['seconds'], maxsize=self.server.serversettings.settings['cache']['user-note']['size'])
    def getNote(self, noteabout):
        """
        Retrieve any note by user A about user B
        """
        # Make sure the key we're asking about is formatted right.
        # I don't trust myself ;)

        key = Key(pub=noteabout)
        noteabout = key.pubkey
        # Retrieve the note from mongo
        note = self.server.db.unsafe.find_one(
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
        key = Key(pub=noteabout)
        noteabout = key.pubkey

        newnote = {"user": self.Keys['master'].pubkey, "noteabout":
                   noteabout, "note": note}

        # Retrieve any existing note, so that the _id is the same. Then, we'll
        # gut it, and put in our own values.
        newnote = self.server.db.unsafe.find_one(
            'notes', {"user": self.Keys['master'].pubkey, "noteabout": noteabout})
        if newnote is None:
            newnote = {"user": self.Keys['master'].pubkey,
                       "noteabout": noteabout, "note": note}
        newnote['note'] = note
        self.server.db.unsafe.save('notes', newnote)
        self.getNote(noteabout=noteabout, forcerecache=True)

   # @memorise(parent_keys=['Keys.master.pubkey'], ttl=self.server.serversettings.settings['cache']['user-trust']['seconds'], maxsize=self.server.serversettings.settings['cache']['user-trust']['size'])
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
        # Ensure we have proper formatting for the key we're examining, so we
        # find it in the DB.
        key = Key(pub=askingabout)
        askingabout = key.pubkey

        # Our opinion of everyone starts off Neutral
        trust = 0

        # Set the maximum amount of trust we can return.
        # This is set to 40% of incoming - Incoming starts at 250, to ensure
        # that this goes to 100 for myself.
        maxtrust = .4 * incomingtrust

        # We trust ourselves implicitly
        if askingabout == self.Keys['master'].pubkey:
            self.server.logger.info("I trust me.")
            return round(incomingtrust)

        # Don't recurse forever, please.
        # Stop after 4 Friends-of-Friends = 100,40,16,6,0,0,0,0,0,0,0,0,0,0,0,0
        # etc
        if incomingtrust <= 2:
            return 0

        # Query mongo to retrieve the most recent rating for a specific user.
        myvote = self.server.db.unsafe.find_one(
            collection='envelopes',
            query={"envelope.payload.class": "usertrust",
                   "envelope.payload.trusted_pubkey": str(askingabout),
                   "envelope.payload.trust": {"$exists": "true"},
                   "envelope.local.author.pubkey": str(self.Keys['master'].pubkey)},
            sortkey="envelope.local.time_added",
            sortdirection='descending')

        if myvote:
            # If I directly rated this user, Mazel tov, that was easy.
            self.server.logger.info("I rated this user directly.")
            trust = int(myvote['envelope']['payload']['trust'])

        else:
            # If we didn't directly rate the user, let's see if any of our
            # friends have rated him.

            # First, let's get a list of the friends we trust
            alltrusted = self.server.db.unsafe.find(
                'envelopes',
                {"envelope.payload.class": "usertrust",
                 "envelope.payload.trust": {"$gt": 0},
                 "envelope.local.author.pubkey": self.Keys['master'].pubkey})
            combinedFriendTrust = 0
            friendcount = 0

            # Now, iterate through each of those people, and see if they rated him. Check THEIR friends.
            # This will be slow for the first search, but the function uses a
            # decorator for caching.
            for trusted in alltrusted:
                friendcount += 1
                # Load in our friend from the DB.
                u = User()
                u.load_mongo_by_pubkey(
                    trusted['envelope']['payload']['trusted_pubkey'])
                # How much do we trust our Friend...
                # We're only going to be here if we directly rated them, which set it out at 100
                # But if they're from a bad neighborhood, or if they constantly recommend people we downvote, we might decide we don't like them anymore.
                # That's why we want to weigh their recomendation by how much
                # we trust them.
                amountITrustThisFriend = u.gatherTrust(
                    askingabout=trusted[
                        'envelope'][
                        'payload'][
                        'trusted_pubkey'],
                    incomingtrust=maxtrust)
                amountMyFriendTrustsAskingAbout = u.gatherTrust(
                    askingabout=askingabout, incomingtrust=maxtrust)

                # I can never trust my friends unusual amounts.
                if amountITrustThisFriend > 100:
                    amountITrustThisFriend = 100
                if amountITrustThisFriend < 1:
                    amountITrustThisFriend = 1

                combinedFriendTrust += round(
                    (amountITrustThisFriend / 100) * amountMyFriendTrustsAskingAbout)

            if friendcount > 0:
                trust = combinedFriendTrust / friendcount
            self.server.logger.info("total friend average" + str(trust))

        # Ensure that this element of the trust doesn't go out of range, and
        # unduly effect others.
        if trust > maxtrust:
            trust = maxtrust
        if trust < (-1 * maxtrust):
            trust = (-1 * maxtrust)

        # OK, so now we have a rating for this user, either directly or indirectly.
        # Let's add other characteristics.
        # For instance, If we've upvoted this guy, that should weigh in, somewhat.
        # We'll weigh the vote by log2, to discourage vote-farming.
        ratingtally = 0
        allratings = self.server.db.unsafe.find(
            'envelopes',
            {"envelope.payload.class": "messagerating",
             "envelope.payload.rating": {"$exists": "true"},
             "envelope.local.regardingAuthor": askingabout})
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

        # Ensure that this element of the trust doesn't go out of range, and
        # unduly effect others.
        if trust > maxtrust:
            trust = maxtrust
        if trust < (-1 * maxtrust):
            trust = (-1 * maxtrust)

        # We should also reduce their trust everytime we disagree with a recommendation.
        # We still like them, but we don't trust their judgement.
        # TODO - How can we do this without spending ALL the CPU?
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

    # @memorise(parent_keys=['Keys.master.pubkey'], ttl=self.server.serversettings.settings['cache']['message-ratings']['seconds'], maxsize=self.server.serversettings.settings['cache']['message-ratings']['size'])
    def getRatings(self, postInQuestion):
        """
        Get the ratings of a specific message
        """
        # Move this. Maybe to Server??
        allvotes = self.server.db.unsafe.find(
            'envelopes',
            {"envelope.payload.class": "messagerating",
             "envelope.payload.rating": {"$exists": "true"},
             "envelope.payload.regarding": postInQuestion})
        combinedrating = 0
        for vote in allvotes:
            author = vote['envelope']['local']['author']['pubkey']
            rating = vote['envelope']['payload']['rating']
            authorTrust = self.gatherTrust(askingabout=author)

            # Now that we know how much we trust the author, pay attention to
            # their rating in proportion to how much we trust them.
            if authorTrust > 0:
                authorPCT = authorTrust / 100
                combinedrating += rating * authorPCT

        # Stamp based ratings give a baseline, like SpamAssassin.
        e = self.server.db.unsafe.find_one('envelopes',
                                           {"envelope.local.payload_sha512": postInQuestion})

        if e is not None:
            if 'stamps' in e['envelope']:
                stamps = e['envelope']['stamps']
                for stamp in stamps:
                    # if it was posted directly to OUR server, we can ip limit
                    # it, give it a +1
                    if stamp['class'] == "origin":
                        if stamp['pubkey'] == self.server.ServerKeys.pubkey:
                            combinedrating += 1

        return combinedrating

    def followTopic(self, topic):
        if topic not in self.UserSettings['followedTopics']:
            self.UserSettings['followedTopics'].append(topic)

    def unFollowTopic(self, topic):
        # Compare the lowercase/sorted values
        for followedtopic in self.UserSettings['followedTopics']:
            if self.server.sorttopic(followedtopic) == self.server.sorttopic(topic):
                self.UserSettings['followedTopics'].remove(followedtopic)

    def generate(self, AllowGuestKey=True,
                 password=None, email=None, username=None):
        """
        Create a Tavern user, filling in any missing information for existing users.
        Only creates keys if asked to.
        """

        # Ensure that these values are filled in.
        # Either by Saved values, Passed-in values, or by Null objects.

        # Create a string/immutable version of UserSettings that we can compare
        # against later to see if anything changed.
        tmpsettings = str(self.UserSettings) + str(self.Keys)

        if self.UserSettings.get('username') is None:
            if username is not None:
                self.UserSettings['username'] = username
            else:
                self.UserSettings['username'] = "Anonymous"

        if self.UserSettings.get('email') is None:
            if email is not None:
                self.UserSettings['email'] = email
            else:
                self.UserSettings['email'] = "email@example.org"

        if self.UserSettings['status'].get('guest') is None:
            self.UserSettings['status']['guest'] = True

        if not 'setpassword' in self.UserSettings['status']:
            self.UserSettings['status']['setpassword'] = None

        # If we've been told not to use a GuestKey, make sure we don't have
        # one.
        if AllowGuestKey is False and self.server.guestacct is not None:
            if self.server.guestacct.Keys.get('master') is not None and self.Keys.get('master') is not None:
                if self.Keys['master'].pubkey == self.server.guestacct.Keys['master'].pubkey:
                    print("Getting rid of a GuestKey.")
                    self.UserSettings['keys'] = {}
                    self.UserSettings['keys']['master'] = {}
                    self.passkey = None
                    self.Keys = {}
                    self.Keys['posted'] = []
                    self.Keys['secret'] = []
                    self.Keys['master'] = None

        # Ensure we don't somehow end up as an empty, but keyed user..
        if isinstance(self.Keys['master'], LockedKey):
            if self.Keys['master'].pubkey is None:
                self.Keys['master'] = None

        # Ensure we have a valid keys, one way or another.
        # If GuestKey is true, then use the server default accts.
        # Otherwise, make the keys.
        if self.Keys.get('master') is None:
            # Save if we're using the GuestKey or not.
            if AllowGuestKey:
                self.Keys = self.server.guestacct.Keys
                self.UserSettings['status']['guest'] = True
            else:
                print("Generating a LockedKeys")
                self.Keys['master'] = LockedKey()

                password = self.Keys['master'].generate(random=True)

                self.UserSettings['status']['guest'] = False
                self.passkey = self.Keys['master'].get_passkey(password)

        # Ensure we have a valid/current public posted key.
        if self.UserSettings['status']['guest'] is not True:
            # Set key to false, disprove assertion later.
            validcommkey = False
            # Make sure our Posted keys are in good shape.
            if len(self.Keys['posted']) > 0:
                # Sort the keys that we've already posted, highest expires
                # first.
                self.Keys['posted'].sort(
                    key=lambda e: (e.expires),
                    reverse=True)

                # Are we still in the same month we generated the key in?
                gen_month = datetime.datetime.fromtimestamp(
                    self.Keys['posted'][-1].generated).month
                gen_year = datetime.datetime.fromtimestamp(
                    self.Keys['posted'][-1].generated).year
                if gen_year == datetime.datetime.now().year:
                    if gen_month == datetime.datetime.now().month:
                        validcommkey = True

            # Either we have no key, or an old one.
            if validcommkey is False:
                print("Generating new posted key")
                newkey = LockedKey()
                newkey.generate(passkey=self.passkey)

                # We want the key to expire on the last second of NEXT month.
                # So if it's currently Oct 15, we want the answer Nov31-23:59:59
                # This makes it harder to pin down keys by when they were
                # generated, since it's not based on current time

                number_of_days_this_month = calendar.monthrange(
                    datetime.datetime.now().year,
                    datetime.datetime.now().month)[1]
                number_of_days_next_month = calendar.monthrange(
                    datetime.datetime.now().year,
                    datetime.datetime.now().month + 1)[1]
                two_months = datetime.datetime.now() + datetime.timedelta(
                    days=number_of_days_this_month + number_of_days_next_month)
                expiresdate = datetime.date(
                    two_months.year,
                    two_months.month,
                    1) - datetime.timedelta(
                    days=1)
                expiresdatetime = datetime.datetime.combine(
                    expiresdate, datetime.time.max)
                expirestamp = calendar.timegm(expiresdatetime.utctimetuple())

                newkey.expires = expirestamp
                self.Keys['posted'].append(newkey)

        if password is not None and self.passkey is None:
            self.passkey = self.Keys['master'].get_passkey(password=password)

        if self.UserSettings.get('time_created') is None:
            self.UserSettings['time_created'] = int(time.time())

        if self.UserSettings.get('display_useragent') is None:
            self.UserSettings['display_useragent'] = False

        if self.UserSettings.get('theme') is None:
            self.UserSettings['theme'] = 'default'

        if self.UserSettings.get('followedTopics') is None:
            self.UserSettings['followedTopics'] = []

        if self.UserSettings.get('allowembed') is None:
            self.UserSettings['allowembed'] = 0

        if self.UserSettings['followedTopics'] == []:
            self.followTopic("StarTrek")
            self.followTopic("Python")
            self.followTopic("Egypt")
            self.followTopic("Funny")

        if self.UserSettings.get('maxposts') is None:
            self.UserSettings['maxposts'] = 100

        if self.UserSettings.get('maxreplies') is None:
            self.UserSettings['maxreplies'] = 100

        # Set Friendlyname to most recent post, or Anonymous for lurkers
        if self.UserSettings.get('friendlyname') is None:
            if self.UserSettings['status']['guest'] is False:
                # They're registered, they may have posted.
                posts = self.server.getUsersPosts(self.Keys['master'].pubkey)
                if len(posts) > 0:
                    self.UserSettings[
                        'friendlyname'] = posts[
                        0].dict[
                        'envelope'][
                        'local'][
                        'author'][
                        'friendlyname']
            if self.UserSettings.get('friendlyname') is None:
                self.UserSettings['friendlyname'] = 'Anonymous'

        if self.UserSettings.get('include_location') is None:
            self.UserSettings['include_location'] = False

        if self.UserSettings.get('ignoreedits') is None:
            self.UserSettings['ignoreedits'] = False

        if self.UserSettings.get('author_wordhash') is None:
            self.UserSettings['author_wordhash'] = self.server.wordlist.wordhash(
                self.Keys['master'].pubkey)

        if self.UserSettings.get('author_sha512') is None:
            if self.UserSettings['status']['guest'] is False:
                self.UserSettings['author_sha512'] = hashlib.sha512(
                    self.Keys['master'].pubkey.encode('utf-8')).hexdigest()
            else:
                self.UserSettings['author_sha512'] = None

        # Determine if we changed anything without an explicit dirty flag.
        if tmpsettings == str(self.UserSettings) + str(self.Keys):
            return False
        else:
            return True

    def decrypt(self, text, passkey=None):
        """
        Decrypt a message sent to me, using one of my communication keys.

        Note - We don't try to decrypt using the master key, even though it's technically possible.
        This is intentional, so that other clients don't start sending PMs to the master key, and compromise security.
        """
        if self.passkey is not None:
            passkey = self.passkey

        keys = self.Keys['posted'] + self.Keys['secret']
        for key in keys:
            if isinstance(key, LockedKey):
                key.unlock(passkey)
            result = key.decrypt(text)

            if len(result) > 0:
                return result

    def changepass(self, newpassword, oldpasskey=None):
        """
        Change the User's password
        """
        # Re-encrypt our Privkey

        if oldpasskey is None and self.passkey is not None:
            oldpasskey = self.passkey

        print("Old Passkey is " + str(oldpasskey))
        print("Old Key is " + str(self.Keys['master'].encryptedprivkey))

        #TODO - Change --all-- keys
        if self.Keys['master'].changepass(oldpasskey=oldpasskey, newpassword=newpassword):
            self.passkey = self.Keys['master'].get_passkey(newpassword)
            self.UserSettings['lastauth'] = int(time.time())
            self.UserSettings['status']['setpassword'] = int(time.time())
            self.savemongo()
            print("New Passkey is " + str(self.passkey))
            print("New Password is " + str(newpassword))
            print("New Key is " + str(self.Keys['master'].encryptedprivkey))
        else:
            return False

    def presave_clean(self):
        """
        Ensure our keys are saved to the userdict for later restore, and remove sensetive info
        """
        if self.Keys.get('master'):
            if not self.UserSettings['keys'].get('master'):
                self.UserSettings['keys']['master'] = {}
            self.UserSettings[
                'keys'][
                'master'][
                'pubkey'] = self.Keys[
                'master'].pubkey

            self.UserSettings[
                'keys'][
                'master'][
                'encryptedprivkey'] = self.Keys[
                'master'].encryptedprivkey
            self.UserSettings['keys']['master']['generated'] = int(time.time())
            self.UserSettings['keys']['master']['expires'] = None
            self.UserSettings['keys']['master']['privkey'] = None

        self.UserSettings['keys']['posted'] = []
        for key in self.Keys['posted']:

            keydict = {}
            keydict['pubkey'] = key.pubkey
            keydict['encryptedprivkey'] = key.encryptedprivkey
            keydict['generated'] = key.generated
            keydict['expires'] = key.expires

            if key.expires > time.time():
                self.UserSettings['keys']['posted'].append(keydict)

        self.UserSettings['keys']['secret'] = []
        for key in self.Keys['secret']:

            keydict = {}
            keydict['pubkey'] = key.pubkey
            keydict['encryptedprivkey'] = key.encryptedprivkey
            keydict['generated'] = key.generated
            keydict['expires'] = key.expires

            if key.expires > time.time():
                self.UserSettings['keys']['secret'].append(keydict)

        self.UserSettings['passkey'] = None
        self.UserSettings['_id'] = self.Keys['master'].pubkey

    def restore_keys(self):
        """
        After being loaded in, re-create out key objects.
        """
        # Restore our master key
        if self.UserSettings['keys'].get('master') is not None:
            if 'encryptedprivkey' in self.UserSettings['keys']['master']:
                self.Keys['master'] = LockedKey(
                    pub=self.UserSettings['keys']['master']['pubkey'],
                    encryptedprivkey=self.UserSettings['keys']['master']['encryptedprivkey'])
                self.Keys[
                    'master'].generated = self.UserSettings[
                    'keys'][
                    'master'][
                    'generated']
                self.Keys[
                    'master'].expires = self.UserSettings[
                    'keys'][
                    'master'][
                    'expires']
                self.server.logger.info("Reconstructed with encryptedprivkey")
            else:
                # If we just have a pubkey string, do the best we can.
                if self.UserSettings['keys']['master'].get('pubkey'):
                    self.Keys['master'] = Key(
                        pub=self.UserSettings['keys']['master']['pubkey'])
                    self.Keys['master'].generated = self.UserSettings[
                        'keys']['master'].get('generated')
                    self.Keys['master'].expires = self.UserSettings[
                        'keys']['master'].get('expires')
                    self.server.logger.info(
                        "reconstructed user without privkey")
        else:
            print("Requested user had no master key.")
        # Restore any Posted communication keys.
        for key in self.UserSettings['keys'].get('posted', []):
            lk = LockedKey(
                pub=key['pubkey'],
                encryptedprivkey=key['encryptedprivkey'])
            lk.generated = key['generated']
            lk.expires = key['expires']
            self.Keys['posted'].append(lk)

        # Restore any oneoff communication keys
        for key in self.UserSettings['keys'].get('secret', []):
            lk = LockedKey(
                pub=key['pubkey'],
                encryptedprivkey=key['encryptedprivkey'])
            lk.generated = key['generated']
            lk.expires = key['expires']
            self.Keys['secret'].append(lk)

    def load_string(self, incomingstring):
        self.UserSettings = json.loads(
            incomingstring,
            object_pairs_hook=collections.OrderedDict,
            object_hook=collections.OrderedDict)
        # Sort our Posted keys.
        self.Keys['posted'].sort(key=lambda e: (e.expires), reverse=True)
        self.restore_keys()
        self.generate()

    def load_pubkey_only(self, pubkey):
        print("public only requested")
        self.UserSettings['keys']['master']['pubkey'] = pubkey
        self.load_string(json.dumps(self.UserSettings))

    def load_file(self, filename):
        filehandle = open(filename, 'r')
        filecontents = filehandle.read()
        self.load_string(filecontents)
        filehandle.close()

    def load_dict(self, userdict):
        self.UserSettings = userdict
        self.load_string(json.dumps(self.UserSettings))

    def savefile(self, filename=None):
        if filename is None:
            filename = self.UserSettings['username'] + ".TavernUser"

        self.presave_clean()
        filehandle = open(filename, 'w')
        filehandle.write(json.dumps(self.UserSettings, separators=(',', ':')))
        filehandle.close()

    def load_mongo_by_pubkey(self, pubkey):
        """
        Returns a user object for a given pubkey
        """

        # Get Formatted key for searching.
        tmpkey = Key(pub=pubkey)
        user = self.server.db.safe.find_one('users',
                                            {"keys.master.pubkey": tmpkey.pubkey})
        if user is not None:
            # If we find a local user, load in their priv and pub keys.
            self.load_string(json.dumps(user))
        else:
            # If the user doesn't exist in our service, he's only someone we've heard about.
            # We won't know their privkey, so load the pubkey, and then reload
            # the user
            print("Can't find user by pubkey. Using pub-only.")
            self.load_pubkey_only(pubkey)

    def load_mongo_by_sha512(self, sha):
        """
        Returns a user object for a given sha512
        """
        print("Trying to load : " + str(sha))
        user = self.server.db.unsafe.find_one('users', {'author_sha512': sha})
        if user is not None:
            self.load_string(json.dumps(user))
            print("Got it.")
            return True
        else:
            return False

    def load_mongo_by_username(self, username):
        # Local server Only
        user = self.server.db.safe.find_one('users',
                                            {"username": username})
        # If we're loading by username, it means you logged in.
        # Ensure settings are up to date

        if self.generate():
            self.savemongo()

        self.load_string(json.dumps(self.UserSettings))

    def savemongo(self):
        self.presave_clean()
        print("Saving User to mongo " +
              str(self.UserSettings['author_sha512']))
        self.server.db.safe.save('users', self.UserSettings)
