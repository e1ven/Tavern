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
import imghdr 
import random
import socket
import pymongo
import json
from PIL import Image
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
import TopicList
import uuid

import re
try: 
   from hashlib import md5 as md5_func
except ImportError:
   from md5 import new as md5_func
import NofollowExtension


define("port", default=8090, help="run on the given port", type=int)

class BaseHandler(tornado.web.RequestHandler):
    def error(self,errortext):
	    self.write("***ERROR***")
	    self.write(errortext)
	    self.write("***END ERROR***")
	    
    def getvars(self):
        if "clientauth" in self.request.arguments:
            clientauth = self.get_argument("clientauth")
            self.sessionid = server.mongos['sessions']['sessions'].find_one({'client-session' : clientauth })
        else:
            self.sessionid = None
                

class NotFoundHandler(BaseHandler):
    def get(self,whatever):
        self.error("API endpoint Not found.")


class ListActiveTopics(BaseHandler):        
    def get(self):       
        topics = OrderedDict()
        for topicrow in server.mongos['default']['topiclist'].find({}):
            topics[topicrow['_id']['tag']] = topicrow['value']['count']
        self.write(json.dumps(topics,ensure_ascii=False,separators=(u',',u':')))


class MessageHandler(BaseHandler):        
    def get(self,message,persp=None):
        
        client_message_id = tornado.escape.xhtml_escape(message)
        if persp is not None:
            client_perspective = tornado.escape.xhtml_escape(persp)
        else: 
            client_perspective = None
        
        envelope = server.mongos['default']['envelopes'].find_one({'envelope.payload_sha512' : client_message_id })

        if client_perspective is not None:
            u = User()
            u.load_mongo_by_pubkey(pubkey=client_perspective)
            usertrust = u.gatherTrust(envelope['envelope']['payload']['author']['pubkey'])
            messagerating = u.getRatings(client_message_id)
        else:
            usertrust = 100
            messagerating = 1
        
        envelope = server.formatEnvelope(envelope)
        envelope['envelope']['local']['calculatedrating'] = messagerating    
        self.write(json.dumps(envelope,ensure_ascii=False,separators=(u',',u':')))


class TopicHandler(BaseHandler):        
    def get(self,topic,persp=None,offset=0,include=100):
                
        if persp is not None:
            client_perspective = tornado.escape.xhtml_escape(persp)
        else: 
            client_perspective = None
            
        envelopes = []
        client_topic = tornado.escape.xhtml_escape(topic)
        
        for envelope in server.mongos['default']['envelopes'].find({'envelope.payload.topictag' : client_topic },limit=include,skip=offset):
            if client_perspective is not None:
                u = User()
                u.load_mongo_by_pubkey(pubkey=client_perspective)
                usertrust = u.gatherTrust(envelope['envelope']['payload']['author']['pubkey'])
                messagerating = u.getRatings(envelope['envelope']['payload_sha512'])
                envelope['envelope']['local']['calculatedrating'] = messagerating    
                
            envelope = server.formatEnvelope(envelope)
            envelopes.append(envelope)
                   
        self.write(json.dumps(envelopes,ensure_ascii=False,separators=(u',',u':')))
                


                                
class ShowUserPosts(BaseHandler):
    def get(self,pubkey):
        self.getvars()
        
        #Unquote it, then convert it to a PluricKey object so we can rebuild it.
        #Quoting destroys the newlines.
        pubkey = urllib.unquote(pubkey)
        k = Keys(pub=pubkey)
        k.formatkeys()
        pubkey = k.pubkey
        
        
        messages = []
        self.write(self.render_string('templates/header.html',title="Welcome to Pluric!",username=self.username,loggedin=self.loggedin))
        # for message in server.mongos['default']['envelopes'].find({'envelope.payload.author.pubkey':pubkey},fields={'envelope.payload_sha512','envelope.payload.topictag','envelope.payload.subject'},limit=10,).sort('value',-1):
        #     messages.append(message)

        self.write(self.render_string('templates/showuserposts.html',messages=messages))
        self.write(self.render_string('templates/footer.html'))
                 

            
            
        

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
        e.payload.dict['payload_type'] = "rating"
        e.payload.dict['rating'] = rating_val
        e.payload.dict['regarding'] = client_hash
            
        #Instantiate the user who's currently logged in
        user = server.mongos['default']['users'].find_one({"username":self.username})        
        u = User()
        u.load_mongo_by_pubkey(user['pubkey'])
        
        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['pubkey'] = u.UserSettings['pubkey']
        e.payload.dict['author']['friendlyname'] = u.UserSettings['username']
        e.payload.dict['author']['client'] = "Pluric Web frontend Pre-release 0.1"
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
        e.dict['envelope']['sender_signature'] = usersig
        
        #Send to the server
        server.receiveEnvelope(e.text())


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
        e.payload.dict['payload_type'] = "usertrust"
        e.payload.dict['trust'] = trust_val
                
        k = Keys(pub=client_pubkey)
        e.payload.dict['pubkey'] = k.pubkey

        #Instantiate the user who's currently logged in
        user = server.mongos['default']['users'].find_one({"username":self.username})        
        u = User()
        u.load_mongo_by_pubkey(user['pubkey'])

        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['pubkey'] = u.UserSettings['pubkey']
        e.payload.dict['author']['friendlyname'] = u.UserSettings['username']

        e.payload.dict['author']['client'] = "Pluric Web frontend Pre-release 0.1"
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
        e.dict['envelope']['sender_signature'] = usersig

        #Send to the server
        server.receiveEnvelope(e.text())



      
class PrivateMessagesHandler(BaseHandler):
    def get(self,pubkey):

        client_pubkey =  tornado.escape.xhtml_escape(pubkey)             
        envelopes = []

        for envelope in server.mongos['default']['envelopes'].find({'envelope.payload.to':client_pubkey}):
            formattedtext = server.formatText(envelope)
            envelope['envelope']['local']['formattedbody'] = formattedbody
            envelopes.append(message)

        self.write(json.dumps(envelopes,ensure_ascii=False,separators=(u',',u':')))
        

class SubmitMessageHandler(BaseHandler):
    def post(self):
        client_message =  tornado.escape.xhtml_escape(self.get_argument("message"))
        server.receiveEnvelope(client_message)

        
class RegisterClientHandler(BaseHandler):
    def get(self,pubkey):
        client_pubkey =  tornado.escape.xhtml_escape(pubkey)
        u = uuid.uuid4()
        endpoint = OrderedDict()
        endpoint['pubkey'] = client_pubkey
        endpoint['_id'] = client_pubkey
        endpoint['token'] = str(u)
        endpoint['users'] = []
        server.mongos['default']['api-clients'].save(endpoint)
        self.write(str(u))
        
        
class RegisterClientUsersHandler(BaseHandler):
    def get(self,token):
        client_token =  tornado.escape.xhtml_escape(token) 
        client = server.mongos['default']['api-clients'].find_one({"token":client_serverpubkey})        
        client_userpublickeylist =  tornado.escape.xhtml_escape(self.get_argument("userpublickeylist"))
        client['users'] = client_userpublickeylist
        server.mongos['default']['api-clients'].save(client)

        
        
def main():
    tornado.options.parse_command_line()
    # timeout in seconds
    timeout = 10
    socket.setdefaulttimeout(timeout)
    print "Starting Web Frontend for " + server.ServerSettings['hostname']
    #####TAKE ME OUT IN PRODUCTION!!!!@! #####
    
    tl = TopicList.TopicList()        
    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "cookie_secret": "7cxqGjRMzxv7E9Vxq2mnXalZbeUhaoDgnoTSvn0B",
        "login_url": "/login",
        "xsrf_cookies": True,
    }
    application = tornado.web.Application([
        (r"/ListActiveTopics" ,ListActiveTopics),
        (r"/message/(.*)" ,MessageHandler),
        (r"/message/(.*)/(.*)", MessageHandler),
        (r"/topictag/(.*)", TopicHandler),
        (r"/topictag/(.*)/(.*)", TopicHandler),
        (r"/topictag/(.*)/(.*)/(.*)", TopicHandler),
        
        
        (r"/(.*)", NotFoundHandler)
    ], **settings)
    
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
