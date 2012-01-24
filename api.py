#!/usr/bin/env python3
#
# Copyright 2011 Pluric
    
import codecs
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
import Image
from Envelope import Envelope
from collections import OrderedDict
import pymongo
from tornado.options import define, options
from server import server
import pprint
from keys import *
from User import User
from gridfs import GridFS
import hashlib
import urllib.request, urllib.parse, urllib.error
#import TopicList
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
            self.sessionid = server.mongos['sessions']['sessions'].find_one({'client-session' : clientauth },as_class=OrderedDict)
        else:
            self.sessionid = None
                

class NotFoundHandler(BaseHandler):
    def get(self,whatever):
        self.error("API endpoint Not found.")


class ListActiveTopics(BaseHandler):  
    def get(self):      
        toptopics = []
        for quicktopic in server.mongos['default']['topiclist'].find(limit=10,as_class=OrderedDict).sort('value',-1):
            toptopics.append(quicktopic['_id']['tag']) 
        self.write(json.dumps(toptopics,separators=(',',':')))
        self.finish()

class MessageHandler(BaseHandler):        
    def get(self,message,persp=None):
        
        client_message_id = tornado.escape.xhtml_escape(message)
        if persp is not None:
            client_perspective = tornado.escape.xhtml_escape(persp)
        else: 
            client_perspective = None
            
        envelope = server.mongos['default']['envelopes'].find_one({'envelope.payload_sha512' : client_message_id },as_class=OrderedDict)
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
        self.write(json.dumps(envelope,separators=(',',':')))


class TopicHandler(BaseHandler):        
    def get(self,topic,since='1319113800',include=100,offset=0,persp=None,):
        if persp is not None:
            client_perspective = tornado.escape.xhtml_escape(persp)
        else: 
            client_perspective = None    
            
        envelopes = []
        client_topic = tornado.escape.xhtml_escape(topic)
        since = int(tornado.escape.xhtml_escape(since))
        print(server.ServerSettings['pubkey'])
        for envelope in server.mongos['default']['envelopes'].find({'envelope.stamps.time_added': {'$gt' : since },'envelope.payload.topic' : client_topic },limit=include,skip=offset,as_class=OrderedDict):
            print("foo")
            if client_perspective is not None:
                print("FFFF")
                u = User()
                u.load_mongo_by_pubkey(pubkey=client_perspective)
                usertrust = u.gatherTrust(envelope['envelope']['payload']['author']['pubkey'])
                messagerating = u.getRatings(envelope['envelope']['payload_sha512'])
                envelope['envelope']['local']['calculatedrating'] = messagerating    
                
            envelope = server.formatEnvelope(envelope)
            envelopes.append(envelope)
                   
        self.write(json.dumps(envelopes,separators=(',',':')))
            
class PrivateMessagesHandler(BaseHandler):
    def get(self,pubkey):

        client_pubkey =  tornado.escape.xhtml_escape(pubkey)             
        envelopes = []

        for envelope in server.mongos['default']['envelopes'].find({'envelope.payload.to':client_pubkey},as_class=OrderedDict):
            formattedtext = server.formatText(envelope)
            envelope['envelope']['local']['formattedbody'] = formattedbody
            envelopes.append(message)

        self.write(json.dumps(envelopes,separators=(',',':')))
        

class SubmitEnvelopeHandler(BaseHandler):
    def post(self):
        
        client_message = tornado.escape.to_unicode(self.get_argument("envelope"))
        # Receive a message, print back it's SHA
        self.write(server.receiveEnvelope(client_message))

class ServerStatus(BaseHandler):
    def get(self):
        status = OrderedDict()
        
        status['timestamp'] = int(time.time())
        status['pubkey'] = server.ServerKeys.pubkey
        status['hostname'] = server.ServerSettings['hostname']
        self.write(json.dumps(status,separators=(',',':')))
        
        

        
        
def main():
    tornado.options.parse_command_line()
    # timeout in seconds
    timeout = 10
    socket.setdefaulttimeout(timeout)
    print("Starting Web Frontend for " + server.ServerSettings['hostname'])
     
    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "cookie_secret": "7cxqGjRMzxv7E9Vxq2mnXalZbeUhaoDgnoTSvn0B",
        "login_url": "/login",
        "xsrf_cookies": False,
    }
    application = tornado.web.Application([
        (r"/topics" ,ListActiveTopics),
        (r"/status" ,ServerStatus),
        (r"/message/(.*)" ,MessageHandler),
        (r"/message/(.*)/(.*)", MessageHandler),
        (r"/newenvelope", SubmitEnvelopeHandler),        
        (r"/topic/(.*)/(.*)/(.*)/(.*)/(.*)", TopicHandler),
        (r"/topic/(.*)/(.*)/(.*)/(.*)", TopicHandler),
        (r"/topic/(.*)/(.*)/(.*)", TopicHandler),
        (r"/topic/(.*)/(.*)", TopicHandler),
        (r"/topic/(.*)", TopicHandler),   
        (r"/(.*)", NotFoundHandler)
    ], **settings)
    
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
