#!/usr/bin/env python
#
# Copyright 2011 Pluric
    

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.escape
import bcrypt
import time
import datetime
import os
import random
import socket
import pymongo
import json
from Envelope import Envelope
from collections import OrderedDict
import pymongo
from tornado.options import define, options
from server import server
import GeoIP
import pprint
from keys import *
from User import User
from gridfs import GridFS
import hashlib
import urllib
#import TopicList
import urllib
from BeautifulSoup import BeautifulSoup

import re
try: 
    from hashlib import md5 as md5_func
except ImportError:
    from md5 import new as md5_func
import NofollowExtension


define("port", default=8080, help="run on the given port", type=int)


class BaseHandler(tornado.web.RequestHandler):

    def __init__(self, *args, **kwargs):
        #Ensure we have a html variable set.
        self.html = ""
        super(BaseHandler,self).__init__(*args,**kwargs)
        
    def write(self,html):
        self.html = self.html + html

    def gettext(self):
        ptext = ""
        for a in self.pagetext:
            ptext = ptext + a
        self.write(ptext)
        

    def finish(self,div='limits',div2=None,message=None):
        if "js" in self.request.arguments:
            #if JS is set at all, send the JS script version.
            super(BaseHandler, self).write(self.getjs(div))
            if div2 is not None:
                super(BaseHandler, self).write(self.getjs(div2))
        elif "getonly" in self.request.arguments:
            #Get ONLY the div content marked
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
        #Get the element text, remove all linebreaks, and escape it up.
        #Then, send that as a document replacement
        #Also, rewrite the document history in the browser, so the URL looks normal.
        
        jsvar = self.request.uri.find("js=")
        if jsvar > -1:
            #This should always be true    
            #But Are there other params?
            nextvar = self.request.uri.find("&",jsvar)
            if nextvar > 0:
                #There are Additional Variables in this URL
                finish = self.request.uri[nextvar:len(self.request.uri)]
            else:
                print "No Next variables"
                #There are no other variables. Delete until End of string
                finish = ""
                
            modifiedurl = self.request.uri[0:self.request.uri.find("js=") -1] + finish
            
        soup = BeautifulSoup(self.html)
        soupyelement = soup.find(id=element)
        soupytxt = ""
        if soupyelement is not None:
            for child in soupyelement.contents:
                soupytxt += str(child)

        escapedtext = soupytxt.replace("\"","\\\"")
        escapedtext = escapedtext.replace("\n","")
        
        print "----------- " + escapedtext + "---------"
        return ( '''var pluric_replace = function() 
                {
                    var stateObj = {
	    		        title: document.title,
	    		        url: window.location.pathname 
	    	    };
                    window.history.pushState(stateObj, "","''' + modifiedurl + '''");
                    document.getElementById("''' + element + '''").innerHTML="''' + escapedtext + '''";
                    $('div#''' + element  + ''' a.internal').each( function ()
                    {            
                        $(this).click(function()
                        {   
                            $("#spinner").height($(this).parent().height());
                            $("#spinner").width($(this).parent().width());
                            $("#spinner").css("top", $(this).parent().offset().top).css("left", $(this).parent().offset().left).show();
                            include_dom($(this).attr('link-destination') + "?js=yes");
                            return false;
                        });
                        $(this).attr("link-destination",this.href);
                    });
                    $('#spinner').hide();
                };
                pluric_replace();
                pluric_replace = null;
                ''')

    def getvars(self):
        self.username = self.get_secure_cookie("username")
        if self.username is None:
            self.username = "Guest"
            self.loggedin = False
        else:
            self.loggedin = True
        self.maxposts = self.get_secure_cookie("maxposts")
        if self.maxposts is None:
            self.maxposts = 20
        else:
            self.maxposts = int(self.maxposts)
        if self.maxposts is None:
            self.maxposts = 20
        else:
            self.maxposts = int(self.maxposts)
        
        self.pubkey = self.get_secure_cookie("pubkey")
        #Toggle this.
        self.include_loc = "on"  
           
        return str(self.username)
           
    


class FancyPantsTemplate(BaseHandler):
    def write(self,text):
        if callback is not None:
            self.write("var mydiv = document.getElementById('" + tornado.escape.xhtml_escape(addto) + "'); mydiv.appendChild(document.createTextNode('" + tornado.escape.xhtml_escape(callback) + "'));")
        if addto is None:
            return
        else:
            self.write(text)



class NotFoundHandler(BaseHandler):
    def get(self,whatever):
        self.getvars()
        self.write(self.render_string('header.html',title="Page not Found",username=self.username,loggedin=self.loggedin,pubkey=self.pubkey))
        self.write(self.render_string('404.html'))
        self.write(self.render_string('footer.html'))


class FrontPageHandler(BaseHandler):        
    def get(self):
        self.getvars()
        toptopics = []
        self.write(self.render_string('header.html',title="Welcome to Pluric!",username=self.username,loggedin=self.loggedin,pubkey=self.pubkey))

        for topic in server.mongos['default']['topiclist'].find(limit=10,as_class=OrderedDict).sort('value',-1):
            toptopics.append(topic)
            
        self.write(self.render_string('frontpage.html',toptopics=toptopics))
        self.write(self.render_string('footer.html'))
        self.finish("content")

class TopicHandler(BaseHandler):        
    def get(self,topic):
        self.getvars()
        client_topic = tornado.escape.xhtml_escape(topic)
        envelopes = []
        self.write(self.render_string('header.html',title="Pluric :: " + client_topic,username=self.username,loggedin=self.loggedin,pubkey=self.pubkey,canon="topictag/" + client_topic))
       
        for envelope in server.mongos['default']['envelopes'].find({'envelope.payload.topictag' : client_topic },limit=self.maxposts,as_class=OrderedDict):
                envelopes.append(envelope)
        self.write(self.render_string('messages-in-topic.html',envelopes=envelopes))
        self.write(self.render_string('footer.html'))


class TriPaneHandler(BaseHandler): 
    #The TriPane Handler is the beefiest handler in the project.
    #It renders the main tri-panel interface, and only pushes out the parts that are needed.
                
    def get(self,action=None,param=None,bulshit=None):
        self.getvars()
        
        #TODO KILL THIS!!
        #THIS WILL WASTE CPU
        #tl = TopicList.TopicList()        
        
        toptopics = []
        for topic in server.mongos['default']['topiclist'].find(limit=10,as_class=OrderedDict).sort('value',-1):
            toptopics.append(topic)
        canon = None
        #Assign Default Values     
        client_message_id = None
        client_topic = None
        displayenvelope = None
        if action is not None:
            client_action = tornado.escape.xhtml_escape(action)
        else:
            #If we don't submit an action, aka, just the base page, go to the topic 'sitecontent'
            client_action = "topic"
            param="sitecontent"
                
                
        print "action = " + client_action    
        subjects = []   
        if client_action == "topic":
            client_topic = tornado.escape.xhtml_escape(param)
            for envelope in server.mongos['default']['envelopes'].find({'envelope.payload.topictag' : client_topic,'envelope.payload.regarding':{'$exists':False}},limit=self.maxposts,as_class=OrderedDict):
                subjects.append(envelope)
            displayenvelope = subjects[0]  
            canon="topictag/" + client_topic 
            
        if client_action == "message":
            client_message_id = tornado.escape.xhtml_escape(param)
            displayenvelope = server.mongos['default']['envelopes'].find_one({'envelope.payload_sha512' : client_message_id },as_class=OrderedDict)
            client_topic = displayenvelope['envelope']['payload']   ['topictag'][0]
            for envelope in server.mongos['default']['envelopes'].find({'envelope.payload.topictag' : client_topic,'envelope.payload.regarding':{'$exists':False}},limit=self.maxposts,as_class=OrderedDict):
                subjects.append(envelope)
            canon="message/" + displayenvelope['envelope']['payload_sha512'] + "/" + displayenvelope['envelope']['local']['short-title']

            
            
        if displayenvelope is None:     
            displayenvelope = server.mongos['default']['envelopes'].find_one({'envelope.payload_sha512' : client_message_id },as_class=OrderedDict)


        u = User()
        u.load_mongo_by_username(username=self.username)
        usertrust = u.gatherTrust(displayenvelope['envelope']['payload']['author']['pubkey'])
        messagerating = u.getRatings(client_message_id)
        displayenvelope = server.formatEnvelope(displayenvelope)
        displayenvelope['envelope']['local']['messagerating'] = messagerating
    

        #Gather up all the replies to this message, so we can send those to the template as well
        self.write(self.render_string('header.html',title="Pluric Front Page",username=self.username,loggedin=self.loggedin,pubkey=self.pubkey,canon=canon))
        self.write(self.render_string('tripane.html',toptopics=toptopics,subjects=subjects,envelope=displayenvelope))
        self.write(self.render_string('footer.html'))  
           
        if client_action == "message":
            print "only update right"
            self.finish("right")
        elif client_action == "topic":
            self.finish(div="center",div2="right")
        else:
            self.finish()
      
       
class MessageHandler(BaseHandler):        
    def get(self,message):
        self.getvars()
        client_message_id = tornado.escape.xhtml_escape(message)
        
        envelope = server.mongos['default']['envelopes'].find_one({'envelope.payload_sha512' : client_message_id },as_class=OrderedDict)

        u = User()
        u.load_mongo_by_username(username=self.username)
        usertrust = u.gatherTrust(envelope['envelope']['payload']['author']['pubkey'])

        messagerating = u.getRatings(client_message_id)
        envelope = server.formatEnvelope(envelope)

            
        self.write(self.render_string('header.html',title="Pluric :: " + envelope['envelope']['payload']['subject'],username=self.username,pubkey=self.pubkey,loggedin=self.loggedin,canon="message/" + envelope['envelope']['payload_sha512']))
        self.write(self.render_string('single-message.html',formattedbody=envelope['envelope']['local']['formattedbody'],messagerating=messagerating,usertrust=usertrust,displayableAttachmentList=envelope['envelope']['local']['displayableattachmentlist'],envelope=envelope))
        self.write(self.render_string('footer.html'))
        self.finish("right")

class SiteContentHandler(BaseHandler):        
    def get(self,message):
        self.getvars()
        client_message_id = tornado.escape.xhtml_escape(message)
        
        envelope = server.mongos['default']['envelopes'].find_one({'envelope.payload_sha512' : client_message_id },as_class=OrderedDict)

        envelope = server.formatEnvelope(envelope)

            
        self.write(self.render_string('header.html',title="Pluric :: " + envelope['envelope']['payload']['subject'],username=self.username,pubkey=self.pubkey,loggedin=self.loggedin,canon="sitecontent/" + envelope['envelope']['payload_sha512']))
        self.write(self.render_string('sitecontent.html',formattedbody=envelope['envelope']['local']['formattedbody'],displayableAttachmentList=envelope['envelope']['local']['displayableattachmentlist'],envelope=envelope))
        self.write(self.render_string('footer.html'))
        
        

class PrivateMessageHandler(BaseHandler):        
    def get(self,message):
        self.getvars()
        client_message_id = tornado.escape.xhtml_escape(message)

        envelope = server.mongos['default']['envelopes'].find_one({'envelope.payload_sha512' : client_message_id },as_class=OrderedDict)

        u = User()
        u.load_mongo_by_username(username=self.username)
        usertrust = u.gatherTrust(envelope['envelope']['payload']['author']['pubkey'])
        
        envelope['envelope']['payload']['body'] = u.Keys.decryptToSelf(envelope['envelope']['payload']['body'])
        envelope['envelope']['payload']['subject'] = u.Keys.decryptToSelf(envelope['envelope']['payload']['subject'])

        if envelope['envelope']['payload'].has_key('formatting'):
                formattedbody = server.formatText(text=envelope['envelope']['payload']['body'],formatting=envelope['envelope']['payload']['formatting'])
        else:    
                formattedbody = server.formatText(text=envelope['envelope']['payload']['body'])

        self.write(self.render_string('header.html',title="Pluric :: " + envelope['envelope']['payload']['subject'],username=self.username,loggedin=self.loggedin,pubkey=self.pubkey))
        self.write(self.render_string('singleprivatemessage.html',formattedbody=formattedbody,usertrust=usertrust,envelope=envelope))
        self.write(self.render_string('footer.html'))




class RegisterHandler(BaseHandler):
    def get(self):
        self.getvars()
        self.write(self.render_string('header.html',title="Register for an Account",username=self.username,loggedin=self.loggedin,pubkey=self.pubkey))
        self.write(self.render_string('registerform.html'))
        self.write(self.render_string('footer.html'))
    def post(self):
        self.getvars()
        self.write(self.render_string('header.html',title='Register for an account',username="",loggedin=False,pubkey=self.pubkey))

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
            hashedpass = bcrypt.hashpw(client_newpass, bcrypt.gensalt(12))
            u = User()
            u.generate(hashedpass=hashedpass,username=client_newuser.lower())
            if client_email is not None:
                u.UserSettings['email'] = client_email.lower()
            
            u.UserSettings['maxposts'] = 20
            u.savemongo()
            
            self.set_secure_cookie("username",client_newuser.lower(),httponly=True)
            self.set_secure_cookie("maxposts",str(u.UserSettings['maxposts']),httponly=True)
            
            self.redirect("/")


class LoginHandler(BaseHandler):
    def get(self):
        self.getvars()        
        self.write(self.render_string('header.html',title="Login to your account",username=self.username,loggedin=self.loggedin,pubkey=self.pubkey))
        self.write(self.render_string('loginform.html'))
        self.write(self.render_string('footer.html'))
    def post(self):
        self.getvars()
        self.write(self.render_string('header.html',loggedin=False,title='Login to your account',username="",pubkey=self.pubkey))

        client_username =  tornado.escape.xhtml_escape(self.get_argument("username"))
        client_password =  tornado.escape.xhtml_escape(self.get_argument("pass"))

        user = server.mongos['default']['users'].find_one({"username":client_username.lower()},as_class=OrderedDict)
        if user is not None:
            u = User()
            u.load_mongo_by_username(username=client_username.lower())
            if bcrypt.hashpw(client_password,user['hashedpass']) == user['hashedpass']:
                self.set_secure_cookie("username",user['username'].lower(),httponly=True)
                self.set_secure_cookie("maxposts",str(u.UserSettings['maxposts']),httponly=True)
                self.set_secure_cookie("pubkey",str(''.join(u.UserSettings['pubkey'].split() ) ),httponly=True)
                print str(''.join(u.UserSettings['pubkey'].split() ) )
                self.redirect("/")
                return

        self.write("I'm sorry, we don't have that username/password combo on file.")

class LogoutHandler(BaseHandler):
     def post(self):
         self.clear_cookie("username")
         self.redirect("/")

class ShowUserPosts(BaseHandler):
    def get(self,pubkey):
        self.getvars()
        
        #Unquote it, then convert it to a PluricKey object so we can rebuild it.
        #Quoting destroys the newlines.
        pubkey = urllib.unquote(pubkey)
        k = Keys(pub=pubkey)
        k.formatkeys()
        pubkey = k.pubkey
        
        print "---???---"
        print pubkey
        print "---XXX---"

        messages = []
        self.write(self.render_string('header.html',title="Welcome to Pluric!",username=self.username,loggedin=self.loggedin,pubkey=self.pubkey))
        for message in server.mongos['default']['envelopes'].find({'envelope.payload.author.pubkey':pubkey},fields={'envelope.payload_sha512','envelope.payload.topictag','envelope.payload.subject'},limit=10,as_class=OrderedDict).sort('value',-1):
            messages.append(message)

        self.write(self.render_string('showuserposts.html',messages=messages))
        self.write(self.render_string('footer.html'))
                 
                 
class FollowUserHandler(BaseHandler):
    def get(self,pubkey):
        self.getvars()
        #Calculate the votes for that post. 

    def post(self):    
        self.getvars()
        if not self.loggedin:
            self.write("You must be logged in to follow a user.")
            return 0
        u = User()
        u.load_mongo_by_username(username=self.username)
        u.followUser(pubkey)
        u.savemongo()
        
class NoFollowUserHandler(BaseHandler):
    def get(self,topictag):
        self.getvars()
     #Calculate the votes for that post. 

    def post(self):    
        self.getvars()
        if not self.loggedin:
            self.write("You must be logged in to follow a topic.")
            return 0
        u = User()
        u.load_mongo_by_username(username=self.username)
        u.noFollowUser(topictag)
        u.savemongo()


class FollowTopicHandler(BaseHandler):
    def get(self,pubkey):
        self.getvars()

    def post(self):    
        self.getvars()
        if not self.loggedin:
            self.write("You must be logged in to follow a user.")
            return 0
        u = User()
        u.load_mongo_by_username(username=self.username)
        u.followTopic(pubkey)
        u.savemongo()

class NoFollowTopicHandler(BaseHandler):
    def get(self,topictag):
        self.getvars()
        
    def post(self):       
        self.getvars()
        if not self.loggedin:
            self.write("You must be logged in to follow a topic.")
            return 0
        u = User()
        u.load_mongo_by_username(username=self.username)
        u.noFollowTopic(topictag)
        u.savemongo()
    
            
            
        

class RatingHandler(BaseHandler):
    def get(self,posthash):
        self.getvars()
        #Calculate the votes for that post. 
         
    def post(self):    
        self.getvars()

        #So you may be asking yourself.. Self, why did we do this as a POST, rather than
        #Just a GET value, of the form server.com/msg123/voteup
        #The answer is xsrf protection.
        #We don't want people to link to the upvote button and trick you into voting up.

        if not self.loggedin:
            self.write("You must be logged in to rate a message.")
            return
        
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
        user = server.mongos['default']['users'].find_one({"username":self.username},as_class=OrderedDict)        
        u = User()
        u.load_mongo_by_pubkey(user['pubkey'])
        
        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['pubkey'] = u.UserSettings['pubkey']
        e.payload.dict['author']['friendlyname'] = u.UserSettings['username']
        e.payload.dict['author']['useragent'] = "Pluric Web frontend Pre-release 0.1"
        if self.include_loc == "on":
            gi = GeoIP.open("/usr/local/share/GeoIP/GeoIPCity.dat",GeoIP.GEOIP_STANDARD)
            ip = self.request.remote_ip
            
            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"
                
            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + "," + str(gir['longitude'])
        
        #Sign this bad boy
        usersig = u.Keys.signstring(e.payload.text())
        
        stamp = OrderedDict()
        stamp['class'] = 'author'
        stamp['pubkey'] = u.UserSettings['pubkey']
        stamp['signature'] = usersig
        utctime = time.time()
        stamp['time_added'] = int(utctime)
        stamplist = []
        stamplist.append(stamp)
        e.dict['envelope']['stamps'] = stamplist
        
        #Send to the server
        server.receiveEnvelope(e.text())
        
        self.write("Your vote has been recorded. Thanks!")

class UserTrustHandler(BaseHandler):
    def get(self,user):
        self.getvars()
        #Calculate the trust for a user. 

    def post(self):    
        self.getvars()
        if not self.loggedin:
            self.write("You must be logged in to trust or distrust a user.")
            return

        client_pubkey =  self.get_argument("pubkey")    
        client_trust =  tornado.escape.xhtml_escape(self.get_argument("trust"))
        trust_val = int(client_trust)
        if trust_val not in [-100,0,100]:
            self.write("Invalid Trust Score.")
            return -1

        e = Envelope()
        e.payload.dict['class'] = "usertrust"
        e.payload.dict['trust'] = trust_val
                
        k = Keys(pub=client_pubkey)
        e.payload.dict['pubkey'] = k.pubkey

        #Instantiate the user who's currently logged in
        user = server.mongos['default']['users'].find_one({"username":self.username},as_class=OrderedDict)        
        u = User()
        u.load_mongo_by_pubkey(user['pubkey'])

        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['pubkey'] = u.UserSettings['pubkey']
        e.payload.dict['author']['friendlyname'] = u.UserSettings['username']

        e.payload.dict['author']['useragent'] = "Pluric Web frontend Pre-release 0.1"
        if self.include_loc == "on":
            gi = GeoIP.open("/usr/local/share/GeoIP/GeoIPCity.dat",GeoIP.GEOIP_STANDARD)
            ip = self.request.remote_ip

            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"

            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + "," + str(gir['longitude'])

        #Sign this bad boy
        usersig = u.Keys.signstring(e.payload.text())
        
        stamp = OrderedDict()
        stamp['class'] = 'author'
        stamp['pubkey'] = u.UserSettings['pubkey']
        stamp['signature'] = usersig
        utctime = time.time()
        stamp['time_added'] = int(utctime)
        stamplist = []
        stamplist.append(stamp)
        e.dict['envelope']['stamps'] = stamplist
        
        
        #Send to the server
        server.receiveEnvelope(e.text())



      
class NewmessageHandler(BaseHandler):
    def get(self,regarding="",topic=None):
         self.getvars()
         self.write(self.render_string('header.html',title="Login to your account",username=self.username,loggedin=self.loggedin,pubkey=self.pubkey))
         self.write(self.render_string('newmessageform.html',regarding=regarding,topic=topic))
         self.write(self.render_string('footer.html'))
         self.finish('content')

    def post(self):
        self.getvars()
        if not self.loggedin:
            self.write("You must be logged in to do this.")
            return
        
        # self.write(self.render_string('header.html',title='Post a new message',username=self.username))

        client_topic =  tornado.escape.xhtml_escape(self.get_argument("topic"))
        client_subject =  tornado.escape.xhtml_escape(self.get_argument("subject"))
        client_body =  tornado.escape.xhtml_escape(self.get_argument("body"))
        self.include_loc = tornado.escape.xhtml_escape(self.get_argument("include_location"))
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
        filelist = dict(map(lambda i: (i,1),filelist)).keys()
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
           
            print "Trying client_filepath" 
            fs_basename = os.path.basename(client_filepath)
            fullpath = server.ServerSettings['upload-dir'] + "/" + fs_basename
       
            #Hash the file in chunks
            sha512 = hashlib.sha512()
            with open(fullpath,'rb') as f: 
                for chunk in iter(lambda: f.read(128 * sha512.block_size), ''): 
                     sha512.update(chunk)
            digest =  sha512.hexdigest()
            
            if not server.bin_GridFS.exists(filename=digest):
                with open(fullpath) as localfile:
                    
                    oid = server.bin_GridFS.put(localfile,filename=digest, content_type=client_filetype)
                    stored = True
            else:
                stored = True
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
        topics = []
        topics.append(client_topic)        
        e.payload.dict['formatting'] = "markdown"
        e.payload.dict['class'] = "message"
        e.payload.dict['topictag'] = topics
        e.payload.dict['body'] = client_body
        e.payload.dict['subject'] = client_subject
        if client_regarding is not None:
            print "Adding Regarding - " + client_regarding
            e.payload.dict['regarding'] = client_regarding
            
        #Instantiate the user who's currently logged in
        user = server.mongos['default']['users'].find_one({"username":self.username},as_class=OrderedDict)        
        u = User()
        u.load_mongo_by_pubkey(user['pubkey'])
        
        if stored is True:
            e.payload.dict['binaries'] = envelopebinarylist

        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['pubkey'] = u.UserSettings['pubkey']
        e.payload.dict['author']['friendlyname'] = u.UserSettings['username']
        e.payload.dict['author']['useragent'] = "Pluric Web frontend Pre-release 0.1"
        if self.include_loc == "on":
            gi = GeoIP.open("/usr/local/share/GeoIP/GeoIPCity.dat",GeoIP.GEOIP_STANDARD)
            ip = self.request.remote_ip
            
            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"
                
            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + "," + str(gir['longitude'])
        
        #Sign this bad boy
        usersig = u.Keys.signstring(e.payload.text())
        stamp = OrderedDict()
        stamp['class'] = 'author'
        stamp['pubkey'] = u.UserSettings['pubkey']
        stamp['signature'] = usersig
        utctime = time.time()
        stamp['time_added'] = int(utctime)
        stamplist = []
        stamplist.append(stamp)
        e.dict['envelope']['stamps'] = stamplist
        
                
        #Send to the server
        newmsgid = server.receiveEnvelope(e.text())
        self.redirect('/message/' + newmsgid, permanent=False)

class MyPrivateMessagesHandler(BaseHandler):
    def get(self):
        self.getvars()
        if not self.loggedin:
            self.write("You must be logged in to do this.")
            return
            
        messages = []
        user = server.mongos['default']['users'].find_one({"username":self.username},as_class=OrderedDict)        
        u = User()
        u.load_mongo_by_pubkey(user['pubkey'])
        
        self.write(self.render_string('header.html',title="Welcome to Pluric!",username=self.username,loggedin=self.loggedin,pubkey=self.pubkey))
        for message in server.mongos['default']['envelopes'].find({'envelope.payload.to':u.Keys.pubkey},fields={'envelope.payload_sha512','envelope.payload.subject'},limit=10,as_class=OrderedDict).sort('value',-1):
            message['envelope']['payload']['subject'] = u.Keys.decryptToSelf(message['envelope']['payload']['subject'])
            messages.append(message)

        self.write(self.render_string('showprivatemessages.html',messages=messages))
        self.write(self.render_string('footer.html'))


class NewPrivateMessageHandler(BaseHandler):
    def get(self,urlto=None):
         self.getvars()
         self.write(self.render_string('header.html',title="Login to your account",username=self.username,loggedin=self.loggedin,pubkey=self.pubkey))
         self.write(self.render_string('privatemessageform.html',urlto=urlto))
         self.write(self.render_string('footer.html'))

    def post(self,urlto=None):
        self.getvars()
        if not self.loggedin:
            self.write("You must be logged in to do this.")
            return

        client_to =  tornado.escape.xhtml_escape(self.get_argument("to"))
        if urlto is not None:
            client_to = tornado.escape.xhtml_escape(urlto)
            
        client_subject =  tornado.escape.xhtml_escape(self.get_argument("subject"))
        client_body =  tornado.escape.xhtml_escape(self.get_argument("body"))
        self.include_loc = tornado.escape.xhtml_escape(self.get_argument("include_location"))
        if "regarding" in self.request.arguments:
            client_regarding = tornado.escape.xhtml_escape(self.get_argument("regarding"))
            if client_regarding == "":
                client_regarding = None
        else:
            client_regarding = None

        #Instantiate the user who's currently logged in
        user = server.mongos['default']['users'].find_one({"username":self.username},as_class=OrderedDict)        
        u = User()
        u.load_mongo_by_pubkey(user['pubkey'])
        
        #Instantiate the key of the user who we're sending to
        toKey = Keys(pub=client_to)
        toKey.formatkeys()


        e = Envelope()
        topics = []
        e.payload.dict['class'] = "privatemessage"
        e.payload.dict['to'] = toKey.pubkey
        e.payload.dict['body'] = toKey.encryptToSelf(client_body)
        e.payload.dict['subject'] = toKey.encryptToSelf(client_subject)
        if client_regarding is not None:
            print "Adding Regarding - " + client_regarding
            e.payload.dict['regarding'] = client_regarding

        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['pubkey'] = u.UserSettings['pubkey']
        e.payload.dict['author']['friendlyname'] = u.UserSettings['username']
        e.payload.dict['author']['useragent'] = "Pluric Web frontend Pre-release 0.1"
        if self.include_loc == "on":
            gi = GeoIP.open("/usr/local/share/GeoIP/GeoIPCity.dat",GeoIP.GEOIP_STANDARD)
            ip = self.request.remote_ip

            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"

            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + "," + str(gir['longitude'])

        #Sign this bad boy
        usersig = u.Keys.signstring(e.payload.text())
        stamp = OrderedDict()
        stamp['class'] = 'author'
        stamp['pubkey'] = u.UserSettings['pubkey']
        stamp['signature'] = usersig
        utctime = time.time()
        stamp['time_added'] = int(utctime)
        stamplist = []
        stamplist.append(stamp)
        e.dict['envelope']['stamps'] = stamplist

        #Send to the server
        server.receiveEnvelope(e.text())



class TodoHandler(BaseHandler):
    def get(self):
        #TODO: Stuff
        self.getvars()


      
        
def main():

    tornado.options.parse_command_line()
    # timeout in seconds
    timeout = 10
    socket.setdefaulttimeout(timeout)
    print "Starting Web Frontend for " + server.ServerSettings['hostname']
    #####TAKE ME OUT IN PRODUCTION!!!!@! #####
    
    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "cookie_secret": "7cxqGjRMzxv7E9Vxq2mnXalZbeUhaoDgnoTSvn0B",
        "login_url": "/login",
        "xsrf_cookies": True,
        "template_path" : "templates",
    }
    application = tornado.web.Application([
        (r"/" ,TriPaneHandler),
        (r"/user/(.*)" ,TodoHandler),  
        (r"/register" ,RegisterHandler),
        (r"/login" ,LoginHandler),
        (r"/logout" ,LogoutHandler), 
        (r"/newmessage" ,NewmessageHandler),
        (r"/reply/(.*)/(.*)" ,NewmessageHandler),
        (r"/uploadnewmessage" ,NewmessageHandler), 
        (r"/vote" ,RatingHandler),
        (r"/usertrust",UserTrustHandler),  
        (r"/followuser/(.*)" ,FollowUserHandler),  
        (r"/followtopic/(.*)" ,FollowTopicHandler),  
        (r"/showuserposts/(.*)" ,ShowUserPosts),  
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
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
