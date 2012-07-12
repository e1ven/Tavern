#!/usr/bin/env python3
#
# Copyright 2011 Tavern
    

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
from bs4 import BeautifulSoup
import rss
import Image
import imghdr

import re
try: 
    from hashlib import md5 as md5_func
except ImportError:
    from md5 import new as md5_func


class BaseHandler(tornado.web.RequestHandler):
    
    """
    The BaseHandler is the baseclass for all objects in the webserver.
    It is not expected to ever be instantiated directly.
    It's main uses are:
        * Handle Cookies/logins
        * Allow modules to update just PARTS of the page
    """

    def __init__(self, *args, **kwargs):
        """
        Wrap the default RequestHandler with extra methods
        """    
        #Ensure we have a html variable set.
        self.html = ""
        super(BaseHandler,self).__init__(*args,**kwargs)

        # Add in a random fortune
        self.set_header("X-Fortune", str(server.fortune.random()))
        # Do not allow the content to load in a frame.
        # Should help prevent certain attacks
        self.set_header("X-FRAME-OPTIONS", "DENY")
        # Don't try to guess content-type. 
        # This helps avoid JS sent in an image.
        self.set_header("X-Content-Type-Options","nosniff")
        
    def render_string(self, template_name, **kwargs):
        """
        Overwrite the default render_string to ensure the "server" variable is always available to templates
        """    
        args = dict(
             server=server
        )
        args.update(kwargs)
        return tornado.web.RequestHandler.render_string(self,template_name, **args) 


    def write(self,html):
        if hasattr(html, 'decode'):
            self.html += html.decode('utf-8')
        else:
             self.html += html

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
        
        return ( '''var tavern_replace = function() 
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
                    jQuery('div#''' + element  + ''' a.internal').each( function ()
                    {            
                        jQuery(this).click(function()
                        {   
                            jQuery("#spinner").height(jQuery(this).parent().height());
                            jQuery("#spinner").width(jQuery(this).parent().width());
                            jQuery("#spinner").css("top", jQuery(this).parent().offset().top).css("left", jQuery(this).parent().offset().left).show();
                            head.js(jQuery(this).attr('link-destination') + "?js=yes&timestamp=" + Math.round(new Date().getTime())  );            
                            return false;
                        });
                        jQuery(this).attr("link-destination",this.href);
                    });
                    jQuery('#spinner').hide();
                };
                tavern_replace();
                tavern_replace = null;
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
        signed = self.create_signed_value("tavern_preferences",json.dumps(usersettings))

        # Chunk up the cookie value, so we can spread across multiple cookies.
        numchunks = 0
        for chunk in self.chunks(signed,3000):
            numchunks += 1
            self.set_cookie("tavern_preferences" + str(numchunks),chunk,httponly=True,expires_days=999)
        self.set_secure_cookie("tavern_preferences_count",str(numchunks),httponly=True,expires_days=999)
        print("numchunks + " + str(numchunks))
        print("Setting :::: " + json.dumps(usersettings))

    def getvars(self,ensurekeys=False):
        """
        Retrieve the basic user variables out of your cookies.
        """
        self.user = User()
        if self.get_secure_cookie("tavern_preferences_count") is not None:

            # Restore the signed cookie, across many chunks
            restoredcookie = ""
            for i in range(1,1 + int(self.get_secure_cookie("tavern_preferences_count"))):
                restoredcookie += self.get_cookie("tavern_preferences" + str(i))

            # Validate the cookie, and load if it passes
            decodedcookie = self.get_secure_cookie("tavern_preferences",value=restoredcookie)
            if decodedcookie is not None:
                self.user.load_string(decodedcookie.decode('utf-8'))
            else:
                print("Cookie doesn't validate. Deleting...")
                self.clear_cookie('tavern_preferences')
                self.clear_cookie('tavern_preferences_count')

        # If there isn't already a cookie, make a very basic one.
        # Don't bother doing the keys, since that eats randomness.
        else:
            print("Making cookies")
            self.user.generate(skipkeys=True)
            self.setvars()

        # If we've asked to make the keys.. Generate them.
        # This won't overwrite existing values, since user.generate() is additive.
        if ensurekeys == True:
            validkey = False
            if 'encryptedprivkey' in self.user.UserSettings:
                if self.user.UserSettings['encryptedprivkey'] is not None:
                    validkey = True
            if not validkey:
                print("Making keys with a random password.")

                # Generate a random password with a random number of characters
                numcharacters = 100 + random.randrange(1,100)
                password = server.randstr(numcharacters)
                self.user.generate(skipkeys=False,password=password)

                # Save it out.
                self.setvars()
                self.user.savemongo()
                self.set_secure_cookie('tavern_passkey',self.user.Keys.passkey(password),httponly=True,expires_days=999) 
                self.user.passkey = self.user.Keys.passkey(password)


        if not hasattr(self.user,'passkey'):
            self.user.passkey = self.get_secure_cookie('tavern_passkey')
        if self.user.passkey == None:   
            self.user.passkey = self.get_secure_cookie('tavern_passkey')


        return self.user.UserSettings['username']


class RSSHandler(BaseHandler):
    def get(self,action,param):
        if action =="topic":
            channel = rss.Channel('Tavern - ' + param,
                          'http://Tavern.com/rss/' + param,
                          'Tavern discussion about ' + param,
                          generator = 'Tavern',
                          pubdate = datetime.datetime.now())
            for envelope in server.mongos['default']['envelopes'].find({'envelope.local.sorttopic' : server.sorttopic(param),'envelope.payload.class':'message'},limit=100,as_class=OrderedDict).sort('envelope.local.time_added',pymongo.DESCENDING):
                item = rss.Item(channel,
                    envelope['envelope']['payload']['subject'],
                    "http://Tavern.com/message/" + envelope['envelope']['local']['short_subject'] + "/" + envelope['envelope']['payload_sha512'],
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
                topic = server.sorttopic(param2)
                    
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
            print(server.sorttopic(topic))
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
            
            if topic != 'sitecontent':
                canon="topic/" + topic 
                title=topic
            else:
                canon=""
                title="An anonymous, shared discussion"

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
            # Set the canon URL to be whatever we just got, since obviously we just got it.
            canon=self.request.path[1:]
            subjects = []
            for envelope in server.mongos['default']['envelopes'].find({'envelope.local.sorttopic' : server.sorttopic(topic),'envelope.payload.class':'message','envelope.payload.regarding':{'$exists':False}},limit=self.user.UserSettings['maxposts'],as_class=OrderedDict).sort('envelope.local.time_added',pymongo.DESCENDING):
                subjects.append(envelope)

        usertrust = self.user.gatherTrust(displayenvelope['envelope']['payload']['author']['pubkey'])
        messagerating = self.user.getRatings(messageid)
        displayenvelope = server.formatEnvelope(displayenvelope)
        displayenvelope['envelope']['local']['messagerating'] = messagerating
   
        # Make canon URL safe
        canon=server.urlize(canon) 

        # Detect people accessing via odd URLs
        if self.request.path[1:] != canon:
            print("Redirecting URL " + self.request.path[1:] + " to " + canon )
            self.redirect("/" + canon, permanent=True)
            return

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

            
        self.write(self.render_string('header.html',title="Tavern :: " + envelope['envelope']['payload']['subject'],user=self.user,canon="sitecontent/" + envelope['envelope']['payload_sha512'],rss="/rss/topic/" + envelope['envelope']['payload']['topic'],topic=envelope['envelope']['payload']['topic']))
        self.write(self.render_string('sitecontent.html',formattedbody=envelope['envelope']['local']['formattedbody'],envelope=envelope))
        self.write(self.render_string('footer.html'))
 
class AttachmentHandler(BaseHandler):
    def get(self,attachment):
        self.getvars()
        client_attachment_id = tornado.escape.xhtml_escape(attachment)
        envelopes = server.mongos['default']['envelopes'].find({'envelope.payload.binaries.sha_512' : client_attachment_id},fields={'envelope.payload_sha512':1,'envelope.payload.subject':1},as_class=OrderedDict)
        stack = []
        for envelope in envelopes:
            stack.append(envelope)

        self.write(self.render_string('header.html',title="Tavern Attachment " + client_attachment_id,user=self.user,rsshead=client_attachment_id,type="attachment"))
        self.write(self.render_string('attachments.html',attachment=client_attachment_id,stack=stack))
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

        self.write(self.render_string('header.html',title="Tavern :: " + envelope['envelope']['payload']['subject'],user=self.user,type="privatemessage",rsshead=None))
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
            # Generate the user
            self.user.generate(username=client_newuser.lower(),password=client_newpass)

            if client_email is not None:
                self.user.UserSettings['email'] = client_email.lower()

            self.user.savemongo()

            # Save the passkey out to a separate cookie.
            self.set_secure_cookie("tavern_passkey",self.user.Keys.passkey(client_newpass),httponly=True,expires_days=999) 

            self.setvars()
            self.redirect("/")


class LoginHandler(BaseHandler):
    def get(self):
        self.getvars()  
        pprint.pprint(self.user.UserSettings)      
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
                print("Passkey - " + self.user.Keys.passkey(client_password))
                self.set_secure_cookie("tavern_passkey",self.user.Keys.passkey(client_password),httponly=True,expires_days=999) 
                self.setvars()
                print("Login Successful.")
                self.redirect('/')
            else:
                print("Username/password fail.")
                self.redirect("http://Google.com")

class LogoutHandler(BaseHandler):
     def post(self):
         self.clear_all_cookies()
         self.redirect("/")

class UserHandler(BaseHandler):
    def get(self,pubkey):
        self.getvars()
        
        #Unquote it, then convert it to a TavernKey object so we can rebuild it.
        #Quoting destroys the newlines.
        pubkey = urllib.parse.unquote(pubkey)
        pubkey = Keys(pub=pubkey).pubkey

        self.write(self.render_string('header.html',title="User page",user=self.user,rsshead=None,type=None))

        if pubkey == self.user.Keys.pubkey:
            self.write(self.render_string('mysettings.html',user=self.user))

        self.write(self.render_string('userpage.html',me=self.user,thatguy=pubkey))

        envelopes = []
        for envelope in server.mongos['default']['envelopes'].find({'envelope.payload.author.pubkey':pubkey,'envelope.payload.class':'message'},as_class=OrderedDict).sort('envelope.local.time_added',pymongo.DESCENDING):
            envelopes.append(envelope)

        self.write(self.render_string('showuserposts.html',envelopes=envelopes))
        self.write(self.render_string('footer.html'))


class ChangeManySettingsHandler(BaseHandler):    
    def post(self):    
        self.getvars(ensurekeys=True)

        friendlyname = tornado.escape.xhtml_escape(self.get_argument('friendlyname'))
        maxposts = int(self.get_argument('maxposts'))
        maxreplies = int(self.get_argument('maxreplies'))
        if 'include_location' in self.request.arguments:
            include_location = True
        else:
            include_location = False
        if 'allowembed' in self.request.arguments:
            allowembed = 1
        else:
            allowembed = -1
                     
        self.user.UserSettings['friendlyname'] = friendlyname
        self.user.UserSettings['maxposts'] = maxposts
        self.user.UserSettings['maxreplies'] = maxreplies
        self.user.UserSettings['include_location'] = include_location
        self.user.UserSettings['allowembed'] = allowembed
        self.user.savemongo()
        self.setvars()

        print("set")
        if "js" in self.request.arguments:
            self.finish(divs=['left'])
        else:
            keyurl = ''.join(self.user.Keys.pubkey.split())
            self.redirect('/user/' + keyurl)
                        
                 
class ChangeSingleSettingHandler(BaseHandler):

    def post(self,setting):    
        self.getvars(ensurekeys=True)

        if setting == "followtopic":
            self.user.followTopic(tornado.escape.xhtml_escape(self.get_argument("topic")))
        elif setting == "unfollowtopic":
            self.user.unFollowTopic(tornado.escape.xhtml_escape(self.get_argument("topic")))
        elif setting == "showembeds":
            self.user.UserSettings['allowembed'] = 1
            print("allowing embeds")
        elif setting == "dontshowembeds":
            self.user.UserSettings['allowembed'] = -1
            print("forbidding embeds")
        else:
            print("Warning, you didn't do anything!")      

        self.user.savemongo()
        self.setvars()
        if "js" in self.request.arguments:
            self.finish(divs=['left'])
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
        e.payload.dict['author']['pubkey'] = self.user.Keys.pubkey
        e.payload.dict['author']['friendlyname'] = self.user.UserSettings['friendlyname']
        e.payload.dict['author']['useragent'] = "Tavern Web frontend Pre-release 0.1"
        if self.user.UserSettings['include_location'] == True or 'include_location' in self.request.arguments:
            gi = pygeoip.GeoIP('/usr/local/share/GeoIP/GeoIPCity.dat')
            ip = self.request.remote_ip
            
            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"
                
            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + "," + str(gir['longitude'])
        
        #Sign this bad boy
        usersig = self.user.Keys.signstring(e.payload.text(),self.user.passkey)
        
        stamp = OrderedDict()
        stamp['class'] = 'author'
        stamp['pubkey'] = self.user.Keys.pubkey
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

        trusted_pubkey = urllib.parse.unquote(self.get_argument("trusted_pubkey"))
        trusted_pubkey = Keys(pub=trusted_pubkey).pubkey 


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
        e.payload.dict['trusted_pubkey'] = trusted_pubkey

        #Instantiate the user who's currently logged in


        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['pubkey'] = self.user.Keys.pubkey
        e.payload.dict['author']['friendlyname'] = self.user.UserSettings['friendlyname']
        e.payload.dict['author']['useragent'] = "Tavern Web frontend Pre-release"


        if self.user.UserSettings['include_location'] == True or 'include_location' in self.request.arguments:
            gi = pygeoip.GeoIP('/usr/local/share/GeoIP/GeoIPCity.dat')
            ip = self.request.remote_ip

            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"

            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + "," + str(gir['longitude'])

        #Sign this bad boy
        usersig = self.user.Keys.signstring(e.payload.text(),self.user.passkey)
        
        stamp = OrderedDict()
        stamp['class'] = 'author'
        stamp['pubkey'] = self.user.Keys.pubkey
        stamp['signature'] = usersig
        utctime = time.time()
        stamp['time_added'] = int(utctime)
        stamplist = []
        stamplist.append(stamp)
        e.dict['envelope']['stamps'] = stamplist
        
        
        #Send to the server
        server.receiveEnvelope(e.text())
        print("Trust Submitted.")

        # Remove cached version of this trust.
        server.mongos['cache']['usertrusts'].remove({"asking":self.user.Keys.pubkey,"askingabout":trusted_pubkey})


      
class NewmessageHandler(BaseHandler):
    def get(self,topic=None,regarding=None):
         self.getvars()
         self.write(self.render_string('header.html',title="Post a new message",user=self.user,rsshead=None,type=None))
         self.write(self.render_string('newmessageform.html',regarding=regarding,topic=topic,args=self.request.arguments,user=self.user))
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

        if 'attached_file1.sha512' in self.request.arguments:
            SHA512_precalced = False
        else:
            SHA512_precalced = True

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


            if SHA512_precalced = False:
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
            else:
                digest = tornado.escape.xhtml_escape(self.get_argument(attached_file + ".sha512"))

            print("Opening File " + fullpath + " as digest " + digest)
            if not server.bin_GridFS.exists(filename=digest):
                with open(fullpath,'rb') as localfile:
                    # If it's an image, strip EXIF data.
                    # Do so here, rather than in server, so that server->server messages aren't touched
                    imagetype = imghdr.what('ignoreme',h=localfile.read())
                    acceptable_images = ['gif','jpeg','jpg','png','bmp']
                    if imagetype in acceptable_images:
                        Image.open(fullpath).save(fullpath,format=imagetype)
                    localfile.seek(0)

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
        e.payload.dict['author']['pubkey'] = self.user.Keys.pubkey
        e.payload.dict['author']['friendlyname'] = self.user.UserSettings['friendlyname']
        e.payload.dict['author']['useragent'] = "Tavern Web frontend Pre-release 0.1"
        if self.user.UserSettings['include_location'] == True or 'include_location' in self.request.arguments:
            gi = pygeoip.GeoIP('/usr/local/share/GeoIP/GeoIPCity.dat')
            ip = self.request.remote_ip
            
            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"
                
            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + "," + str(gir['longitude'])
        
        #Sign this bad boy
        usersig = self.user.Keys.signstring(e.payload.text(),self.user.passkey)
        stamp = OrderedDict()
        stamp['class'] = 'author'
        stamp['pubkey'] = self.user.Keys.pubkey
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
        self.user.load_mongo_by_username(self.user['username'])
        
        self.write(self.render_string('header.html',title="Welcome to the Tavern!",user=self.user,rsshead=None,type=None))
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
        e.payload.dict['author']['pubkey'] = self.user.Keys.pubkey
        e.payload.dict['author']['friendlyname'] = self.user.UserSettings['friendlyname']
        e.payload.dict['author']['useragent'] = "Tavern Web frontend Pre-release 0.1"
        if self.user.UserSettings['include_location'] == True or self.get_argument("include_location") == True:
            gi = pygeoip.GeoIP('/usr/local/share/GeoIP/GeoIPCity.dat')
            ip = self.request.remote_ip

            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"

            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + "," + str(gir['longitude'])

        #Sign this bad boy
        usersig = self.user.Keys.signstring(e.payload.text(),self.user.passkey)
        stamp = OrderedDict()
        stamp['class'] = 'author'
        stamp['pubkey'] = self.user.Keys.pubkey
        stamp['signature'] = usersig
        utctime = time.time()
        stamp['time_added'] = int(utctime)
        stamplist = []
        stamplist.append(stamp)
        e.dict['envelope']['stamps'] = stamplist

        #Send to the server
        server.receiveEnvelope(e.text())
    
class NullHandler(BaseHandler):
        # This is grabbed by nginx, and never called in prod.
    def get(self,url=None):
        return 
    def post(self,url=None):
        return

class AvatarHandler(BaseHandler):
    """
    For users who aren't using nginx (like in dev), this will pull in the avatars
    """
    def get(self,avatar):
        print("Bouncing to offsite avatar. Install the NGINX package to avoid this! ")
        self.redirect('https://robohash.org/' + avatar + "?" + "set="  + self.get_argument('set') + "&bgset=" + self.get_argument('bgset') + "&size=" + self.get_argument('size') )
        
def main():

    tornado.options.parse_command_line()
    # timeout in seconds
    timeout = 10
    socket.setdefaulttimeout(timeout)
    print("Starting Web Frontend for " + server.ServerSettings['hostname'])
    

    # Generate a default user, to use when no one is logged in.
    # This can't be done in the Server module, because it requires User, which requires Server, which can't then require User....
    if not 'guestacct' in server.ServerSettings:
        serveruser = User()
        serveruser.generate(skipkeys=False,password=server.ServerSettings['serverkey-password'])
        server.ServerSettings['guestacct'] = serveruser.UserSettings
        server.saveconfig()


    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "cookie_secret": server.ServerSettings['cookie-encryption'],
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
        (r"/attachment/(.*)" ,AttachmentHandler), 
        (r"/topicinfo/(.*)",TopicPropertiesHandler),  
        (r"/changesetting/(.*)" ,ChangeSingleSettingHandler),
        (r"/changesettings" ,ChangeManySettingsHandler),  
        (r"/showprivates" ,MyPrivateMessagesHandler), 
        (r"/uploadprivatemessage/(.*)" ,NewPrivateMessageHandler),
        (r"/uploadprivatemessage" ,NewPrivateMessageHandler),  
        (r"/privatemessage/(.*)" ,PrivateMessageHandler), 
        (r"/sitecontent/(.*)" ,SiteContentHandler),  
        (r"/avatar/(.*)" ,AvatarHandler),           
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
