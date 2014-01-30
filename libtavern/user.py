import json
from collections import OrderedDict
import hashlib
import math
import libtavern.baseobj
import libtavern.lockedkey
import libtavern.utils

class User(libtavern.baseobj.Baseobj):

    def __init2__(self):
        self.username = None
        self.has_unique_key = False
        self.has_set_password = False
        self.has_login = False
        self.friendlyname = None

        self.emails = {}

        self.passkey = None
        self.lastauth = 0

        self.Keys = {}
        self.Keys['posted'] = [] # These keys are posted, either in a PM or a Message.
        self.Keys['master'] = None # This is the master key for the acct. Used to sign.


        # Only things that are changable settings
        # About the Tavern interface. Not Tavern-core stuff.
        self.UserSettings = {}
        self.UserSettings['followed_topics'] = []

    def generate(self, AllowGuestKey=True, password=None, email=None, username=None):
        """
        Create a Tavern user for this server.
        Add things like username/password/etc that aren't needed for ALL tavern users.

        Only creates keys if asked to.
        """
        # Create a string/immutable version of UserSettings that we can compare
        # against later to see if anything changed.

        tmpsettings = str(self.UserSettings) + str(self.Keys)

        # Only overwrite values if they aren't already set.
        if self.username is None:
             self.UserSettings['username'] = username

        if self.emails == {} and email is not None:
            self.emails[email] = {}
            self.emails[email]['confirmed'] = False
            self.emails[email]['added'] = libtavern.utils.inttime()

        if password is not None and self.passkey is None:
            self.passkey = self.Keys['master'].get_passkey(password=password)

        # Assign default user settings values
        if not 'followed_topics' in self.UserSettings:
            self.UserSettings['followed_topics'] = []
            for topic in self.server.serversettings.settings['usersettings']['followed_topics']:
                self.follow_topic(topic)

        if not 'maxposts' in self.UserSettings:
            self.UserSettings['maxposts'] = self.server.serversettings.settings['usersettings']['maxposts']

        if not 'maxreplies' in self.UserSettings:
            self.UserSettings['maxreplies'] = self.server.serversettings.settings['usersettings']['maxreplies']


        if not 'include_location' in self.UserSettings:
            self.UserSettings['include_location'] = self.server.serversettings.settings['usersettings']['include_location']

        if not 'ignore_edits' in self.UserSettings:
            self.UserSettings['ignore_edits'] = self.server.serversettings.settings['usersettings']['ignore_edits']

        if not 'allow_embed' in self.UserSettings:
            self.UserSettings['allow_embed'] = self.server.serversettings.settings['usersettings']['allow_embed']

        if not 'display_useragent' in self.UserSettings:
            self.UserSettings['allow_embed'] = self.server.serversettings.settings['usersettings']['display_useragent']

        if not 'theme' in self.UserSettings:
            self.UserSettings['theme'] = self.server.serversettings.settings['usersettings']['theme']

        # Set to none by default. T/F one user-set
        if not 'datauri' in self.UserSettings:
            self.UserSettings['datauri'] = None

        # Ensure we have valid master keys.
        # This will either be generated, or shared with the Server (Guest)

        if self.Keys['master'] is None:
            if AllowGuestKey:
                self.Keys = self.server.guestacct.Keys
                self.has_unique_key = False
                self.logger.debug("Set a user to the guest key")
            else:
                pulledkey = self.server.unusedkeycache.get(block=True)
                self.Keys['master'] = libtavern.lockedkey.LockedKey()
                self.Keys['master'].from_dict(pulledkey,passkey=pulledkey['passkey'])
                self.passkey = self.Keys['master'].passkey
                self.has_unique_key = True


        # The 'friendlyname' is a convienience for showing who they are.
        # It's appended before the wordhash.
        # If they have one, use it. If not, use Anonymous.
        # Set Friendlyname to most recent post, or Anonymous for lurkers

        if self.friendlyname is None:
            if self.has_unique_key:
                # This user is registered, they may have posted here before...
                posts = self.server.get_all_user_posts(self.Keys['master'].pubkey)
                if len(posts) > 0:
                    self.friendlyname = posts[0].dict['envelope']['local']['author']['friendlyname']

        # Ensure we have hashes based on the master key.
        self.author_wordhash = self.server.wordlist.wordhash(self.Keys['master'].pubkey)
        self.author_sha512 = hashlib.sha512(self.Keys['master'].pubkey.encode('utf-8')).hexdigest()

        # We can only login if we have some sort of username (username/oauth/email) + password
        if not self.has_login:
            for email in self.emails:
                if email is not None:
                    if email['confirmed'] is True:
                        self.has_login = True
            if self.username is not None:
                self.has_login = True

            # if self.facebooktoken is true..

        # Determine if we changed anything without an explicit dirty flag.
        if tmpsettings == str(self.UserSettings) + str(self.Keys):
            return False
        else:
            return True

    def new_posted_key(self):
        """
        Generate a new communication key.
        This key might be attached to a forum message, or a private message.

        By generating a new key for each message, even if our key does eventually leak
        it will be difficult to decode old messages, who's keys have been deleted.
        """

        if self.passkey is None:
            raise Exception("Must have a valid passkey to run this method")

        # Step 1, Create a new Key for this person.
        newkey = libtavern.lockedkey.LockedKey()
        newkey.generate(passkey=self.passkey, autoexpire=True)
        self.Keys['posted'].append(newkey)
        self.save_mongo()
        return newkey


    def verify_password(self, guessed_password, tryinverted=True):
        """Check a proposed password, to see if it's able to open and load a
        user's account."""

        successful = False
        try:
            tmp_passkey = self.Keys['master'].get_passkey(password)
            if self.Keys['master'].unlock(tmp_passkey):
                # We've successfully unlocked.
                self.lastauth = libtavern.utils.inttime()
                successful = True
        except:
            pass

        if successful:
            return True
        elif tryinverted:
            # Based on the FB-technique, as described at
            # http://blog.agilebits.com/2011/09/13/facebook-and-caps-lock-unintuitive-security/
            # Prevents users with Caplocks on
            return self.verify_password(guessed_password=guessed_password.swapcase(), tryinverted=False)
        else:
            return False


    def get_note(self, noteabout):
        """Retrieve any note by user A about user B."""
        # Make sure the key we're asking about is formatted right.
        # I don't trust myself ;)

        key = libtavern.key.Key(pub=noteabout)
        noteabout = key.pubkey
        # Retrieve the note from mongo
        note = self.server.db.unsafe.find_one(
            'notes', {"user": self.Keys['master'].pubkey, "noteabout": noteabout})
        if note is not None:
            return note['note']
        elif noteabout == self.Keys['master'].pubkey:
            # I'm asking about myself, and I haven't set a note yet.
            return "This is you!"
        else:
            return None

    def save_note(self, noteabout, note=""):
        """Save a note to mongo about a user"""

        # Format the Key.
        key = libtavern.key.Key(pub=noteabout)
        noteabout = key.pubkey

        # Retrieve any existing note.
        # We do this so we can them save the new note out as an update.

        newnote = self.server.db.unsafe.find_one('notes', {"user": self.Keys['master'].pubkey, "noteabout": noteabout})
        if newnote is None:
            newnote = {"user": self.Keys['master'].pubkey,"noteabout": noteabout, "note": note}
        newnote['note'] = note
        self.server.db.unsafe.save('notes', newnote)


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
        key = libtavern.key.Key(pub=askingabout)
        askingabout = key.pubkey

        # Our opinion of everyone starts off Neutral
        trust = 0

        # Set the maximum amount of trust we can return.
        # This is set to 40% of incoming - Incoming starts at 250, to ensure
        # that this goes to 100 for myself.
        maxtrust = .4 * incomingtrust

        # We trust ourselves implicitly
        if askingabout == self.Keys['master'].pubkey:
            self.logger.info("I trust me.")
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
            self.logger.info("I rated this user directly.")
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
                u.load_dict(
                    trusted['envelope']['payload']['trusted_pubkey'])
                # TODO -
                # MAKE THIS NOT LOAD BY PUBKEY
                # WE WANT TO RE-CREATE FROM PUBLIC DATA, NOT LOAD LOCALLY!!

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
            self.logger.info("total friend average" + str(trust))

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
        """Get the ratings of a specific message."""
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

    def follow_topic(self, topic):
        if topic not in self.UserSettings['followed_topics']:
            sorted_version = self.server.sorttopic(topic)
            self.UserSettings['followed_topics'].append(sorted_version)

    def unfollow_topic(self, topic):
        # Compare the lowercase/sorted values
        for followedtopic in self.UserSettings['followed_topics']:
            if self.server.sorttopic(followedtopic) == self.server.sorttopic(topic):
                self.UserSettings['followed_topics'].remove(followedtopic)

    def decrypt(self, text, passkey=None):
        """Decrypt a message sent to me, using one of my communication keys.

        Note - We don't try to decrypt using the master key, even though it's technically possible.
        This is intentional, so that other clients don't start sending PMs to the master key, and compromise security.

        """
        if self.passkey is not None:
            passkey = self.passkey

        for key in self.Keys['posted']:
            if isinstance(key, LockedKey):
                key.unlock(passkey)
            result = key.decrypt(text)

            if len(result) > 0:
                return result

    def get_pubkeys(self):
        """ Returns a list of all public keys for a user.
        Typically used to search for messages belonging to that user.
        :return: A list of all public keys.
        """
        keys = self.Keys['posted']
        keys.append(self.Keys['master'])
        pubs = []
        for key in Keys:
            pub.append(key.pubkey)
        return pubs

    def changepass(self, newpassword, oldpasskey=None):
        """
        Change the User's password.
        Since this password is used to encrypt all of the keys, we need to re-encrypt them as well.
        """

        if oldpasskey is None and self.passkey is not None:
            oldpasskey = self.passkey

        if self.Keys['master'].changepass(oldpasskey=oldpasskey, newpassword=newpassword):
            self.passkey = self.Keys['master'].get_passkey(newpassword)
            self.lastauth = libtavern.utils.inttime()
            self.has_set_password = True

            for key in self.Keys['posted']:
                key.changepass(oldpasskey=oldpasskey, newpassword=newpassword)
            self.save_mongo()
            return True

        else:
            return False

    def to_dict(self):
        """
        Marshall out the user obj a dictionary.
        """

        userdict = {}
        userdict['usersettings'] = self.UserSettings
        userdict['local']= {}
        userdict['local']['username'] = self.username
        userdict['local']['has_unique_key'] = self.has_unique_key
        userdict['local']['has_set_password'] = self.has_set_password
        userdict['local']['has_login'] = self.has_login
        userdict['local']['friendlyname'] = self.friendlyname
        userdict['local']['emails'] = self.emails

        # Dump master key
        userdict['keys'] = {}
        userdict['keys']['master'] = self.Keys['master'].to_dict()

        # Dump all posted keys
        userdict['keys']['posted'] = []
        for key in self.Keys['posted']:
            keydict = key.to_dict()
            if key.expires > libtavern.utils.inttime():
                userdict['keys']['posted'].append(keydict)

        userdict['_id'] = self.Keys['master'].pubkey
        return userdict


    def from_dict(self,userdict):
        """
        Demarshall a user obj from a dictionary.
        """

        self.UserSettings = userdict['usersettings']
        self.username = userdict['local']['username']
        self.has_unique_key = userdict['local']['has_unique_key']
        self.has_set_password = userdict['local']['has_set_password']
        self.has_login = userdict['local']['has_login']
        self.friendlyname = userdict['local']['friendlyname']
        self.emails = userdict['local']['emails']

        self.Keys = {}

        # Restore our master key
        self.Keys['master'] = libtavern.lockedkey.LockedKey()
        self.Keys['master'].from_dict(userdict['keys']['master'])
        self.logger.info("Reconstructed with encryptedprivkey")

        self.Keys['posted'] = []
        # Restore any posted communication keys
        for key in userdict['keys']['posted']:
            lk = libtavern.lockedkey.LockedKey()
            lk.from_dict(key)
            self.Keys['posted'].append(lk)

        self.Keys['posted'].sort(key=lambda e: (e.expires), reverse=True)
        self.generate()

    def load_string(self, incomingstring):
        userdict = json.loads(
            incomingstring,
            object_pairs_hook=OrderedDict,
            object_hook=OrderedDict)
        self.from_dict(userdict)

    def load_file(self, filename):
        filehandle = open(filename, 'r')
        filecontents = filehandle.read()
        self.load_string(filecontents)
        filehandle.close()


    def load_mongo_by_pubkey(self, pubkey):
        """Returns a user object for a given pubkey."""

        # Get Formatted key for searching.
        tmpkey = libtavern.key.Key(pub=pubkey)
        user = self.server.db.safe.find_one('users',{"keys.master.pubkey": tmpkey.pubkey})

        if user is not None:
            # If we find a local user, load in their priv and pub keys.
            self.load_string(json.dumps(user))
        else:
            return None

    def load_mongo_by_username(self, username):
        # Local server Only
        user = self.server.db.safe.find_one('users',
                                            {"username": username})
        if user is None:
            return None

        self.load_string(json.dumps(user))
    
    def load_mongo_by_sessionid(self,sessionid):
        """
        Load in a user, via their sessionid
        """
        session = self.server.sessions.safe.find_one('sessions',{"sessionid":sessionid})
        if session is None:
            return None
        elif session['expires'] < libtavern.utils.inttime():
            return None
        return self.load_mongo_by_pubkey(session['pubkey'])


    def save_file(self, filename=None):
        if filename is None:
            filename = self.UserSettings['username'] + ".TavernUser"

        userdict = self.to_dict()
        filehandle = open(filename, 'w')
        filehandle.write(json.dumps(userdict, separators=(',', ':')))
        filehandle.close()

    def save_mongo(self,overwriteguest=False):
        userdict = self.to_dict()

        if self.has_unique_key is True and self.Keys['master'].pubkey != self.server.guestacct.Keys['master'].pubkey or overwriteguest is True:
            self.logger.debug("Saving User to mongo ")
            self.server.db.safe.save('users', userdict)
        else:
            self.logger.debug("Cowardly refusing to overwrite Guest user")

    def save_session(self):
        """
        Save a session out to the DB.
        """
        sessiondict = {}
        sessiondict['sessionid'] = libtavern.utils.randstr(100)
        sessiondict['expires'] = libtavern.utils.inttime() + self.server.serversettings.settings['webtav']['session_lifetime']
        sessiondict['pubkey'] = self.Keys['master'].pubkey
        self.server.sessions.safe.save('sessions', sessiondict)
        return sessiondict['sessionid']
