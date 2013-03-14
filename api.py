#!/usr/bin/env python3
#
# Copyright 2011 Tavern

import codecs
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.escape
import time
import datetime
import os
import imghdr
import socket
import pymongo
import json
import Image
from Envelope import Envelope
from collections import OrderedDict
import pymongo
from tornado.options import define, options
from Server import server
from keys import *
from User import User
from gridfs import GridFS
import hashlib
import urllib.request
import urllib.parse
import urllib.error
#import TopicList
import uuid
from ServerSettings import serversettings

import re
try:
    from hashlib import md5 as md5_func
except ImportError:
    from md5 import new as md5_func


define("port", default=8090, help="run on the given port", type=int)


class BaseHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        """
        Wrap the default RequestHandler with extra methods
        """
        super(BaseHandler, self).__init__(*args, **kwargs)
        # Add in a random fortune
        self.set_header("X-Fortune", str(server.fortune.random()))
        self.set_header("Access-Control-Allow-Origin", "*")

    def error(self, errortext):
        self.write("***ERROR***")
        self.write(errortext)
        self.write("***END ERROR***")

    def getvars(self):
        if "clientauth" in self.request.arguments:
            clientauth = self.get_argument("clientauth")
            self.sessionid = server.db.sessions['sessions'].find_one(
                {'client-session': clientauth})
        else:
            self.sessionid = None


class NotFoundHandler(BaseHandler):
    def get(self, whatever):
        self.error("API endpoint Not found.")


class ListActiveTopics(BaseHandler):
    def get(self):
        toptopics = []
        for quicktopic in server.db.unsafe['topiclist'].find(collection='topiclist', limit=10, sortkey='value', sortdirection='descending'):
            toptopics.append(quicktopic['_id']['tag'])
        self.write(json.dumps(toptopics, separators=(',', ':')))
        self.finish()


class MessageHandler(BaseHandler):
    def get(self, message, persp=None):

        client_message_id = tornado.escape.xhtml_escape(message)
        if persp is not None:
            client_perspective = tornado.escape.xhtml_escape(persp)
        else:
            client_perspective = None

        envelope = server.db.unsafe.find_one(
            'envelopes', {'envelope.payload_sha512': client_message_id})
        if client_perspective is not None:
            u = User()
            u.load_mongo_by_pubkey(pubkey=client_perspective)
            usertrust = u.gatherTrust(
                envelope['envelope']['payload']['author']['pubkey'])
            messagerating = u.getRatings(client_message_id)
        else:
            usertrust = 100
            messagerating = 1

        envelope = server.formatEnvelope(envelope)
        envelope['envelope']['local'] = {}
        envelope['envelope']['local']['calculatedrating'] = messagerating
        self.write(json.dumps(envelope, separators=(',', ':')))


class TopicHandler(BaseHandler):
    def get(self, topic, since='1319113800', include=100, offset=0, persp=None,):
        if persp is not None:
            client_perspective = tornado.escape.xhtml_escape(persp)
        else:
            client_perspective = None

        envelopes = []
        client_topic = tornado.escape.xhtml_escape(topic)
        since = int(tornado.escape.xhtml_escape(since))
        server.logger.info(serversettings.settings['pubkey'])
        for envelope in server.db.unsafe.find('envelopes', {'envelope.local.time_added': {'$gt': since}, 'envelope.local.sorttopic': server.sorttopic(client_topic)}, limit=include, skip=offset):
            if client_perspective is not None:
                u = User()
                u.load_mongo_by_pubkey(pubkey=client_perspective)
                usertrust = u.gatherTrust(
                    envelope['envelope']['payload']['author']['pubkey'])
                messagerating = u.getRatings(
                    envelope['envelope']['payload_sha512'])
                envelope['envelope']['local'][
                    'calculatedrating'] = messagerating

            envelope = server.formatEnvelope(envelope)
            envelopes.append(envelope)

        self.write(json.dumps(envelopes, separators=(',', ':')))


class PrivateMessagesHandler(BaseHandler):
    def get(self, pubkey):

        client_pubkey = tornado.escape.xhtml_escape(pubkey)
        envelopes = []

        for envelope in server.db.unsafe.find('envelopes', {'envelope.payload.to': client_pubkey}):
            formattedtext = server.formatText(envelope, formatting=envelope['envelope']['payload']['formatting'])
            envelope['envelope']['local']['formattedbody'] = formattedbody
            envelopes.append(message)

        self.write(json.dumps(envelopes, separators=(',', ':')))


class SubmitEnvelopeHandler(BaseHandler):
    def post(self):

        client_message = tornado.escape.to_unicode(
            self.get_argument("envelope"))
        # Receive a message, server.logger.info back it's SHA
        self.write(server.receiveEnvelope(client_message))


class ServerStatus(BaseHandler):
    def get(self):
        status = OrderedDict()
        status['timestamp'] = int(time.time())
        status['pubkey'] = server.ServerKeys.pubkey
        status['hostname'] = serversettings.settings['hostname']
        # Report ourselves, plus the default connection.
        status['connections'] = ['http://' + serversettings.settings['hostname']
                                 + ':8090', 'http://GetTavern.com:8090', 'http://Tavern.is:8090']
        self.write(json.dumps(status, separators=(',', ':')))


def main():
    tornado.options.parse_command_line()
    # timeout in seconds
    timeout = 10
    socket.setdefaulttimeout(timeout)
    server.logger.info(
        "Starting Web Frontend for " + serversettings.settings['hostname'])

    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "cookie_secret": "7cxqGjRMzxv7E9Vxq2mnXalZbeUhaoDgnoTSvn0B",
        "login_url": "/login",
        "xsrf_cookies": False,
    }
    application = tornado.web.Application([
        (r"/topics", ListActiveTopics),
        (r"/status", ServerStatus),
        (r"/message/(.*)", MessageHandler),
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
