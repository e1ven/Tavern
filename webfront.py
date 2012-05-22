#!/usr/bin/env python3
#
# Copyright 2011 Pluric
    

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.escape
import time
import datetime
import os
import random
import socket
import json
from Envelope import Envelope
from collections import OrderedDict
import pymongo
from tornado.options import define, options
from server import server
import pygeoip
import pprint
from keys import *
from User import User
from gridfs import GridFS
import hashlib
import urllib.request, urllib.parse, urllib.error
#import TopicList
import urllib.request, urllib.parse, urllib.error
from bs4 import BeautifulSoup
import rss

import re
try: 
    from hashlib import md5 as md5_func
except ImportError:
    from md5 import new as md5_func
import NofollowExtension


class BaseHandler(tornado.web.RequestHandler):
    
    """
    The BaseHandler is the baseclass for all objects in the webserver.
    It is not expected to ever be instantiated directly.
    It's main uses are:
        * Handle Cookies/logins
        * Allow modules to update just PARTS of the page
    """
    
    def __init__(self, *args, **kwargs):
        #Ensure we have a html variable set.
        self.html = ""
        super(BaseHandler,self).__init__(*args,**kwargs)
        
    def write(self,html):
        if hasattr(html, 'decode'):
            self.html += html.decode('utf-8')
        else:
             self.html += html
        #self.set_header("X-Fortune", server.fortune.random())
             
    def gettext(self):
        ptext = ""
        for a in self.pagetext:
            ptext = ptext + a
        self.write(ptext)
        

    def finish(self,divs=['limits'],message=None):
        if "js" in self.request.arguments:
            if "singlediv" in self.request.arguments:
                divs = [self.get_argument('singlediv')]
            #if JS is set at all, send the JS script version.
            for div in divs:
                super(BaseHandler, self).write(self.getjs(div))

        elif "getonly" in self.request.arguments:
            #Get ONLY the div content marked
            for div in divs:
                super(BaseHandler, self).write(self.getdiv(div))
        else:
            super(BaseHandler, self).write(self.html)
        super(BaseHandler,self).finish(message) 
   
    def getdiv(self,element):
        soup = BeautifulSoup(self.html)
        soupyelement = soup.find(id=element)
        soupytxt = ""
        if soupyelement is not None:
            for child in soupyelement.contents:
                soupytxt += str(child)
        return soupytxt
        
    def getjs(self,element):
        """ 
        Get the element text, remove all linebreaks, and escape it up.
        Then, send that as a document replacement
        Also, rewrite the document history in the browser, so the URL looks normal.
        """
        jsvar = self.request.uri.find("js=")
        if jsvar > -1:
            #This should always be true    
            #But Are there other params?
            nextvar = self.request.uri.find("&",jsvar)
            if nextvar > 0:
                #There are Additional Variables in this URL
                finish = "?" + self.request.uri[nextvar+1:len(self.request.uri)]
            else:
                print("No Next variables")
                #There are no other variables. Delete until End of string
                finish = ""
                
            modifiedurl = self.request.uri[0:self.request.uri.find("js=") -1] + finish
            
            #Also strip out the "timestamp" param
            jsvar = modifiedurl.find("timestamp=")
            if jsvar > -1:
                #This should always be true    
                #But Are there other params?
                nextvar = modifiedurl.find("&",jsvar)
                if nextvar > 0:
                    #There are Additional Variables in this URL
                    finish = "?" + modifiedurl[nextvar+1:len(modifiedurl)]
                else:
                    print("No Next variables")
                    #There are no other variables. Delete until End of string
                    finish = ""
                modifiedurl = modifiedurl[0:modifiedurl.find("timestamp=") -1] + finish



        soup = BeautifulSoup(self.html)    
        soupyelement = soup.find(id=element)
        newtitle = soup.html.head.title.string.rstrip().lstrip()
        
        soupytxt = ""
        if soupyelement is not None:
            for child in soupyelement.contents:
                soupytxt += str(child)

        escapedtext = soupytxt.replace("\"","\\\"")
        escapedtext = escapedtext.replace("\n","")
        
        return ( '''var pluric_replace = function() 
                {
                    var stateObj = 
                    {
                        title: document.title,
                        url: window.location.pathname 
                    };
                    document.title = "''' + newtitle + ''' ";
                    if (typeof history.pushState !== "undefined")
                    {
                        window.history.pushState(stateObj, "","''' + modifiedurl + '''");
                    }
                    document.getElementById("''' + element + '''").innerHTML="''' + escapedtext + '''";
                    $('div#''' + element  + ''' a.internal').each( function ()
                    {            
                        $(this).click(function()
                        {   
                            $("#spinner").height($(this).parent().height());
                            $("#spinner").width($(this).parent().width());
                            $("#spinner").css("top", $(this).parent().offset().top).css("left", $(this).parent().offset().left).show();
                            head.js($(this).attr('link-destination') + "?js=yes&timestamp=" + Math.round(new Date().getTime())  );            
                            return false;
                        });
                        $(this).attr("link-destination",this.href);
                    });
                    $('#spinner').hide();
                };
                pluric_replace();
                pluric_replace = null;
                ''' + server.cache['instance.js'] 
                + 
                '''
                // Any other code here.
                '''
                )


    def chunks(self,s, n):
        """
        Produce `n`-character chunks from `s`.
        """
        for start in range(0, len(s), n):
            yield s[start:start+n]

    def setvars(self):
        """
        Saves out the current userobject to a cookie, or series of cookies.
        These are encrypted using the built-in Tornado cookie encryption.
        """
        
        # Zero out the stuff in 'local', since it's big.
        usersettings = self.user.UserSettings

        # Create the Cookie value, and sign it.
        signed = self.create_signed_value("pluric_preferences",json.dumps(usersettings))

        # Chunk up the cookie value, so we can spread across multiple cookies.
        numchunks = 0
        for chunk in self.chunks(signed,3000):
            numchunks += 1
            self.set_cookie("pluric_preferences" + str(numchunks),chunk,httponly=True,expires_days=999999)
        self.set_secure_cookie("pluric_preferences_count",str(numchunks),httponly=True,expires_days=999999)
        print("numchunks + " + str(numchunks))

        print("Setting :::: " + json.dumps(usersettings))

    def getvars(self,ensurekeys=False):
        """
        Retrieve the basic user variables out of your cookies.
        """

        self.user = User()
        if self.get_secure_cookie("pluric_preferences_count") is not None:

            # Restore the signed cookie, across many chunks
            restoredcookie = ""
            for i in range(1,1 + int(self.get_secure_cookie("pluric_preferences_count"))):
                restoredcookie += self.get_cookie("pluric_preferences" + str(i))

            # Validate the cookie, and load if it passes
            decodedcookie = self.get_secure_cookie("pluric_preferences",value=restoredcookie)
            if decodedcookie is not None:
                self.user.load_string(decodedcookie.decode('utf-8'))
            else:
                print("Cookie doesn't validate")

        # If there isn't already a cookie, make a very basic one.
        # Don't bother doing the keys, since that eats randomness.
        else:
            print("Making cookies")
            self.user.generate(skipkeys=True)
            self.setvars()

        # If we've asked to make the keys.. Generate them.
        # This won't overwrite existing values, since user.generate() is additive.
        if ensurekeys == True:
            if self.user.UserSettings['privkey'] is None:
                print("Making key cookies")
                self.user.generate(skipkeys=False)
                self.setvars()
                self.user.savemongo()

        return self.user.UserSettings['username']


class RSSHandler(BaseHandler):
    def get(self,action,param):
        if action =="topic":
            channel = rss.Channel('ForumLegion - ' + param,
                          'http://ForumLegion.ch/rss/' + param,
                          'ForumLegion discussion about ' + param,
                          generator = 'ForumLegion',
                          pubdate = datetime.datetime.now())
            for envelope in server.mongos['default']['envelopes'].find({'envelope.local.sorttopic' : server.sorttopic(param),'envelope.payload.class':'message'},limit=100,as_class=OrderedDict).sort('envelope.local.time_added',pymongo.ASCENDING):
                item = rss.Item(channel,
                    envelope['envelope']['payload']['subject'],
                    "http://ForumLegion.ch/message/" + envelope['envelope']['local']['short_subject'] + "/" + envelope['envelope']['payload_sha512'],
                    envelope['envelope']['local']['formattedbody'])
                channel.additem(item)
            self.write(channel.toprettyxml())
                      
                          

class TriPaneHandler(BaseHandler):
    
    """ 
    The TriPane Handler is the beefiest handler in the project.
    It renders the main tri-panel interface, and only pushes out the parts that are needed.
    """            
    
    def get(self,param1=None,param2=None,param3=None):
        self.getvars()
               
        # We want to assign the parameters differently, depending on how many there are.
        # Normally, we'd just say get(action=None,param=None,bullshit=None)
        # But in this scenerio, we want the second param to be the text, if there are three, and have the ID as #3
        # But if there are only two, the second param should be the ID.


        # Count up our number of parameters.
        if param3 == None:
            if param2 == None:
                if param1 == None:
                    numparams = 0
                else:
                    numparams = 1
            else:
                numparams = 2
        else:
            numparams = 3
            
            
        #Decide what to do, based on the number of incoming actions.    
        if numparams < 2:
            # Defaults all around
            action = "topic"
            topic = "sitecontent"
        else:
            action = tornado.escape.xhtml_escape(param1) 
            if action == "t" or action == "topic" or action == "topictag":
                action = "topic"
            elif action == "m" or action == "message":
                action = "message"
            else:
                action = "message"

            if action == "message":       
                if numparams == 2:
                    messageid = tornado.escape.xhtml_escape(param2)
                if numparams == 3:
                    messageid = tornado.escape.xhtml_escape(param3)
            elif action == "topic":
                topic = tornado.escape.xhtml_escape(param2)
                    
        #TODO KILL THIS!!
        #THIS WILL WASTE CPU
        #tl = TopicList.TopicList()                
        
        divs = []
        toptopics = []
        for quicktopic in server.mongos['default']['topiclist'].find(limit=14,as_class=OrderedDict).sort('value',-1):
            toptopics.append(quicktopic)

        print(action)                        
        if action == "topic":
            # If you change the topic, refresh all three panels.
            divs.append("left")
            divs.append("center")
            divs.append("right")

            subjects = []
            if topic != "all":
                for envelope in server.mongos['default']['envelopes'].find({'envelope.local.sorttopic' : server.sorttopic(topic),'envelope.payload.class':'message','envelope.payload.regarding':{'$exists':False}},limit=self.user.UserSettings['maxposts'],as_class=OrderedDict).sort('envelope.local.time_added',pymongo.DESCENDING):
                    subjects.append(envelope)
            else:
                for envelope in server.mongos['default']['envelopes'].find({'envelope.payload.class':'message','envelope.payload.regarding':{'$exists':False}},limit=self.user.UserSettings['maxposts'],as_class=OrderedDict).sort('envelope.local.time_added',pymongo.DESCENDING):
                    subjects.append(envelope)

            if len(subjects) > 0:
                displayenvelope = subjects[0]
                messageid = subjects[0]['envelope']['payload_sha512'] 
            else:
                displayenvelope = None
                     
            canon="topic/" + topic 
            title=topic
 
        if action == "message":
            divs.append("center")
            divs.append("right")

            displayenvelope = server.mongos['default']['envelopes'].find_one({'envelope.payload_sha512' : messageid },as_class=OrderedDict)
            if displayenvelope is not None:
                topic = displayenvelope['envelope']['payload']['topic']
                subjects = []
                for envelope in server.mongos['default']['envelopes'].find({'envelope.local.sorttopic' : server.sorttopic(topic),'envelope.payload.class':'message','envelope.payload.regarding':{'$exists':False}},limit=self.user.UserSettings['maxposts'],as_class=OrderedDict).sort('envelope.local.time_added',pymongo.DESCENDING):
                    subjects.append(envelope)
                canon="message/" + displayenvelope['envelope']['local']['short_subject'] + "/" + displayenvelope['envelope']['payload_sha512']
                title = displayenvelope['envelope']['payload']['subject']
            
        if displayenvelope is None:
            # Can't find a message ;(
            e = server.error_envelope("Can't find your message")
            displayenvelope = e.dict
            messageid = e.payload.hash()
            title = "Can't find your message"
            topic = "sitecontent"
            canon="message/" + displayenvelope['envelope']['local']['short_subject'] + "/" + displayenvelope['envelope']['payload_sha512']
            subjects = []
            for envelope in server.mongos['default']['envelopes'].find({'envelope.local.sorttopic' : server.sorttopic(topic),'envelope.payload.class':'message','envelope.payload.regarding':{'$exists':False}},limit=self.user.UserSettings['maxposts'],as_class=OrderedDict).sort('envelope.local.time_added',pymongo.DESCENDING):
                subjects.append(envelope)

        usertrust = self.user.gatherTrust(displayenvelope['envelope']['payload']['author']['pubkey'])
        messagerating = self.user.getRatings(messageid)
        displayenvelope = server.formatEnvelope(displayenvelope)
        displayenvelope['envelope']['local']['messagerating'] = messagerating
    
        #Gather up all the replies to this message, so we can send those to the template as well
        self.write(self.render_string('header.html',title=title,user=self.user,canon=canon,type="topic",rsshead=displayenvelope['envelope']['payload']['topic']))
        self.write(self.render_string('tripane.html',topic=topic,user=self.user,toptopics=toptopics,subjects=subjects,envelope=displayenvelope))
        self.write(self.render_string('footer.html'))  
           
        pprint.pprint(divs)   
        if action == "message" or action == "topic":
            self.finish(divs=divs)
        else:
            self.finish()
      
class TopicPropertiesHandler(BaseHandler):
    def get(self,topic):
        self.getvars()

        client_topic = tornado.escape.xhtml_escape(topic)

        mods = []
        for mod in server.mongos['default']['modlist'].find({'_id.topic':server.sorttopic(topic)},as_class=OrderedDict,max_scan=10000).sort('value.trust',direction=pymongo.DESCENDING):
            pprint.pprint(mod)
            mod['_id']['moderator_pubkey_sha512'] = hashlib.sha512(mod['_id']['moderator'].encode('utf-8')).hexdigest() 
            mods.append(mod)

        toptopics = []
        for quicktopic in server.mongos['default']['topiclist'].find(limit=10,as_class=OrderedDict).sort('value',-1):
            toptopics.append(quicktopic)
        subjects = []
        for envelope in server.mongos['default']['envelopes'].find({'envelope.local.sorttopic' : server.sorttopic(topic),'envelope.payload.class':'message','envelope.payload.regarding':{'$exists':False}},limit=self.user.UserSettings['maxposts'],as_class=OrderedDict):
            subjects.append(envelope)

        title = "Properties for " + topic    
        self.write(self.render_string('header.html',title=title,user=self.user,rsshead=topic,type="topic"))
        self.write(self.render_string('topicprefs.html',user=self.user,topic=topic,toptopics=toptopics,subjects=subjects,mods=mods))
        self.write(self.render_string('footer.html'))  
        self.finish(divs=['right'])

class SiteContentHandler(BaseHandler):        
    def get(self,message):
        self.getvars()
        client_message_id = tornado.escape.xhtml_escape(message)
        
        envelope = server.mongos['default']['envelopes'].find_one({'envelope.payload_sha512' : client_message_id },as_class=OrderedDict)
        envelope = server.formatEnvelope(envelope)

            
        self.write(self.render_string('header.html',title="Pluric :: " + envelope['envelope']['payload']['subject'],user=self.user,canon="sitecontent/" + envelope['envelope']['payload_sha512'],rss="/rss/topic/" + envelope['envelope']['payload']['topic'],topic=envelope['envelope']['payload']['topic']))
        self.write(self.render_string('sitecontent.html',formattedbody=envelope['envelope']['local']['formattedbody'],envelope=envelope))
        self.write(self.render_string('footer.html'))
 
class PrivateMessageHandler(BaseHandler):        
    def get(self,message):
        self.getvars()
        client_message_id = tornado.escape.xhtml_escape(message)

        envelope = server.mongos['default']['envelopes'].find_one({'envelope.payload_sha512' : client_message_id },as_class=OrderedDict)

        usertrust = self.user.gatherTrust(envelope['envelope']['payload']['author']['pubkey'])
        
        envelope['envelope']['payload']['body'] = self.user.Keys.decryptToSelf(envelope['envelope']['payload']['body'])
        envelope['envelope']['payload']['subject'] = self.user.Keys.decryptToSelf(envelope['envelope']['payload']['subject'])

        if 'formatting' in envelope['envelope']['payload']:
                formattedbody = server.formatText(text=envelope['envelope']['payload']['body'],formatting=envelope['envelope']['payload']['formatting'])
        else:    
                formattedbody = server.formatText(text=envelope['envelope']['payload']['body'])

        self.write(self.render_string('header.html',title="Pluric :: " + envelope['envelope']['payload']['subject'],user=self.user,type="privatemessage",rsshead=None))
        self.write(self.render_string('singleprivatemessage.html',formattedbody=formattedbody,usertrust=usertrust,envelope=envelope))
        self.write(self.render_string('footer.html'))




class RegisterHandler(BaseHandler):
    def get(self):
        self.getvars()
        self.write(self.render_string('header.html',title="Register for an Account",user=self.user,type=None,rsshead=None))
        self.write(self.render_string('registerform.html'))
        self.write(self.render_string('footer.html'))
    def post(self):
        self.getvars()
        self.write(self.render_string('header.html',title='Register for an account',user=self.user,type=None,rsshead=None))

        client_newuser =  tornado.escape.xhtml_escape(self.get_argument("username"))
        client_newpass =  tornado.escape.xhtml_escape(self.get_argument("pass"))
        client_newpass2 = tornado.escape.xhtml_escape(self.get_argument("pass2"))
        if "email" in self.request.arguments:
            client_email = tornado.escape.xhtml_escape(self.get_argument("email"))
            if client_email == "":
                client_email = None
        else:
            client_email = None     
            
        if client_newpass != client_newpass2:
            self.write("I'm sorry, your passwords don't match.") 
            return

        if client_email is not None:
            users_with_this_email = server.mongos['default']['users'].find({"email":client_email.lower()},as_class=OrderedDict)
            if users_with_this_email.count() > 0:
                self.write("I'm sorry, this email address has already been used.")  
                return
            
        users_with_this_username = server.mongos['default']['users'].find({"username":client_newuser.lower()},as_class=OrderedDict)
        if users_with_this_username.count() > 0:
            self.write("I'm sorry, this username has already been taken.")  
            return    
            
        else:
            hashedpass = self.user.hash_password(client_newpass)
            self.user.generate(hashedpass=hashedpass,username=client_newuser.lower())
            if client_email is not None:
                self.user.UserSettings['email'] = client_email.lower()
            self.user.savemongo()
            self.setvars()
            self.redirect("/")


class LoginHandler(BaseHandler):
    def get(self):
        self.getvars()        
        self.write(self.render_string('header.html',title="Login to your account",user=self.user,rsshead=None,type=None))
        self.write(self.render_string('loginform.html'))
        self.write(self.render_string('footer.html'))
    def post(self):
        self.getvars()
        self.write(self.render_string('header.html',title='Login to your account',user=self.user,rsshead=None,type=None))

        client_username =  tornado.escape.xhtml_escape(self.get_argument("username"))
        client_password =  tornado.escape.xhtml_escape(self.get_argument("pass"))

        login = False
        user = server.mongos['default']['users'].find_one({"username":client_username.lower()},as_class=OrderedDict)
        if user is not None:
            u = User()
            u.load_mongo_by_username(username=client_username.lower())
            
            # Allow four forms of password
            # Normal password
            # swapped case (caps lock)
            # First letter as upper if you initially signed up on mobile
            # First form lower, as if you're on mobile now.
            
            if u.verify_password(client_password):
                login = True
            elif u.verify_password(client_password.swapcase()):
                    login = True
            elif u.verify_password(client_password[:1].upper() + client_password[1:]):
                    login = True
            elif u.verify_password(client_password[:1].lower() + client_password[1:]):
                    login = True
            if login == True:
                self.user = u
                pprint.pprint(u.UserSettings)
                self.setvars()
                print("Login Successful.")
                pprint.pprint(self.user.UserSettings)
                self.redirect("/")
                return

            print("Username/password fail." + client_password[:1].upper() + client_password[1:])
            self.redirect("http://Google.com")

class LogoutHandler(BaseHandler):
     def post(self):
         self.clear_all_cookies()
         self.redirect("/")

class UserHandler(BaseHandler):
    def get(self,pubkey):
        self.getvars()
        
        #Unquote it, then convert it to a PluricKey object so we can rebuild it.
        #Quoting destroys the newlines.
        pubkey = urllib.parse.unquote(pubkey)

        #Reformat it correctly
        k = Keys(pub=pubkey)
        pubkey = k.pubkey
        print(pubkey)
        messages = []
        self.write(self.render_string('header.html',title="Welcome to Pluric!",user=self.user,rsshead=None,type=None))

        for message in server.mongos['default']['envelopes'].find({'envelope.payload.author.pubkey':pubkey},as_class=OrderedDict).sort('value',-1):
            messages.append(message)

        self.write(self.render_string('showuserposts.html',messages=messages))
        self.write(self.render_string('footer.html'))
                 
                 
class FollowUserHandler(BaseHandler):

    def post(self):    
        self.getvars()
        self.user.followUser(tornado.escape.xhtml_escape(self.get_argument("pubkey")))
        self.user.savemongo()
        self.servars()

        if "js" in self.request.arguments:
            self.finish(divs=['right'])
        else:
            self.redirect("/")

class NoFollowUserHandler(BaseHandler):

    def post(self):    
        self.getvars()
        self.user.noFollowUser(tornado.escape.xhtml_escape(self.get_argument("pubkey")))
        self.user.savemongo()
        self.setvars()

        if "js" in self.request.arguments:
            self.finish(divs=['right'])
        else:
            self.redirect("/")

class FollowTopicHandler(BaseHandler):

    def post(self):    
        self.getvars()

        self.user.followTopic(tornado.escape.xhtml_escape(self.get_argument("topic")))
        self.user.savemongo()
        self.setvars()

        if "js" in self.request.arguments:
            self.finish(divs=['right'])
        else:
            self.redirect("/")

class NoFollowTopicHandler(BaseHandler):
    def post(self):       
        self.getvars()

        self.user.noFollowTopic(tornado.escape.xhtml_escape(self.get_argument("topic")))
        self.user.savemongo()
        self.setvars()

        if "js" in self.request.arguments:
            self.finish(divs=['right'])
        else:
            self.redirect("/")
        

class RatingHandler(BaseHandler):
    def get(self,posthash):
        self.getvars()
        #Calculate the votes for that post. 
         
    def post(self):    
        self.getvars(ensurekeys=True)

        #So you may be asking yourself.. Self, why did we do this as a POST, rather than
        #Just a GET value, of the form server.com/msg123/voteup
        #The answer is xsrf protection.
        #We don't want people to link to the upvote button and trick you into voting up.

        
        client_hash =  tornado.escape.xhtml_escape(self.get_argument("hash"))        
        client_rating =  tornado.escape.xhtml_escape(self.get_argument("rating"))
        rating_val = int(client_rating)
        if rating_val not in [-1,0,1]:
            self.write("Invalid Rating.")
            return -1
        
        e = Envelope()
        e.payload.dict['class'] = "rating"
        e.payload.dict['rating'] = rating_val
        e.payload.dict['regarding'] = client_hash
            
        #Instantiate the user who's currently logged in
        
        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['pubkey'] = self.user.UserSettings['pubkey']
        e.payload.dict['author']['friendlyname'] = self.user.UserSettings['username']
        e.payload.dict['author']['useragent'] = "Pluric Web frontend Pre-release 0.1"
        if self.user.UserSettings['include_location'] == True or 'include_location' in self.request.arguments:
            gi = pygeoip.GeoIP('/usr/local/share/GeoIP/GeoIPCity.dat')
            ip = self.request.remote_ip
            
            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"
                
            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + "," + str(gir['longitude'])
        
        #Sign this bad boy
        usersig = self.user.Keys.signstring(e.payload.text())
        
        stamp = OrderedDict()
        stamp['class'] = 'author'
        stamp['pubkey'] = self.user.UserSettings['pubkey']
        stamp['signature'] = usersig
        utctime = time.time()
        stamp['time_added'] = int(utctime)
        stamplist = []
        stamplist.append(stamp)
        e.dict['envelope']['stamps'] = stamplist
        
        #Send to the server
        server.receiveEnvelope(e.text())
        
        self.write("Your vote has been recorded. Thanks!")


class UserNoteHandler(BaseHandler):
    def get(self,user):
        self.getvars()
        #Show the Note for a user

    def post(self):    
        self.getvars(ensurekeys=True)

        client_pubkey = self.get_argument("pubkey")    
        client_note = self.get_argument("note")
        self.user.setNote(client_pubkey,client_note)
        print("Note Submitted.")




class UserTrustHandler(BaseHandler):
    def get(self,user):
        self.getvars()
        #Calculate the trust for a user. 

    def post(self):    
        self.getvars(ensurekeys=True)

        client_trusted_pubkey =  self.get_argument("trusted_pubkey")    
        client_trust =  self.get_argument("trust")
        client_topic =  self.get_argument("topic")


        trust_val = int(client_trust)
        if trust_val not in [-100,0,100]:
            self.write("Invalid Trust Score.")
            return -1
        

        e = Envelope()
        e.payload.dict['class'] = "usertrust"
        e.payload.dict['trust'] = trust_val
        e.payload.dict['topic'] = client_topic   
        k = Keys(pub=client_trusted_pubkey)
        e.payload.dict['trusted_pubkey'] = k.pubkey

        #Instantiate the user who's currently logged in


        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['pubkey'] = self.user.UserSettings['pubkey']
        e.payload.dict['author']['friendlyname'] = self.user.UserSettings['username']
        e.payload.dict['author']['useragent'] = "Pluric Web frontend Pre-release 0.1"


        if self.user.UserSettings['include_location'] == True or 'include_location' in self.request.arguments:
            gi = pygeoip.GeoIP('/usr/local/share/GeoIP/GeoIPCity.dat')
            ip = self.request.remote_ip

            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"

            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + "," + str(gir['longitude'])

        #Sign this bad boy
        usersig = self.user.Keys.signstring(e.payload.text())
        
        stamp = OrderedDict()
        stamp['class'] = 'author'
        stamp['pubkey'] = self.user.UserSettings['pubkey']
        stamp['signature'] = usersig
        utctime = time.time()
        stamp['time_added'] = int(utctime)
        stamplist = []
        stamplist.append(stamp)
        e.dict['envelope']['stamps'] = stamplist
        
        
        #Send to the server
        server.receiveEnvelope(e.text())
        print("Trust Submitted.")


      
class NewmessageHandler(BaseHandler):
    def get(self,topic=None,regarding=None):
         self.getvars()
         self.write(self.render_string('header.html',title="Post a new message",user=self.user,rsshead=None,type=None))
         self.write(self.render_string('newmessageform.html',regarding=regarding,topic=topic,args=self.request.arguments))
         self.write(self.render_string('footer.html'))
         self.finish(divs=['right','single'])

    def post(self):
        self.getvars(ensurekeys=True)
        client_body =  tornado.escape.xhtml_escape(self.get_argument("body"))

        # Pull in our Form variables. 
        # The reason for the uncertainty is the from can be used two ways; One for replies, one for new messages.
        # It acts differently in the two scenerios.
        if "topic" in self.request.arguments:
            client_topic = tornado.escape.xhtml_escape(self.get_argument("topic"))
            if client_topic == "":
                client_topic = None
        else:
            client_topic = None
        if "subject" in self.request.arguments:
            client_subject = tornado.escape.xhtml_escape(self.get_argument("subject"))
            if client_subject == "":
                client_subject = None  
        else:
            client_subject = None
        if "regarding" in self.request.arguments:
            client_regarding = tornado.escape.xhtml_escape(self.get_argument("regarding"))
            if client_regarding == "":
                client_regarding = None
        else:
            client_regarding = None
     
        #Build a list of all the variables that come in with attached_fileX, 
        #so we can parse them later on. attached_fileXXXX.path
        filelist = []
        for argument in self.request.arguments:
            if argument.startswith("attached_file") and argument.endswith('.path'):
                filelist.append(argument.rsplit('.')[0])
        #Uniquify list
        filelist = list(dict([(i,1) for i in filelist]).keys())
        #Use this flag to know if we successfully stored or not.
        stored = False   
        client_filepath = None     
        envelopebinarylist = []
        for attached_file in filelist:
            #I've testing including this var via the page directly. 
            #It's safe to trust this path, it seems.
            #All the same, let's strip out all but the basename.
            
            client_filepath =  tornado.escape.xhtml_escape(self.get_argument(attached_file + ".path"))
            client_filetype =  tornado.escape.xhtml_escape(self.get_argument(attached_file + ".content_type"))
            client_filename =  tornado.escape.xhtml_escape(self.get_argument(attached_file + ".name"))
            client_filesize =  tornado.escape.xhtml_escape(self.get_argument(attached_file + ".size"))
           
            print("Trying client_filepath of " + client_filepath ) 
            fs_basename = os.path.basename(client_filepath)
            fullpath = server.ServerSettings['upload-dir'] + "/" + fs_basename
            print("Taking Hash!") 

            #Hash the file in chunks
            SHA512 = hashlib.sha512()
            File = open(fullpath, 'rb')
            while True:
                buf = File.read(0x100000)
                if not buf:
                    break
                SHA512.update(buf)
            File.close()
            digest = SHA512.hexdigest()
            print("Opening File " + fullpath + " as digest " + digest)
            if not server.bin_GridFS.exists(filename=digest):
                with open(fullpath,'rb') as localfile:
                    oid = server.bin_GridFS.put(localfile,filename=digest, content_type=client_filetype)
                    stored = True
            else:
                stored = True
            print("Creating Messazge")
            #Create a message binary.    
            bin = Envelope.binary(hash=digest)
            #Set the Filesize. Clients can't trust it, but oh-well.
            bin.dict['filesize_hint'] =  client_filesize
            bin.dict['content_type'] = client_filetype
            bin.dict['filename'] = client_filename
            envelopebinarylist.append(bin.dict)
            #Don't keep spare copies on the webservers
            os.remove(fullpath)
             
                        
        e = Envelope()

        if client_regarding is not None:
            print("Adding Regarding - " + client_regarding)
            e.payload.dict['regarding'] = client_regarding

            regardingmsg = server.mongos['default']['envelopes'].find_one({'envelope.payload_sha512':client_regarding},as_class=OrderedDict)
            e.payload.dict['topic'] = regardingmsg['envelope']['payload']['topic']
            e.payload.dict['subject'] = regardingmsg['envelope']['payload']['subject']
        else:
            e.payload.dict['topic'] = client_topic
            e.payload.dict['subject'] = client_subject

        e.payload.dict['formatting'] = "markdown"
        e.payload.dict['class'] = "message"
        e.payload.dict['body'] = client_body
       
        if stored is True:
            e.payload.dict['binaries'] = envelopebinarylist

        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['pubkey'] = self.user.UserSettings['pubkey']
        e.payload.dict['author']['friendlyname'] = self.user.UserSettings['username']
        e.payload.dict['author']['useragent'] = "Pluric Web frontend Pre-release 0.1"
        if self.user.UserSettings['include_location'] == True or 'include_location' in self.request.arguments:
            gi = pygeoip.GeoIP('/usr/local/share/GeoIP/GeoIPCity.dat')
            ip = self.request.remote_ip
            
            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"
                
            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + "," + str(gir['longitude'])
        
        #Sign this bad boy
        usersig = self.user.Keys.signstring(e.payload.text())
        stamp = OrderedDict()
        stamp['class'] = 'author'
        stamp['pubkey'] = self.user.UserSettings['pubkey']
        stamp['signature'] = usersig
        utctime = time.time()
        stamp['time_added'] = int(utctime)
        stamplist = []
        stamplist.append(stamp)
        e.dict['envelope']['stamps'] = stamplist
        
                
        #Send to the server
        newmsgid = server.receiveEnvelope(e.text())
        if newmsgid != False:
            if client_regarding is not None:
                self.redirect('/message/' + server.find_top_parent(newmsgid) + "?jumpto=" + newmsgid, permanent=False)                
            else:
                self.redirect('/message/' + newmsgid, permanent=False)
        else:
            self.write("Failure to insert message.")

class MyPrivateMessagesHandler(BaseHandler):
    def get(self):
        self.getvars()

            
        messages = []
        self.user.load_mongo_by_pubkey(user['pubkey'])
        
        self.write(self.render_string('header.html',title="Welcome to Pluric!",user=self.user,rsshead=None,type=None))
        for message in server.mongos['default']['envelopes'].find({'envelope.payload.to':self.user.Keys.pubkey},fields={'envelope.payload_sha512','envelope.payload.subject'},limit=10,as_class=OrderedDict).sort('value',-1):
            message['envelope']['payload']['subject'] = self.user.Keys.decryptToSelf(message['envelope']['payload']['subject'])
            messages.append(message)

        self.write(self.render_string('showprivatemessages.html',messages=messages))
        self.write(self.render_string('footer.html'))


class NewPrivateMessageHandler(BaseHandler):
    def get(self,urlto=None):
         self.getvars()
         self.write(self.render_string('header.html',title="Login to your account",user=self.user,rsshead=None,type=none))
         self.write(self.render_string('privatemessageform.html',urlto=urlto))
         self.write(self.render_string('footer.html'))

    def post(self,urlto=None):
        self.getvars(ensurekeys=True)


        client_to =  tornado.escape.xhtml_escape(self.get_argument("to"))
        if urlto is not None:
            client_to = tornado.escape.xhtml_escape(urlto)
            
        client_subject =  tornado.escape.xhtml_escape(self.get_argument("subject"))
        client_body =  tornado.escape.xhtml_escape(self.get_argument("body"))
        if "regarding" in self.request.arguments:
            client_regarding = tornado.escape.xhtml_escape(self.get_argument("regarding"))
            if client_regarding == "":
                client_regarding = None
        else:
            client_regarding = None

        #Instantiate the key of the user who we're sending to
        toKey = Keys(pub=client_to)
        toKey.format_keys()


        e = Envelope()
        e.payload.dict['class'] = "privatemessage"
        e.payload.dict['to'] = toKey.pubkey
        e.payload.dict['body'] = toKey.encryptToSelf(client_body)
        e.payload.dict['subject'] = toKey.encryptToSelf(client_subject)
        if client_regarding is not None:
            print("Adding Regarding - " + client_regarding)
            e.payload.dict['regarding'] = client_regarding

        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['pubkey'] = self.user.UserSettings['pubkey']
        e.payload.dict['author']['friendlyname'] = self.user.UserSettings['username']
        e.payload.dict['author']['useragent'] = "Pluric Web frontend Pre-release 0.1"
        if self.user.UserSettings['include_location'] == True or self.get_argument("include_location") == True:
            gi = pygeoip.GeoIP('/usr/local/share/GeoIP/GeoIPCity.dat')
            ip = self.request.remote_ip

            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"

            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + "," + str(gir['longitude'])

        #Sign this bad boy
        usersig = self.user.Keys.signstring(e.payload.text())
        stamp = OrderedDict()
        stamp['class'] = 'author'
        stamp['pubkey'] = self.user.UserSettings['pubkey']
        stamp['signature'] = usersig
        utctime = time.time()
        stamp['time_added'] = int(utctime)
        stamplist = []
        stamplist.append(stamp)
        e.dict['envelope']['stamps'] = stamplist

        #Send to the server
        server.receiveEnvelope(e.text())
    
        
def main():

    tornado.options.parse_command_line()
    # timeout in seconds
    timeout = 10
    socket.setdefaulttimeout(timeout)
    print("Starting Web Frontend for " + server.ServerSettings['hostname'])
    #####TAKE ME OUT IN PRODUCTION!!!!@! #####
    
    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "cookie_secret": "7cxqGjRMzxv7E9Vxq2mnXalZbeUhaoDgnoTSvn0B",
        "login_url": "/login",
        "xsrf_cookies": True,
        "template_path" : "templates",
        "autoescape" : "xhtml_escape"
    }
    application = tornado.web.Application([
        (r"/" ,TriPaneHandler),
        (r"/register" ,RegisterHandler),
        (r"/login" ,LoginHandler),
        (r"/showuserposts/(.*)" ,UserHandler),  
        (r"/user/(.*)" ,UserHandler),  
        (r"/logout" ,LogoutHandler),   
        (r"/newmessage" ,NewmessageHandler),
        (r"/rss/(.*)/(.*)" ,RSSHandler),
        (r"/reply/(.*)/(.*)" ,NewmessageHandler),
        (r"/reply/(.*)" ,NewmessageHandler),
        (r"/uploadnewmessage" ,NewmessageHandler), 
        (r"/vote" ,RatingHandler),
        (r"/usertrust",UserTrustHandler),  
        (r"/usernote",UserNoteHandler),  

        (r"/topicinfo/(.*)",TopicPropertiesHandler),  
        (r"/followuser" ,FollowUserHandler),  
        (r"/followtopic" ,FollowTopicHandler),  
        (r"/nofollowuser" ,NoFollowUserHandler),  
        (r"/nofollowtopic" ,NoFollowTopicHandler),  
        (r"/showprivates" ,MyPrivateMessagesHandler), 
        (r"/uploadprivatemessage/(.*)" ,NewPrivateMessageHandler),
        (r"/uploadprivatemessage" ,NewPrivateMessageHandler),  
        (r"/privatemessage/(.*)" ,PrivateMessageHandler), 
        (r"/sitecontent/(.*)" ,SiteContentHandler),  
        (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": os.path.join(os.path.dirname(__file__),"static/")}),
        (r"/(.*)/(.*)/(.*)" ,TriPaneHandler), 
        (r"/(.*)/(.*)" ,TriPaneHandler),
        (r"/(.*)" ,TriPaneHandler),           
    ], **settings)
    
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8080)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
