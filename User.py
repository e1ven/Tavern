import os,json
import platform
from Envelope import *
import time
from keys import *
import logging
from collections import OrderedDict
import pymongo
import pprint
from server import server
import scrypt
import random
import base64

class User(object):
      
    def __init__(self):
        self.UserSettings = OrderedDict()
        self.UserSettings['followedUsers'] = []
        self.UserSettings['followedTopics'] = []



    def randstr(self,length):
        return ''.join(chr(random.randint(0,255)) for i in range(length))
    def hash_password(self,password, maxtime=0.5, datalength=64):
        pword = scrypt.encrypt(self.randstr(datalength), password, maxtime=maxtime)

        return base64.b64encode(pword).decode('utf-8')

    def verify_password(self, guessed_password,hashed_password=None, maxtime=0.5):
        try:
            if hashed_password == None:
                hashed_password = self.UserSettings['hashedpass']
            pword = base64.b64decode(hashed_password.encode('utf-8'))
            scrypt.decrypt(pword, guessed_password, maxtime) 
            return True
        except scrypt.error:
            return False

    def getNote(self,noteabout):
        """ 
        Retrieve any note by user A about user B
        """
        # Make sure the key we're asking about is formatted right.
        # I don't trust myself ;)

        key = Keys(pub = noteabout )
        noteabout = key.pubkey

        
        # Retrieve the note from mongo

        note = server.mongos['default']['notes'].find_one({"user":self.Keys.pubkey,"noteabout":noteabout},as_class=OrderedDict)
        if note is not None:
            return note['note']
        else:
            return None

    def setNote(self,noteabout,note=""):
        
        # Format the Key.
        key = Keys(pub = noteabout )
        noteabout = key.pubkey

        newnote = {"user":self.Keys.pubkey,"noteabout":noteabout,"note":note}

        # Retrieve any existing note, so that the _id is the same. Then, we'll gut it, and put in our own values.
        newnote = server.mongos['default']['notes'].find_one({"user":self.Keys.pubkey,"noteabout":noteabout},as_class=OrderedDict)
        if newnote is None:
                newnote = {"user":self.Keys.pubkey,"noteabout":noteabout,"note":note}
        newnote['note'] = note
        server.mongos['default']['notes'].save(newnote) 


    def gatherTrust(self,askingabout,incomingtrust=250):
 
        # Ensure the formatting 
        key = Keys(pub = askingabout )
        askingabout = key.pubkey

        #print("My Key------" +  self.Keys.pubkey)
        #Rating of myself = 250
        #Direct Rating = 100
        #Friend's Rating = 40
        #FoF Rating = 16
        #FoFoF Rating = 6
        #FoFoFoF (etc) Rating = Not Counted.
        
        
        #Our opinion of everyone starts off Neutral
        trust = 0 
        #The Max trust we can return goes down by 40% each time.
        #I trust my self implicly, and I trust each FoF link 40% less.
        maxtrust = .4 * incomingtrust     

        #Check mongo to see if we've recently computed this trust value.
        #Don't keep computing it over and over and over.
        #We can probably bring this cache to be a pretty high number. 60+ secs
        cache = server.mongos['cache']['usertrusts'].find_one({"askingabout":askingabout,"incomingtrust":incomingtrust},as_class=OrderedDict)

        if cache is not None:
            if time.time() - cache['time'] < 20:
                print("Using cached trust")
                return cache['calculatedtrust']
                                
        #We trust ourselves implicitly       
        if askingabout == self.Keys.pubkey:
            print("I trust me.")
            return round(incomingtrust)

        #Don't recurse forever, please.  
        #Stop after 4 Friends-of-Friends = 100,40,16,6,0,0,0,0,0,0,0,0,0,0,0,0 etc     
        if incomingtrust <= 2:
            return 0
        divideby = 1
        #let's first check mongo to see if *THIS USER* directly rated the user we're checking for.
        #TODO - Let's change this to get the most recent. 
        print("Asking About -- " + askingabout)
        trustrow = server.mongos['default']['envelopes'].find({"envelope.payload.payload_type":"usertrust","envelope.payload.trusted_pubkey": str(askingabout), "envelope.payload.trust" : {"$exists":"true"},"envelope.payload.author.pubkey" : str(self.Keys.pubkey)  },as_class=OrderedDict).sort("envelope.local.time_added",pymongo.DESCENDING)
        foundtrust = False
        if trustrow.count() > 0:
            #Get the most recent trust
            tr = trustrow[0]    
            print("We trust this user directly.")
            pprint.pprint(tr)
            trust = int(tr['envelope']['payload']['trust'])
            foundtrust = True
        else:
            print("We have not directly rated this user.")
        if foundtrust == False:
            #If we didn't directly rate the user, let's see if any of our friends have rated him.

            #First, find the people WE'VE trusted
            alltrusted = server.mongos['default']['envelopes'].find({"envelope.payload.class" : "usertrust", "envelope.payload.trust" : {"$gt":0}, "envelope.payload.author.pubkey" : self.Keys.pubkey  },as_class=OrderedDict)
            combinedFriendTrust = 0
            friendcount = 0
            
            #Now, iterate through each of those people. This will be slow, which is why we cache.
            for trusted in alltrusted:
                friendcount += 1
                print("BTW- I trust" + trusted['envelope']['payload']['trusted_pubkey'] +" \n\n\n\n")
                u = User()
                u.load_mongo_by_pubkey(trusted['envelope']['payload']['trusted_pubkey'])
                combinedFriendTrust += u.gatherTrust(askingabout=askingabout,incomingtrust=maxtrust)
                print("My friend trusts this user at : " + str(u.gatherTrust(askingabout=askingabout,incomingtrust=maxtrust)))
            if friendcount > 0:    
                trust = combinedFriendTrust / friendcount
            print("total friend average" + str(trust))

        #Add up the trusts from our friends, and cap at MaxTrust
        if trust > maxtrust:
            trust = maxtrust
        if trust < (-1 * maxtrust):
            trust = (-1 * maxtrust)

        cachedict = OrderedDict()
        cachedict = {"_id": askingabout + str(incomingtrust), "askingabout":askingabout,"incomingtrust":incomingtrust,"calculatedtrust":trust,"time":time.time()}
        server.mongos['cache']['usertrusts'].save(cachedict)
        return round(trust)
    
    def getRatings(self,postInQuestion):            
        #Move this. Maybe to Server??
        allvotes = server.mongos['default']['envelopes'].find({"envelope.payload.class" : "rating", "envelope.payload.rating" : {"$exists":"true"},"envelope.payload.regarding" : postInQuestion },as_class=OrderedDict)
        combinedrating = 0
        for vote in allvotes:
            author = vote['envelope']['payload']['author']['pubkey']
            rating = vote['envelope']['payload']['rating']
            authorTrust = self.gatherTrust(askingabout=author)
            if authorTrust > 0:
                combinedrating += rating
                
        # Stamp based ratings give a baseline, like SpamAssassin. 
        e = server.mongos['default']['envelopes'].find_one({"envelope.payload_sha512" : postInQuestion},as_class=OrderedDict)
        
        if e is not None:
            if 'stamps' in e['envelope']: 
                stamps = e['envelope']['stamps']
                for stamp in stamps:
                    # if it was posted directly to Pluric.com, we can ip limit it, give it a +1
                    if stamp['class'] == "origin":
                        if stamp['pubkey'] == server.ServerKeys.pubkey:
                            combinedrating += 1
                        
        return combinedrating  
    
    def followUser(self,pubkey):
        if pubkey not in self.UserSettings['followedUsers']:
            self.UserSettings['followedUsers'].append(pubkey)

    def followTopic(self,topic):
        if topic not in self.UserSettings['followedTopics']:
            self.UserSettings['followedTopics'].append(topic)

    def noFollowUser(self,pubkey):
        if pubkey in self.UserSettings['followedUsers']:
            self.UserSettings['followedUsers'].remove(pubkey)

    def noFollowTopic(self,topic):
        if topic in self.UserSettings['followedTopics']:
            self.UserSettings['followedTopics'].remove(topic)    
                    
    def generate(self,email=None,hashedpass=None,username=None,skipkeys=False):
        """
        Fill in any missing user information
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
            self.UserSettings['email'] = "email@example.com"

        if hashedpass is not None:
            self.UserSettings['hashedpass'] = hashedpass
        elif not 'hashedpass' in self.UserSettings:
            self.hashedpass = None

        # Ensure we have a valid private key
        validpriv = False
        if 'privkey' in self.UserSettings:
            if self.UserSettings['privkey'] is not None:
                validpriv = True

        if not validpriv: 
            # If we don't have a public key, decide if we need one by the 'skipkeys' value
            # If we do, use the default system guest key.
            # If there isn't one, add one.
            # Adding this here, rather than on system start under Server, to avoid looping deps.
            if skipkeys != True:
                print("I was asked to make a key.")
                self.Keys = Keys()
                self.Keys.generate()
                self.Keys.format_keys()
                self.UserSettings['privkey'] = self.Keys.privkey
                self.UserSettings['pubkey'] = self.Keys.pubkey
            else:
                if 'guestacct' not in server.ServerSettings:
                    u = User()
                    u.generate(skipkeys=False)
                    server.ServerSettings['guestacct'] = u.UserSettings

                self.UserSettings['pubkey'] = server.ServerSettings['guestacct']['pubkey']
                self.UserSettings['privkey'] = None
                self.Keys = Keys(pub=self.UserSettings['pubkey'])


        
        if not 'time_created' in self.UserSettings:
            gmttime = time.gmtime()
            gmtstring = time.strftime("%Y-%m-%dT%H:%M:%SZ",gmttime)
            self.UserSettings['time_created'] = gmtstring


        if len(self.UserSettings['followedTopics']) == 0:
            self.followUser("StarTrek")
            self.followUser("Python")
            self.followUser("Egypt")
            self.followUser("Funny")

        if not 'maxposts' in self.UserSettings:
            self.UserSettings['maxposts'] = 50

        if not 'maxreplies' in self.UserSettings:
            self.UserSettings['maxreplies'] = 20

        if not 'friendlyname' in self.UserSettings:
            self.UserSettings['friendlyname'] = "Anonymous"

        if not 'include_location' in self.UserSettings:
            self.UserSettings['include_location'] = False

    def load_string(self,incomingstring):
        self.UserSettings = json.loads(incomingstring,object_pairs_hook=collections.OrderedDict,object_hook=collections.OrderedDict)
        self.Keys = Keys(pub=self.UserSettings['pubkey'],priv=self.UserSettings['privkey'])
        self.UserSettings['privkey'] = self.Keys.privkey
        self.UserSettings['pubkey'] = self.Keys.pubkey

    def load_file(self,filename):
        filehandle = open(filename, 'r')
        filecontents = filehandle.read()
        self.UserSettings = json.loads(filecontents,object_pairs_hook=collections.OrderedDict,object_hook=collections.OrderedDict)
        filehandle.close()    
        self.Keys = Keys(pub=self.UserSettings['pubkey'],priv=self.UserSettings['privkey'])
        self.UserSettings['privkey'] = self.Keys.privkey
        self.UserSettings['pubkey'] = self.Keys.pubkey
        
    def savefile(self,filename=None):
        self.Keys.format_keys()
        if filename == None:
            filename = self.UserSettings['username'] + ".PluricUser"                
        filehandle = open(filename,'w')   
        filehandle.write(json.dumps(self.UserSettings,separators=(',',':'))) 
        filehandle.close()
    
    def load_mongo_by_pubkey(self,pubkey):
        user = server.mongos['default']['users'].find_one({"pubkey":pubkey},as_class=OrderedDict)
        if user is None:
            #If the user doesn't exist in our service, he's only heard about.
            #We won't know their privkey, so just return their pubkey back out.
            self.Keys = Keys(pub=pubkey) 
        else:    
            #If we *do* find you locally, load in both Priv and Pubkeys
            #And load in the user settings.
            self.UserSettings = user
            self.Keys = Keys(pub=self.UserSettings['pubkey'],priv=self.UserSettings['privkey'])
            self.UserSettings['privkey'] = self.Keys.privkey
        self.UserSettings['pubkey'] = self.Keys.pubkey

    def load_mongo_by_username(self,username):
        #Local server Only
        print(username)
        user = server.mongos['default']['users'].find_one({"username":username},as_class=OrderedDict)
        self.UserSettings = user
        print(self.UserSettings['pubkey'])
        self.Keys = Keys(pub=self.UserSettings['pubkey'],priv=self.UserSettings['privkey'])
        self.UserSettings['privkey'] = self.Keys.privkey
        self.UserSettings['pubkey'] = self.Keys.pubkey
        print("Loaded username " + username + "..." + self.UserSettings['pubkey'])

    def savemongo(self):
        if not 'privkey' in self.UserSettings:
            self.Keys.generate()    
        self.Keys.format_keys()
        self.UserSettings['_id'] = self.Keys.pubkey
        server.mongos['default']['users'].save(self.UserSettings) 
            
