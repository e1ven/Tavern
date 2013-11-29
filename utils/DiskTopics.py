#!/usr/bin/env python3
from Envelope import Envelope
import Server
server = Server.Server()
import sys
import os
import argparse
import tempfile
import shutil

msgsdir = "data/messages/topics/"

parser = argparse.ArgumentParser(
    description='Save/Load messages from the filesystem.')
parser.add_argument(
    '-r', '--reprocess', dest='reprocess', action='store_true', default=False,
    help='Reprocess the Tavern DB - Save all messages to a tmpdir, drop the DB, then load them all in.')
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
    help='Explain more things.')
args = parser.parse_args()


def writetopic(topic, since=0, limit=0, skip=0, directory=None):
    """Write a topic out to .7z files."""
    e = Envelope()
    if topic == 'all':
        envelopes = server.db.safe.find('envelopes')
    else:
        envelopes = server.db.safe.find(
            'envelopes',
            {'envelope.local.time_added': {'$gt': since},
             'envelope.payload.topic': topic},
            limit=limit,
            skip=skip)

    for envelope in envelopes:
        if args.verbose:
            print(envelope)

        id = envelope['envelope']['local']['payload_sha512']
        e.loadmongo(id)
        e.validate()

        if 'topic' in e.payload.dict:
            topic = e.payload.dict['topic']
        else:
            topic = 'none'

        if directory is None:
            topicdir = msgsdir + topic
        else:
            topicdir = directory

        # Make a dir if nec.
        if not os.path.isdir(topicdir):
            os.makedirs(topicdir)

        if not os.path.exists(topicdir + "/" + e.payload.hash() + ".7zTavernEnvelope"):
            e.savefile(topicdir)


def loaddir(directory=None, topic='sitecontent'):
    """Load in a directory full of Tavern Messages."""
    if directory is None:
        directory = msgsdir + topic
    print("Using directory: " + directory)

    listing = os.listdir(directory)
    e = Envelope()
    for infile in listing:
        print(infile)
        e.loadfile(directory + "/" + infile)
        if args.verbose:
            print(e.text())
        # Send to the server. Don't bother to validate it first, the server
        # will do it.
        server.receiveEnvelope(env=e)


def main():

    # Start Tavern services.

    if len(sys.argv) <= 1:
        parser.print_help()
        sys.exit(1)

    print("Starting server for message-processing...")
    server.start()
    server.keygenerator.stop()

    # server.logger.setLevel("DEBUG")
    # server.logger.addHandler(server.consolehandler)

    # Save files to the local HD.
    if args.dump:
        for topic in args.topic:
            print("Writing - " + topic)
            writetopic(topic)

    # Load local files.
    if args.read:
        for topic in args.topic:
            if topic == 'all':
                for idt in os.listdir(msgsdir):
                    if os.path.isdir(msgsdir + idt):
                        print("Loading Topic - " + idt)
                        loaddir(directory=msgsdir + idt)
                    else:
                        print("Non topic file in envelopes directory.")
            else:
                if os.path.isdir(topic):
                    loaddir(topic=topic)

    # Reprocess all Tavern messages
    if args.reprocess:
        print("Writing all envelopes to files...")
        directory = tempfile.mkdtemp()
        writetopic(topic='all', directory=directory)
        server.db.safe.drop_collection('envelopes')
        print("Reading envelopes back in...")
        loaddir(directory=directory)
        shutil.rmtree(directory, ignore_errors=True, onerror=None)

    # We're done here.
    server.stop()

# Run the main() function.
if __name__ == "__main__":
    main()
