#!/usr/bin/env python3
import pymongo
from datetime import datetime, timedelta
from Envelope import Envelope
from server import server
from collections import OrderedDict
import json
import sys
import os
import argparse

msgsdir = "MESSAGES/TOPICS/"

parser = argparse.ArgumentParser(
    description='Save/Load messages from the filesystem.')
parser.add_argument(
    '-s', '--save', dest='dump', action='store_true', default=False,
    help='Save all messages from the DB to a local directory')
parser.add_argument(
    '-l', '--load', dest='read', action='store_true', default=False,
    help='Load all messages from a directory into the DB')
parser.add_argument(
    '-d', '--dirs', dest='dirs', action='store_true', default=False,
    help='Store messages in directories by topic')
parser.add_argument(
    '-t', '--topic', dest='topic', action='append', default=['all'],
    help='Store only messages in topic (Can be used more than once)')
parser.add_argument(
    '-v', '--verbose', dest='verbose', action='store_true', default=False,
    help='Store each message as it\'s imported.')
args = parser.parse_args()


def writetopic(topic, since=0, limit=0, skip=0):
    """
    Write a topic out to .7z files
    """
    e = Envelope()
    if topic == 'all':
        #envelopes = server.mongos['safe']['envelopes'].find({'envelope.local.time_added': {'$gt' : since }},limit=limit,skip=skip,as_class=OrderedDict)
        envelopes = server.mongos['safe']['envelopes'].find()
    else:
        envelopes = server.mongos['safe']['envelopes'].find({'envelope.local.time_added': {'$gt': since}, 'envelope.payload.topic': topic}, limit=limit, skip=skip, as_class=OrderedDict)

    for envelope in envelopes:
        if args.verbose:
            print(envelope)
        envelope = server.formatEnvelope(envelope)
        envstr = json.dumps(envelope, separators=(',', ':'))
        e.loadstring(envstr)
        topic = e.payload.dict['topic']
        topicdir = msgsdir + topic

        # Make a dir if nec.
        if not os.path.isdir(topicdir):
            os.makedirs(topicdir)

        if not os.path.exists(topicdir + "/" + e.payload.hash() + ".7zTavernEnvelope"):
            e.savefile(topicdir)


def loaddir(directory):
    """
    Load in a directory full of Tavern Messages.
    """
    listing = os.listdir(msgsdir + directory)
    e = Envelope()

    for infile in listing:
        e.loadfile(msgsdir + directory + "/" + infile)
        server.receiveEnvelope(e.text())

if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)


if args.dump:
    for topic in args.topic:
        print("Writing - " + topic)
        writetopic(topic)


if args.read:
    for topic in args.topic:
        if topic == 'all':
            for idt in os.listdir(msgsdir):
                print("Loading Topic - " + idt)
                loaddir(idt)
        else:
            loaddir(topic)
