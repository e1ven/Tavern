# This file is the Web server.
# It defines the routes, and the handlers which create those webpages.

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.escape
from tornado.options import define, options

import time
import datetime
import socket
import json
import os

import Image
import imghdr
import io
import pygeoip
import urllib.parse

from Envelope import Envelope
from collections import OrderedDict
import lockedkey
from key import Key
from User import User

from TopicTool import topictool
from TavernUtils import memorise
from TavernUtils import TavernCache
import TavernUtils
from basehandler import BaseHandler

from libs import rss

# Import the Ramdisk vers if possible
try:
    from tmp import Robohash
except ImportError:
    from libs import Robohash

import Server
server = Server.Server()

# What happens when people request the root level?
# for now, send them to that Welcome message ;)
class EntryHandler(tornado.web.RequestHandler):
    def get(self):
        self.redirect('/topic/sitecontent')

class RSSHandler(BaseHandler):
    def get(self, action, param):
        if action == "topic":
            channel = rss.Channel('Tavern - ' + param,
                                  'http://GetTavern.com/rss/' + param,
                                  'Tavern discussion about ' + param,
                                  generator='Tavern',
                                  pubdate=datetime.datetime.now())
            for envelope in server.db.unsafe.find('envelopes', {'envelope.local.sorttopic': server.sorttopic(param), 'envelope.payload.class': 'message'}, limit=100, sortkey='envelope.local.time_added', sortdirection='descending'):
                item = rss.Item(channel,
                                envelope['envelope']['payload']['subject'],
                                "http://GetTavern.com/message/" + envelope['envelope']['local']['sorttopic'] + '/' + envelope['envelope']['local']['short_subject'] + "/" + envelope['envelope']['local']['payload_sha512'],
                                envelope['envelope']['local']['formattedbody'])
                channel.additem(item)
            self.write(channel.toprettyxml())


class MessageHistoryHandler(BaseHandler):
    """
    Display the various edits to a message.
    """
    def get(self, messageid):
        self.getvars()
        origid = server.getOriginalMessage(messageid)
        
        e = Envelope()
        if not e.loadmongo(origid):
            self.write("I can't load that message's history. ;(")
        else:
            messages = []

            # Add the root msg.
            current_message = (messageid,e.dict['envelope']['local']['time_added'])
            messages.append(current_message)

            # Add all the edits
            for message in e.dict['envelope']['local']['edits']:
                current_message = (message['envelope']['local']['payload_sha512'],message['envelope']['local']['time_added'])
                messages.append(current_message)

            self.write(self.render_string('messagehistory.html',messages=messages))

class MessageHandler(BaseHandler):

    """
    The Message Handler displays a message, when given by message id.
    It's intentionally a bit forgiving in the syntax, to make it easy to retrieve messages.
    """
    # @memorise(parent_keys=['fullcookies','request.arguments'], ttl=server.serversettings.settings['cache']['message-page']['seconds'], maxsize=server.serversettings.settings['cache']['message-page']['size'])
    def get(self, *args):
    
        self.getvars()

        # We need both col2 and col3, since the currently active message changes in the col2.
        divs = ['scrollablediv2', 'scrollablediv3']


        # Find the final directory/page sent as part of the request.
        # This could be /m/123, /m/some-topic/123 or even /m/some-topic/some-subject/123 (which is canonical)
        # We're being intentionally loose in letting this be accessed by multiple URLs, so it's easy to get here.
        # We only care about the final argument, which is the messageid.
        for i in args:
            if i is not None:
                messageid = tornado.escape.xhtml_escape(i)

        # 'before' is used for multiple pages, because skip() is slow
        # Don't really need xhtml escape, since we're converting to a float
        if "before" in self.request.arguments:
            before = float(self.get_argument('before'))
        else:
            before = None

        # Do we want to show the original, ignoring edits?
        if "showoriginal" in self.request.arguments:
            # Convert the string to a bool.
            showoriginal = (self.get_argument('showoriginal') == "True")
        else:
            showoriginal = False
      
        messagesenvelope = server.db.unsafe.find_one('envelopes',
                                                    {'envelope.local.payload_sha512': messageid})

        if messagesenvelope is not None:
            displayenvelope = Envelope()
            displayenvelope.loaddict(messagesenvelope)
            topic = displayenvelope.dict['envelope']['payload']['topic']
            self.canon = "message/" + displayenvelope.dict['envelope']['local']['sorttopic'] + '/' + displayenvelope.dict['envelope']['local']['short_subject'] + "/" + displayenvelope.dict['envelope']['local']['payload_sha512']
            title = displayenvelope.dict['envelope']['payload']['subject']
        else:
            # If we didn't find that message, throw an error.
            displayenvelope = server.error_envelope("The Message you are looking for can not be found.")
            title = displayenvelope.dict['envelope']['payload']['subject']
            topic = displayenvelope.dict['envelope']['payload']['topic']

        # Gather up all the replies to this message, so we can send those to the template as well
        self.write(self.render_string('header.html', title=title, canon=self.canon, type="topic", rsshead=displayenvelope.dict['envelope']['payload']['topic']))
        self.write(self.render_string('showmessage.html',
                   envelope=displayenvelope, before=before, topic=topic))
        self.write(self.render_string('footer.html'))
        #self.finish(divs=divs)


class TopicHandler(BaseHandler):

    """
    The Topic Handler displays a topic, and the messages that are in it.
    """

    #@memorise(parent_keys=['fullcookies','request.arguments'], ttl=server.serversettings.settings['cache']['topic-page']['seconds'], maxsize=server.serversettings.settings['cache']['topic-page']['size'])
    def get(self, topic='all'):
    
        self.getvars()
        divs = ['scrollablediv2','scrollablediv3']

        topic = tornado.escape.xhtml_escape(topic)
        # Used for multiple pages, because skip() is slow
        # Don't really need xhtml escape, since we're converting to a float
        if "before" in self.request.arguments:
            before = float(self.get_argument('before'))
        else:
            before = None

        # Do we want to show the original, ignoring edits?
        if "showoriginal" in self.request.arguments:
            # Convert the string to a bool.
            showoriginal = (self.get_argument('showoriginal') == "True")
        else:
            showoriginal = False

        if topic != 'sitecontent':
            self.canon = "topic/" + topic
            title = topic
        else:
            title = "Discuss what matters"

        topicEnvelopes = topictool.messages(topic=topic,maxposts=1)
        if len(topicEnvelopes) > 0:
            displayenvelope = topicEnvelopes[0]
        else:
            displayenvelope = server.error_envelope("That topic does not have any messages in it yet.")
            canon = None
            title = displayenvelope.dict['envelope']['payload']['subject']
            topic = displayenvelope.dict['envelope']['payload']['topic']
        # Gather up all the replies to this message, so we can send those to the template as well
        self.write(self.render_string('header.html', title=title, canon=self.canon, type="topic", rsshead=displayenvelope.dict['envelope']['payload']['topic']))
        self.write(self.render_string('showmessage.html',
                   envelope=displayenvelope, before=before, topic=topic))
        self.write(self.render_string('footer.html'))

        self.finish(divs=divs)

class ShowTopicsHandler(BaseHandler):
    def get(self, start=0):
        self.getvars()

        alltopics = topictool.toptopics(limit=start + 1000,skip=start)
        toptopics =  topictool.toptopics()

        self.write(
            self.render_string('header.html', title="List of all Topics",
                               rsshead=None, type=None))
        
        self.write(self.render_string('showtopics.html',
                   topics=alltopics, toptopics=toptopics,topic='all'))

        self.write(self.render_string('footer.html'))
        self.finish(divs=['column3'])


class TopicPropertiesHandler(BaseHandler):
    def get(self, topic):
        self.getvars()

        mods = []
        for mod in server.db.unsafe.find('modlist', {'_id.topic': server.sorttopic(topic)}, sortkey='value.trust', sortdirection='descending'):
            mod['_id']['moderator_pubkey_sha512'] = hashlib.sha512(
                mod['_id']['moderator'].encode('utf-8')).hexdigest()
            mods.append(mod)

        toptopics = toptool.toptopics()

        subjects = []
        for envelope in server.db.unsafe.find('envelopes', {'envelope.local.sorttopic': server.sorttopic(topic), 'envelope.payload.class': 'message', 'envelope.payload.regarding': {'$exists': False}}, limit=self.user.UserSettings['maxposts']):
            subjects.append(envelope)

        title = "Properties for " + topic
        self.write(self.render_string('header.html', title=title,
                                      rsshead=topic, type="topic"))
        self.write(self.render_string('topicprefs.html', topic=topic,
                   toptopics=toptopics, subjects=subjects, mods=mods))
        self.write(self.render_string('footer.html'))
        self.finish(divs=['scrollablediv3'])


class SiteContentHandler(BaseHandler):
    def get(self, message):
        self.getvars()
        client_message_id = tornado.escape.xhtml_escape(message)

        envelope = server.db.unsafe.find_one(
            'envelopes', {'envelope.local.payload_sha512': client_message_id})

        self.write(self.render_string('header.html', title="Tavern :: " + envelope['envelope']['payload']['subject'], canon="sitecontent/" + envelope['envelope']['local']['payload_sha512'], rss="/rss/topic/" + envelope['envelope']['payload']['topic'], topic=envelope['envelope']['payload']['topic']))
        self.write(self.render_string('sitecontent.html', formattedbody=envelope['envelope']['local']['formattedbody'], envelope=envelope))
        self.write(self.render_string('footer.html'))


class AttachmentHandler(BaseHandler):
    def get(self, attachment):
        self.getvars()
        client_attachment_id = tornado.escape.xhtml_escape(attachment)
        envelopes = server.db.unsafe.find('envelopes', {'envelope.payload.binaries.sha_512': client_attachment_id})
        stack = []
        for envelope in envelopes:
            stack.append(envelope)

        # Find info from one of the messages
        for attach in envelope['envelope']['local']['attachmentlist']:
            if attach['sha_512'] == client_attachment_id:
                myattach = attach

        # Determine if we can preview it
        preview = False
        if 'detected_mime' in myattach:
            if myattach['detected_mime'] in ['video/mp4', 'video/webm', 'audio/mpeg']:
                preview = True

        if 'displayable' in myattach:
            if myattach['displayable'] is not False:
                preview = True

        self.write(self.render_string('header.html', title="Tavern Attachment " + client_attachment_id, rsshead=client_attachment_id, type="attachment"))
        self.write(self.render_string(
            'showattachment.html', myattach=myattach, preview=preview, attachment=client_attachment_id, stack=stack))
        self.write(self.render_string('footer.html'))


class RegisterHandler(BaseHandler):
    def get(self):
        self.getvars()
        self.write(self.render_string('header.html',
                   title="Register for an Account", type=None, rsshead=None))
        self.write(self.render_string('registerform.html'))
        self.write(self.render_string('footer.html'))

    def post(self):
        self.getvars()
        self.write(self.render_string('header.html',
                   title='Register for an account', type=None, rsshead=None))

        client_newuser = self.get_argument("username")
        client_newpass = self.get_argument("pass")
        client_newpass2 = self.get_argument("pass2")
        if "email" in self.request.arguments:
            client_email = self.get_argument("email")
            if client_email == "":
                client_email = None
        else:
            client_email = None

        if client_newpass != client_newpass2:
            self.write("I'm sorry, your passwords don't match.")
            return

        if client_email is not None:
            users_with_this_email = server.db.safe.find('users',
                                                        {"email": client_email.lower()})
            if len(users_with_this_email) > 0:
                self.write(
                    "I'm sorry, this email address has already been used.")
                return

        users_with_this_username = server.db.safe.find('users',
                                                       {"username": client_newuser.lower()})
        if len(users_with_this_username) > 0:
            self.write("I'm sorry, this username has already been taken.")
            return

        else:
            # Generate the user
            self.user.generate(AllowGuestKey=False,
                username=client_newuser.lower(), password=client_newpass)
            self.user.UserSettings['lastauth'] = int(time.time())

            if client_email is not None:
                self.user.UserSettings['email'] = client_email.lower()

            self.user.savemongo()

            # Save the passkey out to a separate cookie.
            self.set_secure_cookie("tavern_passkey", self.user.Keys['master'].get_passkey(
                client_newpass), httponly=True, expires_days=999)

            self.setvars()
            self.redirect("/")


class LoginHandler(BaseHandler):
    def get(self, slug=None):
        self.getvars()
        self.write(self.render_string('header.html',
                   title="Login to your account", rsshead=None, type=None))
        self.write(self.render_string('loginform.html', slug=slug))
        self.write(self.render_string('footer.html'))

    def post(self):
        self.getvars()
        self.write(self.render_string('header.html',
                   title='Login to your account', rsshead=None, type=None))

        successredirect = '/'
        client_username = self.get_argument("username")
        client_password = self.get_argument("pass")
        if 'slug' in self.request.arguments:
            slug = self.get_argument("slug")
            sluglookup = server.db.unsafe.find_one('redirects', {'slug': slug})
            if sluglookup is not None:
                if sluglookup['url'] is not None:
                    successredirect = sluglookup['url']

        login = False
        user = server.db.safe.find_one('users',
                                       {"username": client_username.lower()})
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
                print("Successful login via direct password")
            elif u.verify_password(client_password.swapcase()):
                login = True
            elif u.verify_password(client_password[:1].upper() + client_password[1:]):
                login = True
            elif u.verify_password(client_password[:1].lower() + client_password[1:]):
                login = True
            if login == True:
                self.user = u

                self.clear_cookie('tavern_passkey')
                self.set_secure_cookie("tavern_passkey", self.user.Keys['master'].get_passkey(client_password), httponly=True, expires_days=999)
                self.user.UserSettings['lastauth'] = int(time.time())

                self.setvars()
                server.logger.debug("Login Successful.")
                self.redirect(successredirect)
            else:
                server.logger.debug("Username/password fail.")
                self.redirect("http://Google.com")


class LogoutHandler(BaseHandler):
    def post(self):
        self.clear_all_cookies()
        self.redirect("/")


class ChangepasswordHandler(BaseHandler):
    def get(self):
        self.getvars()

        if not self.recentauth():
            numcharacters = 100 + TavernUtils.randrange(1, 100)
            slug = TavernUtils.randstr(numcharacters, printable=True)
            server.db.safe.insert('redirects', {'slug': slug, 'url': '/changepassword', 'time': int(time.time())})
            self.redirect('/login/' + slug)
        else:
            self.write(self.render_string('header.html',
                       title="Change Password", rsshead=None, type=None))
            self.write(self.render_string('changepassword.html'))
            self.write(self.render_string('footer.html'))

    def post(self):
        self.getvars(AllowGuestKey=False)

        client_newpass = self.get_argument("pass")
        client_newpass2 = self.get_argument("pass2")

        if client_newpass != client_newpass2:
            self.write("I'm sorry, your passwords don't match.")
            return

        # Encrypt the the privkey with the new password
        self.user.changepass(newpassword=client_newpass)

        # Set the Passkey, to be able to unlock the Privkey
        self.set_secure_cookie("tavern_passkey", self.user.Keys['master'].get_passkey(
            password=client_newpass), httponly=True, expires_days=999)

        self.setvars()
        server.logger.debug("Password Change Successful.")
        self.redirect("/")


class UserHandler(BaseHandler):
    def get(self, pubkey):
        self.getvars()

        #Unquote it, then convert it to a TavernKey object so we can rebuild it.
        #Quoting destroys the newlines.
        pubkey = urllib.parse.unquote(pubkey)
        pubkey = Key(pub=pubkey).pubkey

        # Generate a clean user obj with that pubkey and nothing else.
        u = User()
        u.load_pubkey_only(pubkey)
        self.write(self.render_string('header.html', title="User page",
                                      rsshead=None, type=None))

        self.write(self.render_string(
            'userpage.html', thatguy=u,topic=None))

        self.write(self.render_string('footer.html'))


class ChangeManySettingsHandler(BaseHandler):
    def post(self):
        self.getvars(AllowGuestKey=False)

        friendlyname = self.get_argument('friendlyname')
        maxposts = int(self.get_argument('maxposts'))
        maxreplies = int(self.get_argument('maxreplies'))
        if 'include_location' in self.request.arguments:
            include_location = True
        else:
            include_location = False

        # AllowEmbed is a int, not a bool, so we can support a 0 state, which means, never set.
        if 'allowembed' in self.request.arguments:
            allowembed = 1
        else:
            allowembed = -1
        if 'display_useragent' in self.request.arguments:
            display_useragent = True
        else:
            display_useragent = False

        if 'theme' in self.request.arguments:
            newtheme = tornado.escape.xhtml_escape(self.get_argument('theme'))
            if newtheme in server.availablethemes:
                self.user.UserSettings['theme'] = newtheme

        self.user.UserSettings['display_useragent'] = display_useragent
        self.user.UserSettings['friendlyname'] = friendlyname
        self.user.UserSettings['maxposts'] = maxposts
        self.user.UserSettings['maxreplies'] = maxreplies
        self.user.UserSettings['include_location'] = include_location
        self.user.UserSettings['allowembed'] = allowembed

        self.user.savemongo()
        self.setvars()

        if "js" in self.request.arguments:
            self.finish(divs=['scrollablediv3'])
        else:
            keyurl = ''.join(self.user.Keys['master'].pubkey.split())
            self.redirect('/user/' + keyurl)


class ChangeSingleSettingHandler(BaseHandler):

    def post(self, setting, option=None):
        self.getvars(AllowGuestKey=False)
        redirect = True
        if setting == "followtopic":
            self.user.followTopic(
                self.get_argument("topic"))
        elif setting == "unfollowtopic":
            self.user.unFollowTopic(
                self.get_argument("topic"))
        elif setting == "showembeds":
            self.user.UserSettings['allowembed'] = 1
            if option == 'ajax':
                self.write('Tavern will now display all external media.')
                redirect = False
        elif setting == "dontshowembeds":
            self.user.UserSettings['allowembed'] = -1
            server.logger.debug("forbidding embeds")
        else:
            server.logger.debug("Warning, you didn't do anything!")

        self.user.savemongo()
        self.setvars()
        if "js" in self.request.arguments:
            self.finish(divs=['scrollablediv3'])
        else:
            if redirect == True:
                self.redirect("/")


class RatingHandler(BaseHandler):
    def get(self, posthash):
        self.getvars()
        #Calculate the votes for that post.

    def post(self):
        self.getvars(AllowGuestKey=False)

        #So you may be asking yourself.. Self, why did we do this as a POST, rather than
        #Just a GET value, of the form server.com/msg123/voteup
        #The answer is xsrf protection.
        #We don't want people to link to the upvote button and trick you into voting up.

        client_hash = self.get_argument("hash")
        client_rating = self.get_argument("rating")
        rating_val = int(client_rating)
        if rating_val not in [-1, 0, 1]:
            self.write("Invalid Rating.")
            return -1

        e = Envelope()
        e.payload.dict['class'] = "messagerating"
        e.payload.dict['rating'] = rating_val
        e.payload.dict['regarding'] = client_hash

        #Instantiate the user who's currently logged in

        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['replyto'] = self.user.Keys['posted'][-1].pubkey
        e.payload.dict['author'][
            'friendlyname'] = self.user.UserSettings['friendlyname']

        if self.user.UserSettings['include_location'] == True or 'include_location' in self.request.arguments:
            gi = pygeoip.GeoIP('data/GeoIPCity.dat')
            ip = self.request.remote_ip

            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"

            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + \
                "," + str(gir['longitude'])


        # Add stamps to show we're the author (and optionally) we're the origin server
        e.addStamp(stampclass='author',friendlyname=self.user.UserSettings['friendlyname'],keys=self.user.Keys['master'],passkey=self.user.passkey)
        if server.serversettings.settings['mark-origin'] == True:
                e.addStamp(stampclass='origin',keys=server.ServerKeys,hostname=server.serversettings.settings['hostname'])


        #Send to the server
        server.receiveEnvelope(env=e)

        self.write("Your vote has been recorded. Thanks!")

class UserNoteHandler(BaseHandler):
    def get(self, user):
        self.getvars()
        #Show the Note for a user

    def post(self):
        self.getvars(AllowGuestKey=False)

        client_pubkey = self.get_argument("pubkey")
        client_note = self.get_argument("note")
        self.user.setNote(client_pubkey, client_note)

        # Write it back to the page
        self.write('<input class="usernote" type="text" value="" name="note" placeholder="' + client_note + '">')
        server.logger.debug("Note Submitted.")


class UserTrustHandler(BaseHandler):
    def get(self, user):
        self.getvars()
        #Calculate the trust for a user.

    def post(self):
        self.getvars(AllowGuestKey=False)

        trusted_pubkey = urllib.parse.unquote(
            self.get_argument("trusted_pubkey"))
        trusted_pubkey = Key(pub=trusted_pubkey).pubkey

        client_trust = self.get_argument("trust")
        client_topic = self.get_argument("topic")

        trust_val = int(client_trust)
        if trust_val not in [-100, 0, 100]:
            self.write("Invalid Trust Score.")
            return -1

        e = Envelope()
        e.payload.dict['class'] = "usertrust"
        e.payload.dict['trust'] = trust_val
        e.payload.dict['topic'] = client_topic
        e.payload.dict['trusted_pubkey'] = trusted_pubkey

        #Instantiate the user who's currently logged in

        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['replyto'] = self.user.Keys['posted'][-1].pubkey
        e.payload.dict['author'][
            'friendlyname'] = self.user.UserSettings['friendlyname']


        if self.user.UserSettings['include_location'] == True or 'include_location' in self.request.arguments:
            gi = pygeoip.GeoIP('data/GeoIPCity.dat')
            ip = self.request.remote_ip

            # Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"

            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + \
                "," + str(gir['longitude'])


        # Add stamps to show we're the author (and optionally) we're the origin server
        e.addStamp(stampclass='author',friendlyname=self.user.UserSettings['friendlyname'],keys=self.user.Keys['master'],passkey=self.user.passkey)
        if server.serversettings.settings['mark-origin'] == True:
                e.addStamp(stampclass='origin',keys=server.ServerKeys,hostname=server.serversettings.settings['hostname'])


        #Send to the server

        server.receiveEnvelope(env=e)
        server.logger.debug("Trust Submitted.")

class EditMessageHandler(BaseHandler):
    def get(self, regarding):
        self.getvars()
        self.write(self.render_string('header.html',
                   title="Edit a message", rsshead=None, type=None))

        e = Envelope()
        e.loadmongo(regarding)
        oldtext = e.dict['envelope']['payload']['body']
        topic = e.dict['envelope']['payload']['topic']

        if 'edits' in e.dict['envelope']['local']:

            newestedit = e.dict['envelope']['local']['edits'][-1]
            e2 = Envelope()
            e2.loaddict(newestedit)
            oldtext = e2.dict['envelope']['payload']['body']
            topic = e2.dict['envelope']['payload']['topic']

        self.write(self.render_string('editmessageform.html',oldtext=oldtext))
        self.write(self.render_string('footer.html'))
        self.finish(divs=['scrollablediv3'])


class ReplyHandler(BaseHandler):

    def get(self, topic=None, regarding=None):
        self.getvars()
        self.write(self.render_string('header.html',
                   title="Reply to a message", rsshead=None, type=None))
        self.write(self.render_string('replyform.html',regarding=regarding))
        self.write(self.render_string('footer.html'))
        self.finish(divs=['scrollablediv3'])


class NewmessageHandler(BaseHandler):

    def get(self, topic=None):
        self.getvars()
        self.write(self.render_string('header.html',
                   title="Post a new message", rsshead=None, type=None))
        self.write(self.render_string('newmessageform.html',topic=topic))
        self.write(self.render_string('footer.html'))
        self.finish(divs=['scrollablediv3'])


class ReceiveEnvelopeHandler(BaseHandler):
    """
    Where envelopes POST.
    """
    def options(self, regarding=None):
        self.set_header('Access-Control-Allow-Methods',
                        'OPTIONS, HEAD, GET, POST, PUT, DELETE')
        self.set_header('Access-Control-Allow-Origin', '*')


    def get(self, topic=None, regarding=None):
        self.redirect('/')

    def post(self, flag=None):
        self.getvars(AllowGuestKey=False)
        filelist = []

        # We might be getting files either through nginx, or through directly.
        # If we get the file through Nginx, parse out the arguments.
        for argument in self.request.arguments:
            if (argument.startswith("attached_file") and argument.endswith('.path')) or (argument == 'files[].path'):
                individual_file = {}
                individual_file['basename'] = argument.rsplit('.')[0]
                individual_file['clean_up_file_afterward'] = True
                individual_file['filename'] = self.get_argument(
                    individual_file['basename'] + ".name")
                individual_file['content_type'] = self.get_argument(
                    individual_file['basename'] + ".content_type")
                individual_file['path'] = self.get_argument(
                    individual_file['basename'] + ".path")
                individual_file['size'] = self.get_argument(
                    individual_file['basename'] + ".size")

                fs_basename = os.path.basename(individual_file['path'])
                individual_file['fullpath'] = server.serversettings.settings[
                    'upload-dir'] + "/" + fs_basename

                individual_file['filehandle'] = open(
                    individual_file['path'], 'rb+')
                hashname = str(individual_file['basename'] + '.sha512')

                # If we have the nginx_upload new enough to give us the SHA512 hash, use it.
                # If not, calc. it.
                if hashname in self.request.arguments:
                    individual_file['hash'] = self.get_argument(
                        individual_file['basename'] + ".sha512")
                else:
                    print("Calculating Hash in Python. Nginx should do this.")
                    SHA512 = hashlib.sha512()
                    while True:
                        buf = individual_file['filehandle'].read(0x100000)
                        if not buf:
                            break
                        SHA512.update(buf)
                    individual_file['hash'] = SHA512.hexdigest()
                individual_file['filehandle'].seek(0)
                filelist.append(individual_file)

        # If we get files directly, calculate what we need to know.
        for file_field in self.request.files:
            for individual_file in self.request.files[file_field]:
                #     You get these keys from Tornado
                #       body
                #       content_type
                #       filename

                individual_file['clean_up_file_afterward'] = False
                individual_file['filehandle'] = io.BytesIO()
                individual_file['filehandle'].write(individual_file['body'])
                individual_file['size'] = len(individual_file['body'])
                SHA512 = hashlib.sha512()
                while True:
                    buf = individual_file['filehandle'].read(0x100000)
                    if not buf:
                        break
                    SHA512.update(buf)
                individual_file['filehandle'].seek(0)
                SHA512.update(individual_file['body'])
                individual_file['hash'] = SHA512.hexdigest()
                individual_file['filehandle'].seek(0)
                filelist.append(individual_file)

        envelopebinarylist = []

        # Attach the files that are actually here, submitted alongside the message.
        for attached_file in filelist:
            #All the same, let's strip out all but the basename.
            server.logger.debug("Dealing with File " + attached_file['filename']
                               + " with hash " + attached_file['hash'])
            if not server.bin_GridFS.exists(filename=attached_file['hash']):
                attached_file['filehandle'].seek(0)
                imagetype = imghdr.what(
                    'ignoreme', h=attached_file['filehandle'].read())
                acceptable_images = ['gif', 'jpeg', 'jpg', 'png', 'bmp']
                print(imagetype)
                if imagetype in acceptable_images:
                    attached_file['filehandle'].seek(0)
                    # If it's an image, open and re-save to strip EXIF data.
                    # Do so here, rather than in server, so that server->server messages aren't touched
                    Image.open(attached_file['filehandle']).save(
                        attached_file['filehandle'], format=imagetype)
                attached_file['filehandle'].seek(0)
                server.bin_GridFS.put(attached_file['filehandle'], filename=attached_file['hash'], content_type=individual_file['content_type'])
            server.logger.debug("Creating Message")
            #Create a message binary.
            mybinary = Envelope.binary(sha512=attached_file['hash'])
            #Set the Filesize. Clients can't trust it, but oh-well.
            print('estimated size : ' + str(attached_file['size']))
            mybinary.dict['filesize_hint'] = attached_file['size']
            mybinary.dict['content_type'] = attached_file['content_type']
            mybinary.dict['filename'] = attached_file['filename']
            envelopebinarylist.append(mybinary.dict)

            #Don't keep spare copies on the webservers
            attached_file['filehandle'].close()
            if attached_file['clean_up_file_afterward'] is True:
                os.remove(attached_file['fullpath'])

        # Support the Javascript upload handler.
        # return the JSON formatted reply it's looking for
        if flag == "fileonly":
            details = []
            for attached_file in filelist:
                detail = {}
                detail['name'] = attached_file['filename']
                detail['hash'] = attached_file['hash']
                detail['size'] = attached_file['size']
                detail['content_type'] = attached_file['content_type']

                detail['url'] = server.serversettings.settings[
                    'downloadsurl'] + attached_file['hash']
                details.append(detail)
            details_json = json.dumps(details, separators=(',', ':'))
            self.set_header("Content-Type", "application/json")
            print(details_json)
            self.write(details_json)
            return

        # Add the binaries which are referenced only
        # The jQuery uploader will upload them seperately, so this isn't unusual.
        for argument in self.request.arguments:
            print(argument)
            if argument.startswith("referenced_file1") and argument.endswith('_name'):
                r = re.compile('referenced_file(.*?)_name')
                m = r.search(argument)
                binarycount = m.group(1)
                mybinary = Envelope.binary(sha512=self.get_argument(
                    'referenced_file' + binarycount + '_hash'))
                mybinary.dict['filesize_hint'] = self.get_argument(
                    'referenced_file' + binarycount + '_size')
                mybinary.dict['content_type'] = self.get_argument(
                    'referenced_file' + binarycount + '_contenttype')
                mybinary.dict['filename'] = self.get_argument(
                    'referenced_file' + binarycount + '_name')
                envelopebinarylist.append(mybinary.dict)


        # Now that we have the file handled.. (Whew!) .. Let's do the Envelope

        # Pull in our Form variables.
        client_body = self.get_argument("body", None)
        client_topic = self.get_argument("topic", None)
        client_subject = self.get_argument("subject", None)

        client_to = self.get_argument("to",None)
        client_regarding = self.get_argument("regarding",None)


        e = Envelope()
        e.payload.dict['formatting'] = "markdown"

        if flag == 'message':
            e.payload.dict['class'] = "message"
            if client_topic is not None:
                e.payload.dict['topic'] = client_topic
            if client_subject is not None:
                e.payload.dict['subject'] = client_subject
            if client_body is not None:
                e.payload.dict['body'] = client_body

            if envelopebinarylist:
                e.payload.dict['binaries'] = envelopebinarylist

            e.payload.dict['author'] = OrderedDict()
            e.payload.dict['author']['replyto'] = self.user.Keys['posted'][-1].pubkey
            e.payload.dict['author'][
                'friendlyname'] = self.user.UserSettings['friendlyname']


            e.addStamp(stampclass='author',friendlyname=self.user.UserSettings['friendlyname'],keys=self.user.Keys['master'],passkey=self.user.passkey)

        elif flag == 'reply':
            e.payload.dict['class'] = "message"
            if client_regarding is not None:
                e.payload.dict['regarding'] = client_regarding
                regardingmsg = server.db.unsafe.find_one('envelopes', {'envelope.local.payload_sha512': client_regarding})
                e.payload.dict['topic'] = regardingmsg['envelope']['payload']['topic']
                e.payload.dict['subject'] = regardingmsg['envelope']['payload']['subject']
            if client_body is not None:
                e.payload.dict['body'] = client_body
            if envelopebinarylist:
                e.payload.dict['binaries'] = envelopebinarylist
 
            e.payload.dict['author'] = OrderedDict()
            e.payload.dict['author']['replyto'] = self.user.Keys['posted'][-1].pubkey
            e.payload.dict['author'][
                'friendlyname'] = self.user.UserSettings['friendlyname']


            e.addStamp(stampclass='author',friendlyname=self.user.UserSettings['friendlyname'],keys=self.user.Keys['master'],passkey=self.user.passkey)



        elif flag == 'messagerevision':
            e.payload.dict['class'] = "messagerevision"
            if client_body is not None:
                e.payload.dict['body'] = client_body
            e.addStamp(stampclass='author',friendlyname=self.user.UserSettings['friendlyname'],keys=self.user.Keys['master'],passkey=self.user.passkey)

        elif flag =='privatemessage':
            # For encrypted messages we want to actually create a whole sub-envelope inside of it!

            single_use_key = self.user.get_pmkey()
            single_use_key.unlock(self.user.passkey)


            e.payload.dict['class'] = "privatemessage"
            touser = Key(pub=client_to)
            e.payload.dict['to'] = touser.pubkey
            e.payload.dict['author'] = OrderedDict()
            e.payload.dict['author']['replyto'] = single_use_key.pubkey

            encrypted_msg = Envelope()
            encrypted_msg.payload.dict['formatting'] = "markdown"
            encrypted_msg.payload.dict['body'] = client_body
            encrypted_msg.payload.dict['class'] = 'privatemessage'

            if client_regarding is not None:
                encrypted['regarding'] = client_regarding
                regardingmsg = server.db.unsafe.find_one('envelopes', {'envelope.local.payload_sha512': client_regarding})

                # The message we're referencing is likey unreadable due to encryption.
                # Pull in it's subject if possible.
                decrypted_regarding_dict = self.user.decrypt(regardingmsg['payload']['encrypted'])
                decrypted_regarding = Envelope()
                decrypted_regarding.loaddict(decrypted_regarding_dict)

                encrypted_msg.payload.dict['subject'] = decrypted_regarding.payload.dict['subject']
            else:
                encrypted_msg.payload.dict['subject'] = client_subject

            if envelopebinarylist:
                encrypted_msg.payload.dict['binaries'] = envelopebinarylist


            encrypted_msg.payload.dict['author'] = OrderedDict()
            encrypted_msg.payload.dict['author']['replyto'] = single_use_key.pubkey
            encrypted_msg.payload.dict['author'][
                'friendlyname'] = self.user.UserSettings['friendlyname']


            if self.user.UserSettings['include_location'] == True or 'include_location' in self.request.arguments:
                gi = pygeoip.GeoIP('data/GeoIPCity.dat')
                ip = self.request.remote_ip

                #Don't check from home.
                if ip == "127.0.0.1":
                    ip = "8.8.8.8"

                gir = gi.record_by_name(ip)
                encrypted_msg.payload.dict['coords'] = str(gir['latitude']) + \
                    "," + str(gir['longitude'])


            # Add stamps to show we're the author (and optionally) we're the origin server
            encrypted_msg.addStamp(stampclass='author',friendlyname=self.user.UserSettings['friendlyname'],keys=self.user.Keys['master'],passkey=self.user.passkey)
            if server.serversettings.settings['mark-origin'] == True:
                    encrypted_msg.addStamp(stampclass='origin',keys=server.ServerKeys,hostname=server.serversettings.settings['hostname'])


            # Now that we've created the inner message, convert it to text, store it in the outer message.
            encrypted_pmstr = encrypted_msg.text()

            e.payload.dict['encrypted'] = single_use_key.encrypt(encrypt_to=touser.pubkey, encryptstring=encrypted_pmstr)


        # For all classses of messages-

        if self.user.UserSettings['include_location'] == True or 'include_location' in self.request.arguments:
            gi = pygeoip.GeoIP('data/GeoIPCity.dat')
            ip = self.request.remote_ip

            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"

            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + \
                "," + str(gir['longitude'])


        if server.serversettings.settings['mark-origin'] == True:
                e.addStamp(stampclass='origin',keys=server.ServerKeys,hostname=server.serversettings.settings['hostname'])

        #Send to the server
        newmsgid = server.receiveEnvelope(env=e)
        if newmsgid != False:
            if client_to is None:
                if client_regarding is not None:
                    self.redirect('/message/' + server.getTopMessage(
                        newmsgid) + "?jumpto=" + newmsgid, permanent=False)
                else:
                    self.redirect('/message/' + newmsgid, permanent=False)
            else:
                self.redirect('/showprivates')
        else:
            self.write("Failure to insert message.")


class ShowPrivatesHandler(BaseHandler):
    def get(self,messageid=None):
        self.getvars(AllowGuestKey=False)

        messages = []
        self.write(self.render_string('header.html',
                   title="Your Private messages", rsshead=None, type=None))

        # Construct a list of all current PMs
        for message in server.db.unsafe.find('envelopes', {'envelope.payload.to': {'$in' : self.user.get_keys(ret='pubkey')}}, limit=10, sortkey='value', sortdirection='descending'):

            if self.user.decrypt(message['envelope']['payload']['encrypted']):
                unencrypted_str = self.user.decrypt(message['envelope']['payload']['encrypted'])
                unencrypted_env = Envelope()
                unencrypted_env.loadstring(unencrypted_str)
                unencrypted_env.munge()
                unencrypted_env.dict['parent'] = message
                messages.append(unencrypted_env)


        # Retrieve a PM to display - Either by id if requested, or top PM if not.
        e = Envelope()
        if messageid is not None:
            if not e.loadmongo(messageid):
                self.write("Can't load that..")
                return
            else:
                if e.dict['envelope']['payload']['to'] not in self.user.get_keys(ret='pubkey'):
                    print("This is to--")
                    print(e.dict['envelope']['payload']['to'])
                    print("Your Keys-")
                    print( self.user.get_keys(ret='pubkey'))
                    self.write("This isn't you.")
                    return
                    #TODO - Put better error here. Server.Error?
            unencrypted_str = self.user.decrypt(e.dict['envelope']['payload']['encrypted'])
            
            unencrypted_env = Envelope()
            unencrypted_env.loadstring(unencrypted_str)
            unencrypted_env.munge()
            unencrypted_env.dict['parent'] = e.dict

            displaymessage = unencrypted_env

        elif messages:
                displaymessage = messages[0]
        else:
            displaymessage = server.error_envelope("You don't have any private messages yet. Silly goose!")




        self.write(self.render_string('header.html', title="Private Messages", rsshead=None, type=None))
        self.write(
            self.render_string('show_privates.html', messages=messages,envelope=displaymessage))
        self.write(self.render_string('footer.html'))



class NewPrivateMessageHandler(BaseHandler):
    def get(self, urlto=None):
        self.getvars()
        self.write(self.render_string('header.html',
                   title="Send a private message", rsshead=None, type=None))
        self.write(self.render_string('privatemessageform.html', urlto=urlto))
        self.write(self.render_string('footer.html'))


class NullHandler(BaseHandler):
        # This is grabbed by nginx, and never called in prod.
    def get(self, url=None):
        return

    def post(self, url=None):
        return


class BinariesHandler(tornado.web.RequestHandler):
    """
    Serves images/etc out of nginx.
    Really shouldn't be used in prod.
    Use the nginx handler instead
    """
    def get(self, binaryhash, filename=None):
        server.logger.info("The gridfs_nginx plugin is a much better option than this method")
        self.set_header("Content-Type", 'application/octet-stream')

        req = server.bin_GridFS.get_last_version(filename=binaryhash)
        self.write(req.read())

class AvatarHandler(tornado.web.RequestHandler):
    """
    Create Avatars using Robohashes.
    You should cache these on disk using nginx.
    """
    def get(self, avatar):
        format = 'png'
        self.set_header("Content-Type", "image/" + format)

        # Ensure proper sizing
        sizex,sizey = self.get_argument('size','40x40').split("x")
        sizex = int(sizex)
        sizey = int(sizey)
        if sizex > 4096 or sizex < 0:
            sizex = 40
        if sizey > 4096 or sizey < 0:
            sizey = 40
        robo = Robohash.Robohash(avatar)
        robo.assemble(roboset=self.get_argument('set','any'),format=format,bgset=self.get_argument('bgset','any'),sizex=sizex,sizey=sizey)
        robo.img.save(self,format='png')


define("writelog", default=True, help="Determines if Tavern writes to a log file.",type=bool)
define("loglevel", default="UNSET", help="Amount of detail you want.",type=str)
define("initonly", default=False, help="Create config files, then quit.",type=bool)
define("debug", default=False, help="Run with options that make debugging easier.",type=bool)
define("port", default=8080, help="run on the given port", type=int)

def main():
    tornado.options.parse_command_line()
    # timeout in seconds
    timeout = 10
    socket.setdefaulttimeout(timeout)
    server.logger.info(
        "Starting Web Frontend for " + server.serversettings.settings['hostname'])

    server.debug = options.debug
    # Tell the server process to fire up and run for a while.
    server.start()


    settings = {
        "cookie_secret": server.serversettings.settings['cookie-encryption'],
        "login_url": "/login",
        "xsrf_cookies": True,
        "template_path": "themes",
        "autoescape": "xhtml_escape"
    }

    # Detect if we have the ramdisk setup for static files
    staticopts = {}
    if os.path.isfile('tmp/static/scripts/default.js'):
        staticopts['path'] = os.path.join(os.path.dirname(__file__), "tmp/static/")
    else:
        staticopts['path'] = os.path.join(os.path.dirname(__file__), "static/")

    application = tornado.web.Application([
        (r"/", EntryHandler),

        (r"/message/(.*)/(.*)/(.*)", MessageHandler),
        (r"/message/(.*)/(.*)", MessageHandler),
        (r"/message/(.*)", MessageHandler),
        (r"/m/(.*)/(.*)/(.*)", MessageHandler),
        (r"/m/(.*)/(.*)", MessageHandler),
        (r"/m/(.*)", MessageHandler),

        (r"/topic/(.*)", TopicHandler),
        (r"/t/(.*)", TopicHandler),
        
        (r"/sitecontent/(.*)", SiteContentHandler),

        (r"/showtopics", ShowTopicsHandler),
        (r"/showprivates", ShowPrivatesHandler),
        (r"/privatemessage/(.*)", ShowPrivatesHandler),

        (r"/topicinfo/(.*)", TopicPropertiesHandler),
        (r"/attachment/(.*)", AttachmentHandler),
        

        (r"/messagehistory/(.*)", MessageHistoryHandler),
        (r"/user/(.*)", UserHandler),

        (r"/newmessage/(.*)", NewmessageHandler),        
        (r"/newmessage", NewmessageHandler),        

        (r"/edit/(.*)", EditMessageHandler),
        (r"/reply/(.*)/(.*)", ReplyHandler),
        (r"/reply/(.*)", ReplyHandler),
        (r"/newprivatemessage/(.*)", NewPrivateMessageHandler),

        (r"/uploadenvelope/(.*)", ReceiveEnvelopeHandler),
        (r"/uploadfile/(.*)", ReceiveEnvelopeHandler),

        (r"/register", RegisterHandler),
        (r"/login/(.*)", LoginHandler),
        (r"/login", LoginHandler),
        (r"/changepassword", ChangepasswordHandler),
        (r"/logout", LogoutHandler),

        
        (r"/vote", RatingHandler),
        (r"/usertrust", UserTrustHandler),
        (r"/usernote", UserNoteHandler),

        (r"/changesetting/(.*)/(.*)", ChangeSingleSettingHandler),
        (r"/changesetting/(.*)", ChangeSingleSettingHandler),
        (r"/changesettings", ChangeManySettingsHandler),

        (r"/rss/(.*)/(.*)", RSSHandler),

        (r"/avatar/(.*)", AvatarHandler),
        (r"/binaries/(.*)/(.*)", BinariesHandler),
        (r"/binaries/(.*)", BinariesHandler),
        (r"/static/(.*)", tornado.web.StaticFileHandler, staticopts)
    ], **settings)

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)

    server.logger.info(
        server.serversettings.settings['hostname'] + ' is ready for requests on port ' + str(options.port) )
    if options.initonly is False:
        tornado.ioloop.IOLoop.instance().start()
    else:
        server.logger.info("Exiting immediatly as requested")

if __name__ == "__main__":
    main()
