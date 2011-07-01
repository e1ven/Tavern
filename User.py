import os,json
import M2Crypto
import platform
from Envelope import *
import time
from keys import *
import logging
import bcrypt
from collections import OrderedDict
import pymongo
from server import server

class User(object):
      
    def __init__(self):
        self.UserSettings = OrderedDict()
        self.UserSettings['local'] = OrderedDict()
        self.UserSettings['local']['followUser'] = []
        self.UserSettings['local']['followTopic'] = []

    def gatherTrust(self,askingabout,incomingtrust=250):
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
                print "Using cached trust"
                return cache['calculatedtrust']
                                
        #We trust ourselves implicitly       
        if askingabout == self.Keys.pubkey:
            print "I trust me."
            return round(incomingtrust)

        #Don't recurse forever, please.  
        #Stop after 4 Friends-of-Friends = 100,40,16,6,0,0,0,0,0,0,0,0,0,0,0,0 etc     
        if incomingtrust <= 2:
            return 0

        divideby = 1
        #let's first check mongo to see if *THIS USER* directly rated the user we're checking for.
        trustrow = server.mongos['default']['envelopes'].find_one({"envelope.payload.class" : "usertrust", "envelope.payload.pubkey" : str(askingabout), "envelope.payload.trust" : {"$exists":"true"}, "envelope.payload.author.pubkey" : self.UserSettings['pubkey']  },as_class=OrderedDict)
        
        foundtrust = False
        if trustrow is not None:
                trust = int(trustrow['envelope']['payload']['trust'])
                foundtrust = True
                
        if foundtrust == False:
            #If we didn't directly rate the user, let's see if any of our friends have rated him.
            #First, find the people WE'VE trusted.
            
            alltrusted = server.mongos['default']['envelopes'].find({"envelope.payload.class" : "usertrust", "envelope.payload.trust" : {"$gt":0}, "envelope.payload.author.pubkey" : self.UserSettings['pubkey']  },as_class=OrderedDict)
            combinedFriendTrust = 0
            friendcount = 0
            #Now, iterate through each of those people. This will be slow, which is why we cache.
            for trusted in alltrusted:
                friendcount += 1
                print "BTW- I trust" + trusted['envelope']['payload']['pubkey'] +" \n\n\n\n"
                u = User()
                u.load_mongo_by_pubkey(trusted['envelope']['payload']['pubkey'])
                combinedFriendTrust += u.gatherTrust(askingabout=askingabout,incomingtrust=maxtrust)
                print "My friend trusts this user at : " + str(u.gatherTrust(askingabout=askingabout,incomingtrust=maxtrust))
            if friendcount > 0:    
                trust = combinedFriendTrust / friendcount
            print "total friend average" + str(trust)

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
        
        return combinedrating  
    
    def followUser(self,pubkey):
        if pubkey not in self.UserSettings['local']['followUser']:
            self.UserSettings['local']['followUser'].append(pubkey)
            
    def followTopic(self,topictag):
        if pubkey not in self.UserSettings['local']['followTopic']:
            self.UserSettings['local']['followTopic'].append(topictag)

    def noFollowUser(self,pubkey):
        if pubkey in self.UserSettings['local']['followUser']:
            self.UserSettings['local']['followUser'].remove(pubkey)

    def noFollowTopic(self,topictag):
        if pubkey in self.UserSettings['local']['followTopic']:
            self.UserSettings['local']['followTopic'].remove(topictag)    
       
                
    def generate(self,email=None,hashedpass=None,pubkey=None,username=None):
        self.UserSettings['username'] = username
        self.UserSettings['friendlyname'] = username
        #username is specific to this service.
        #Move it to <local> ?
        #Friendlyname is the displayedname
        self.UserSettings['email'] = email
        self.UserSettings['hashedpass'] = hashedpass
        self.Keys = Keys()
        self.Keys.generate()
        self.UserSettings['privkey'] = self.Keys.privkey
        self.UserSettings['pubkey'] = self.Keys.pubkey
        
        gmttime = time.gmtime()
        gmtstring = time.strftime("%Y-%m-%dT%H:%M:%SZ",gmttime)
    
        self.UserSettings['time_created'] = gmtstring
            
    def load_file(self,filename):
        filehandle = open(filename, 'r')
        filecontents = filehandle.read()
        self.UserSettings = json.loads(filecontents,object_pairs_hook=collections.OrderedDict,object_hook=collections.OrderedDict)
        filehandle.close()    
        self.Keys = Keys(pub=self.UserSettings['pubkey'],priv=self.UserSettings['privkey'])
        self.UserSettings['privkey'] = self.Keys.privkey
        self.UserSettings['pubkey'] = self.Keys.pubkey
        
    def savefile(self,filename=None):
        if filename == None:
            filename = self.UserSettings['username'] + ".PluricUser"                
        filehandle = open(filename,'w')   
        filehandle.write(json.dumps(self.UserSettings,separators=(u',',u':'))) 
        filehandle.close()
    
    def load_mongo_by_pubkey(self,pubkey):
        user = server.mongos['default']['users'].find_one({"pubkey":pubkey},as_class=OrderedDict)
        self.UserSettings = user
        if self.UserSettings is None:
            #If the user doesn't exist in our service, he's only heard about.
            #We won't know their privkey, so just return their pubkey back out.
            self.Keys = Keys(pub=pubkey) 
        else:    
            #If we *do* find you locally, load in both Priv and Pubkeys
            self.Keys = Keys(pub=self.UserSettings['pubkey'],priv=self.UserSettings['privkey'])
            self.UserSettings['privkey'] = self.Keys.privkey
        self.UserSettings['pubkey'] = self.Keys.pubkey

    def load_mongo_by_username(self,username):
        #Local server Only
        user = server.mongos['default']['users'].find_one({"username":username},as_class=OrderedDict)
        self.UserSettings = user
        self.Keys = Keys(pub=self.UserSettings['pubkey'],priv=self.UserSettings['privkey'])
        self.UserSettings['privkey'] = self.Keys.privkey
        self.UserSettings['pubkey'] = self.Keys.pubkey

    def savemongo(self):
        self.UserSettings['_id'] = self.UserSettings['pubkey']
        server.mongos['default']['users'].save(self.UserSettings) 
            
