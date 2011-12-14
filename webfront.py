#!/usr/bin/env python3
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
        self.html = self.html + str(html,encoding='utf8')

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
                    var stateObj = {
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
                
                $(".vote").submit(function(event) {
                    voteref = $(this);
                    /* stop form from submitting normally */
                    event.preventDefault(); 

                    /* get some values from elements on the page: */
                    var $form = $( this ),
                        rating = $form.find( 'input[name="rating"]' ).val(),
                        url = $form.attr( 'action' );

                    /* Send the data using post and put the results in a div */
                    $.post( url, { 'rating': $form.find( 'input[name="rating"]' ).val(),
                                   '_xsrf' : $form.find( 'input[name="_xsrf"]' ).val(), 
                                   'hash' : $form.find( 'input[name="hash"]' ).val() },
                      function( data ) {
                          voteref.parent().empty().append( data );
                      }
                    );
                });
                $(".reply").click(function(event) {
                    event.preventDefault();
                    var $msg = $(this).attr('message');
                    var $href = $(this).attr('href');
                    $.get($href + "?getonly=true",function(data) {
                      $('#reply_'+$msg).empty().append("<br>" + data);
                    });   

                });
                
                
                ''')

    def getvars(self):
        """
        Retrieve the basic user variables out of your cookies.
        """
        self.username = self.get_secure_cookie("username")
        if self.username is None:
            self.username = "Guest"
            self.loggedin = False
        else:
            self.username = self.username.decode('utf-8')
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
        if self.pubkey is not None:
            self.pubkey = self.pubkey.decode('utf-8')
        #Toggle this.
        self.include_loc = "on"  
           
        return str(self.username)
           
    def forceregister(self):
        """
        Create a new account for a user.
        They can customize it later if they want.
        """
        newpassword = base64.urlsafe_b64encode(os.urandom(100)).decode('utf-8')
        newusername = 'guest-' + base64.urlsafe_b64encode(os.urandom(20)).decode('utf-8')
        hashedpass = bcrypt.hashpw(newpassword, bcrypt.gensalt(1))
        
        u = User()
        u.generate(hashedpass=hashedpass,username=newusername.lower())
        u.UserSettings['maxposts'] = 20
        u.savemongo()
        
        self.set_secure_cookie("username",newusername.lower(),httponly=True)
        self.set_secure_cookie("maxposts",str(u.UserSettings['maxposts']),httponly=True)
        self.set_secure_cookie("pubkey",str(''.join(u.UserSettings['pubkey'].split() ) ),httponly=True)   
        
        # Now, force-set all the variables. 
        # These are used so the HTTP request that forces a registration goes through, using it. 
        self.username = newusername.lower()
        self.maxposts = 20
        self.pubkey = str(''.join(u.UserSettings['pubkey'].split() ) )
        self.loggedin = True

class NotFoundHandler(BaseHandler):
    """ Handler for 404s"""
    def get(self,whatever):
        self.getvars()
        self.write(self.render_string('header.html',title="Page not Found",username=self.username,loggedin=self.loggedin,pubkey=self.pubkey))
        self.write(self.render_string('404.html'))
        self.write(self.render_string('footer.html'))



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
        if numparams < 1:
            # Defaults all around
            action = "topic"
            topic = "sitecontent"
        else:
            if numparams >= 1:
                action = tornado.escape.xhtml_escape(param1) 
                
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
        
        toptopics = []
        for quicktopic in server.mongos['default']['topiclist'].find(limit=10,as_class=OrderedDict).sort('value',-1):
            toptopics.append(quicktopic)

                                
        if action == "topic":
            subjects = []
            for envelope in server.mongos['default']['envelopes'].find({'envelope.payload.topictag' : topic,'envelope.payload.regarding':{'$exists':False}},limit=self.maxposts,as_class=OrderedDict):
                subjects.append(envelope)
                
            if len(subjects) > 0:
                displayenvelope = subjects[0]
                messageid = subjects[0]['envelope']['payload_sha512'] 
                
            canon="topic/" + topic 
            title=topic
 
        if action == "message":
            displayenvelope = server.mongos['default']['envelopes'].find_one({'envelope.payload_sha512' : messageid },as_class=OrderedDict)
            topic = displayenvelope['envelope']['payload']['topictag'][0]
            subjects = []
            for envelope in server.mongos['default']['envelopes'].find({'envelope.payload.topictag' : topic,'envelope.payload.regarding':{'$exists':False}},limit=self.maxposts,as_class=OrderedDict):
                subjects.append(envelope)
            canon="message/" + displayenvelope['envelope']['local']['short_subject'] + "/" + displayenvelope['envelope']['payload_sha512']
            title = displayenvelope['envelope']['payload']['subject']
        

        u = User()
        u.load_mongo_by_username(username=self.username)
        usertrust = u.gatherTrust(displayenvelope['envelope']['payload']['author']['pubkey'])
        messagerating = u.getRatings(messageid)
        displayenvelope = server.formatEnvelope(displayenvelope)
        displayenvelope['envelope']['local']['messagerating'] = messagerating
    

        #Gather up all the replies to this message, so we can send those to the template as well
        self.write(self.render_string('header.html',title=title,username=self.username,loggedin=self.loggedin,pubkey=self.pubkey,canon=canon))
        self.write(self.render_string('tripane.html',topic=topic,toptopics=toptopics,subjects=subjects,envelope=displayenvelope))
        self.write(self.render_string('footer.html'))  
           
        if action == "message":
            self.finish("right")
        elif action == "topic":
            self.finish(div="center",div2="right")
        else:
            self.finish()
      
     
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

        if 'formatting' in envelope['envelope']['payload']:
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
            hashedpass = bcrypt.hashpw(client_newpass, bcrypt.gensalt(1))
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
                print(str(''.join(u.UserSettings['pubkey'].split() ) ))
                self.redirect("/")
                return

        self.write("I'm sorry, we don't have that username/password combo on file.")

class LogoutHandler(BaseHandler):
     def post(self):
         self.clear_all_cookies()
         self.redirect("/")

class ShowUserPosts(BaseHandler):
    def get(self,pubkey):
        self.getvars()
        
        #Unquote it, then convert it to a PluricKey object so we can rebuild it.
        #Quoting destroys the newlines.
        pubkey = urllib.parse.unquote(pubkey)
        k = Keys(pub=pubkey)
        k.format_keys()
        pubkey = k.pubkey
        
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
            gi = pygeoip.GeoIP('/usr/local/share/GeoIP/GeoIPCity.dat')
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
            gi = pygeoip.GeoIP('/usr/local/share/GeoIP/GeoIPCity.dat')
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
    def get(self,topic=None,regarding=None):
         self.getvars()
         self.write(self.render_string('header.html',title="Login to your account",username=self.username,loggedin=self.loggedin,pubkey=self.pubkey))
         self.write(self.render_string('newmessageform.html',regarding=regarding,topic=topic))
         self.write(self.render_string('footer.html'))
         self.finish('content')

    def post(self):
        self.getvars()
        if not self.loggedin:
            self.forceregister()
        

        client_body =  tornado.escape.xhtml_escape(self.get_argument("body"))
        self.include_loc = tornado.escape.xhtml_escape(self.get_argument("include_location"))

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
           
            print("Trying client_filepath") 
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

        if client_regarding is not None:
            print("Adding Regarding - " + client_regarding)
            e.payload.dict['regarding'] = client_regarding

            regardingmsg = server.mongos['default']['envelopes'].find_one({'envelope.payload_sha512':client_regarding},as_class=OrderedDict)
            e.payload.dict['topictag'] = regardingmsg['envelope']['payload']['topictag']
            e.payload.dict['subject'] = regardingmsg['envelope']['payload']['subject']
        else:
            topics = []
            topics.append(client_topic)        
            e.payload.dict['subject'] = client_subject
            e.payload.dict['topictag'] = topics

        e.payload.dict['formatting'] = "markdown"
        e.payload.dict['class'] = "message"
        e.payload.dict['body'] = client_body
       
            
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
            gi = pygeoip.GeoIP('/usr/local/share/GeoIP/GeoIPCity.dat')
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
        if newmsgid != False:
            if client_regarding is not None:
                print('/message/' + client_regarding + "#" + newmsgid)
                self.redirect('/message/' + client_regarding + "#" + newmsgid, permanent=False)
            else:
                self.redirect('/message/' + newmsgid, permanent=False)
        else:
            self.write("Failure to insert message.")

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
        toKey.format_keys()


        e = Envelope()
        topics = []
        e.payload.dict['class'] = "privatemessage"
        e.payload.dict['to'] = toKey.pubkey
        e.payload.dict['body'] = toKey.encryptToSelf(client_body)
        e.payload.dict['subject'] = toKey.encryptToSelf(client_subject)
        if client_regarding is not None:
            print("Adding Regarding - " + client_regarding)
            e.payload.dict['regarding'] = client_regarding

        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['pubkey'] = u.UserSettings['pubkey']
        e.payload.dict['author']['friendlyname'] = u.UserSettings['username']
        e.payload.dict['author']['useragent'] = "Pluric Web frontend Pre-release 0.1"
        if self.include_loc == "on":
            gi = pygeoip.GeoIP('/usr/local/share/GeoIP/GeoIPCity.dat')
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
    print("Starting Web Frontend for " + server.ServerSettings['hostname'])
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
    http_server.listen(8080)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
