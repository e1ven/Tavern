# This file is the Web self.server.
# It defines the routes, and the handlers which create those webpages.

import sys
import optparse
import socket

from robohash import Robohash

import libtavern.server
import libtavern.envelope
import libtavern.utils
import libtavern.key
import libtavern.topic
import libtavern.user

import webtav.webbase as webbase
from webtav.webbase import weberror
import webtav.uimodules

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.escape
import tornado.wsgi

import flask

import pygeoip


class EntryHandler(webbase.BaseTornado):
    def get(self):
        """
        A simple redirect, that will redirect people from / to a FAQ.

        Currently, this redirects everyone.
        Eventually, it may give a different experience for first-time visitors.
        """
        self.redirect('/t/sitecontent',permanent=False)

class MessageHandler(webbase.BaseTornado):
    def get(self,messageid):
        """
        Displays a given message.
        Parameters Topic and Short_sub are ignored - They are in the URL for SEO reasons.
        :param messageid: The ID of the message
        """

        messagesenvelope = self.server.db.unsafe.find_one('envelopes', {'envelope.local.payload_sha512': messageid})

        if messagesenvelope is None:
            raise weberror(short="Can't find that message.", long="I'm sorry, but we just can't find the message you're looking for. ;(",code=404,log='Looking for ' + str(messageid))

        self.displayenvelope = libtavern.envelope.Envelope()
        self.displayenvelope.loaddict(messagesenvelope)

        self.topic = libtavern.topic.Topic(topic=self.displayenvelope.dict['envelope']['payload']['topic'])
        self.canon = self.server.url_for(envelope=self.displayenvelope)
        self.title = self.displayenvelope.dict['envelope']['payload']['subject']

        self.render('View-showmessage.html')

class MessageHistoryHandler(webbase.BaseTornado):
    def get(self, messageid):
        """Display the various edits to a message."""

        e = libtavern.envelope.Envelope()
        if not e.loadmongo(messageid):
            raise weberror(short="That message's history can't be found :(",
                                  long="I'm terribly sorry, but I can't find any history for the message that's been requested.")

        # Get the original message
        if isinstance(e.payload, libtavern.payloads.Message):
            original = e
        elif isinstance(e.payload, libtavern.envelope.Envelope.MessageRevision):
            original = e.get_original()
        else:
            raise TavernException(self, subject="That message's history can't be found :(",
                                  body="I'm terribly sorry, but I can't find any history for the message that's been requested.")

        # Create a list of unique message ids, and the time we first saw it.
        edits = []
        # Append in the original message's information
        edits.append(original)

        # Loop through all the messages we've received, add to list.
        if 'edits' in original.dict['envelope']['local']:
            for editdict in original.dict['envelope']['local']['edits']:
                e = libtavern.envelope.Envelope()
                e.loaddict(editdict)
                if e not in edits:
                    edits.append(e)
        # Sort the edits.
        edits.sort(key=lambda e: (e.dict['envelope']['local']['priority'], (e.dict['envelope']['local']['time_added'])))

        self.displayenvelope = original
        self.topic = libtavern.topic.Topic(self.displayenvelope.dict['envelope']['payload']['topic'])
        self.canon = self.server.url_for(envelope=self.displayenvelope)
        self.title = "History for " + self.displayenvelope.dict['envelope']['payload']['subject']

        self.render('View-messagehistory.html',edits=edits)


class TopicHandler(webbase.BaseTornado):
    def get(self,topic):
        """
        Display the messages for a given topic
        """
        self.title = topic
        self.topic = libtavern.topic.Topic(topic=topic)
        self.canon = self.server.url_for(topic=topic)

        if self.topic.count() < 1:
            self.displayenvelope = self.server.error_envelope(
                subject="That topic doesn't have any messages in it yet!",
                topic=topic,
                body="""The particular topic you're viewing doesn't have any posts in it yet.
                You can be the first! Like Neil Armstrong, Edmund Hillary, or Ferdinand Magellan, you have the chance to start something.
                Don't be nervous. Breathe. You can do this.
                Click the [New Message]("""+self.server.url_for(topic=self.topic) + '/new' +""" "Post Something!") button, and get started.
                We're rooting you.""")

        self.render('View-showmessage.html')

class AllMessagesHandler(webbase.BaseTornado):
    def get(self):
        """
        Display all messages.
        """
        self.topic.name = "All Messages"
        self.title = "Tavern - All Messages"
        self.canon = self.server.url_for(topic=self.topic)
        self.specialtopic = True

        if self.topic.count() < 1:
            self.displayenvelope = self.server.error_envelope(
                subject="Welcome to Tavern!",
                topic="None",
                body="""This Tavern server has __NO__ messages posted yet.
                If it's public, it should sync up with some other servers soon.
                If not, click the [New Message]("""+self.server.url_for(topic=self.topic) + '/new'+""" "Post Something!") button, and get things started.""")

        self.render('View-showmessage.html')

class AllSavedHandler(webbase.BaseTornado):
    def get(self):
        """
        Display all messages.
        """
        self.topic.name = "Messages from saved topics"

        self.title = "Tavern - Messages in all saved topics"
        self.canon = "/all/saved"
        self.specialtopic = True

        topics = []
        for topic in self.user.followed_topics:
            topics.append(topic.sortname)


        if self.topic.count() < 1:
            self.displayenvelope = self.server.error_envelope(
                subject="Welcome to Tavern!",
                topic="None",
                body="""There are no messages in any topics you have saved.""")

        self.render('View-showmessage.html')




class ShowAllTopicsHandler(webbase.BaseTornado):
    """Show every known topic"""
    def get(self,page=0):
        self.title = "List of all topics"
        topics_per_page = 1000

        if page > 0:
            skip = topics_per_page * page
        else:
            skip = 0

        alltopics = self.topic.toptopics(limit=topics_per_page, skip=skip)
        totalcount = self.server.db.unsafe.count('topiclist')
        remaining = totalcount - len(alltopics) - skip

        self.render('View-showtopics.html',topics=alltopics,remaining=remaining,page=page)

class TopicPropertiesHandler(webbase.BaseTornado):
    """Show Properties for a topic"""
    def get(self,topic):
        self.topic = libtavern.topic.Topic(topic)
        self.title = "Properties for " + self.topic.name

        # Get a list of the most popular mods
        mods = []
        for mod in self.server.db.unsafe.find('modlist', {'_id.topic': libtavern.topic.sorttopic(topic)}, sortkey='value.trust', sortdirection='descending'):
            mods.append(mod)
        self.render('View-topicprefs.html',mods=mods)


class SiteContentHandler(webbase.BaseTornado):
    """Displays site content, such as FAQ, Ettiquite, etc, without replies or other chrome."""
    def get(self,message):
        envelope = self.server.db.unsafe.find_one(
            'envelopes', {'envelope.local.payload_sha512': message})

        if envelope is None:
            raise weberror(short="That page can't be found.", long="I'm sorry, but the page you're looking for doesn't seem to available on this site. ;(",code=404,log='Sitecontent - looking for ' + str(messageid))

        self.displayenvelope = libtavern.envelope.Envelope()
        self.displayenvelope.loaddict(envelope)

        self.topic = libtavern.topic.Topic(topic=self.displayenvelope.dict['envelope']['payload']['topic'])
        self.canon = self.server.url_for(envelope=self.displayenvelope)
        self.title = self.displayenvelope.dict['envelope']['payload']['subject']

        self.render('View-sitecontent.html')


# def AttachmentHandler_get(attachment):
#     self.getvars()
#     client_attachment_id = tornado.escape.xhtml_escape(attachment)
#     envelopes = self.server.db.unsafe.find(
#         'envelopes',
#         {'envelope.payload.binaries.sha_512': client_attachment_id})
#     stack = []
#     for envelope in envelopes:
#         stack.append(envelope)

# Find info from one of the messages
#     for attach in envelope['envelope']['local']['attachmentlist']:
#         if attach['sha_512'] == client_attachment_id:
#             myattach = attach

# Determine if we can preview it
#     preview = False
#     if 'detected_mime' in myattach:
#         if myattach['detected_mime'] in ['video/mp4', 'video/webm', 'audio/mpeg']:
#             preview = True

#     if 'displayable' in myattach:
#         if myattach['displayable'] is not False:
#             preview = True

#     self.write(
#         self.render_string(
#             'header.html',
#             title="Tavern Attachment " +
#             client_attachment_id,
#             rsshead=client_attachment_id,
#             type="attachment"))
#     self.write(self.render_string(
#         'showattachment.html', myattach=myattach, preview=preview, attachment=client_attachment_id, stack=stack))
#     self.write(self.render_string('footer.html'))

class RegisterHandler(webbase.BaseTornado):
    """
    Register a new user for the site.
    """
    def get(self):
        self.title = "Register for a new account"
        self.canon = self.server.url_for(envelope=self.displayenvelope)
        self.render('View-new_user.html')

    def post(self):
        """Create the user in the DB, as requested."""
        username = self.get_argument("username")
        pass1 = self.get_argument("pass")
        pass2 = self.get_argument("pass2")
        email = self.get_argument("email",None)

        u = libtavern.user.User()
        if pass1 != pass2:
            raise weberror(short="Can't create user", long="The two passwords didn't match, can you try again?",code=400)
        if not u.is_username_free(username=username):
            raise weberror(short="Can't create user", long="That username is already being used by someone.",code=400)

        # Create a temporary user, set it to current user.
        u.username = username
        print(u.ensure_keys(AllowGuestKey=False))
        print(u.passkey)
        print(u.changepass(newpassword=pass1,oldpasskey=u.passkey))
        if email:
            self.user.add_email(email)
        u.save_mongo()
        self.user = u
        self.save_session()
        self.redirect(self.server.url_for(user=u))

class LoginHandler(webbase.BaseTornado):
    """
    Allow a user to login to the site.
    Checks a username against mongo, and sees if their password unlocks the key.
    """

    def get(self):
        """
        Display the login form.
        """
        self.title = "Log in to your Tavern account"
        self.canon = self.server.url_for(base=True) + "/login"
        self.render('View-login.html')

    def post(self):
        """
        Receive/Process the login form.
        """
        username = self.get_argument("username")
        password = self.get_argument("pass")

        # Load the user, see if we can match the pass.
        u = libtavern.user.User()
        if not u.load_mongo_by_username(username=username.lower()):
            raise weberror(short="That username can't be found", long="I'm sorry, but there's no record of that username on this Server. Perhaps you originally logged in via another method?.",code=400)

        if not u.verify_password(password):
            raise weberror(short="That password doesn't look right", long="The password you gave doesn't match the one on-file for the account.",code=400)

        # If we've made it here, user/pass matches. We're good.
        self.user = u
        self.save_session()
        self.write("You have successfully logged in.")

class LogoutHandler(webbase.BaseTornado):
    def post(self):
        self.clear_all_cookies()
        self.redirect(self.server.url_for(base=True))

# def ChangepasswordHandler_get():
#     self.getvars()
#       self.js = """{% block extraJS %}
#     <script defer src="/static/scripts/zxcvbn.min.js}}"></script>
#     <script defer src="/static/scripts/register.min.js}}"></script>
# {% end extraJS %}"""
#     if not self.recentauth():
#         numcharacters = 100 + libtavern.TavernUtils.randrange(1, 100)
#         slug = libtavern.TavernUtils.randstr(numcharacters, printable=True)
#         self.server.db.safe.insert(
#             'redirects',
#             {'slug': slug,
#              'url': '/changepassword',
#              'time': int(time.time())})
#         bottle.redirect('/login/' + slug)
#     else:
#         self.write(self.render_string('header.html',
#                    title="Change Password", rsshead=None, type=None))
#         self.write(self.render_string('changepassword.html'))
#         self.write(self.render_string('footer.html'))


# def ChangepasswordHandler_post():
#     self.getvars(AllowGuestKey=False)

#     client_newpass = self.get_argument("pass")
#     client_newpass2 = self.get_argument("pass2")

#     if client_newpass != client_newpass2:
#         self.write("I'm sorry, your passwords don't match.")
#         return

# Encrypt the the privkey with the new password
#     self.user.changepass(newpassword=client_newpass)

# Set the Passkey, to be able to unlock the Privkey
#     self.set_secure_cookie("tavern_passkey", self.user.Keys['master'].get_passkey(
#         password=client_newpass), httponly=True, expires_days=999)

#     self.setvars()
#     self.server.logger.debug("Password Change Successful.")
#     bottle.redirect("/")


class UserHandler(webbase.BaseTornado):
    """
    Print the User's information

    If this is your account, also shows an UI to change settings.
    """
    def get(self,pubkey):

        # Generate a new user, using the pubkey we just received.
        # We are careful not to retrieve anything secret.
        u = libtavern.user.User()
        u.load_publicinfo_by_pubkey(pubkey)

        self.write(self.render_string(
            'View-showuser.html', thatguy=u))


# def ChangeManySettingsHandler_post():
#     self.getvars(AllowGuestKey=False)

#     friendlyname = self.get_argument('friendlyname')
#     maxposts = int(self.get_argument('maxposts'))
#     maxreplies = int(self.get_argument('maxreplies'))
#     if 'include_location' in self.request.arguments:
#         include_location = True
#     else:
#         include_location = False

# AllowEmbed is a int, not a bool, so we can support a 0 state, which
# means, never set.
#     if 'allowembed' in self.request.arguments:
#         allowembed = 1
#     else:
#         allowembed = -1
#     if 'display_useragent' in self.request.arguments:
#         display_useragent = True
#     else:
#         display_useragent = False

#     if 'theme' in self.request.arguments:
#         newtheme = tornado.escape.xhtml_escape(self.get_argument('theme'))
#         if newtheme in self.server.availablethemes:
#             self.user.theme = newtheme

#     self.user.display_useragent = display_useragent
#     self.user.friendlyname = friendlyname
#     self.user.maxposts = maxposts
#     self.user.maxreplies = maxreplies
#     self.user.include_location = include_location
#     self.user.allow_embed = allowembed

#     self.user.savemongo()
#     self.setvars()

#     if "js" in self.request.arguments:
# self.finish(divs=['scrollablediv3'])
#         self.finish(divs=['wrappertable'])

#     else:
#         bottle.redirect(self.server.url_for(user=self.user))


# def ChangeSingleSettingHandler_post(setting, option=None):
#     self.getvars(AllowGuestKey=False)
#     redirect = True
#     if setting == "followtopic":
#         self.user.follow_topic(
#             self.get_argument("topic"))
#     elif setting == "unfollowtopic":
#         self.user.unfollow_topic(
#             self.get_argument("topic"))
#     elif setting == "showembeds":
#         self.user.allowembed = 1
#         if option == 'ajax':
#             self.write('Tavern will now display all external media.')
#             redirect = False
#     elif setting == "dontshowembeds":
#         self.user.allowembed = -1
#         self.server.logger.debug("forbidding embeds")
#     else:
#         self.server.logger.debug("Warning, you didn't do anything!")

#     self.user.savemongo()
#     self.setvars()
#     if "js" in self.request.arguments:
# self.finish(divs=['scrollablediv3'])
#         self.finish(divs=['wrappertable'])

#     else:
#         if redirect:
#             bottle.redirect("/")


# def RatingHandler_get(posthash):
#     self.getvars()
# Calculate the votes for that post.


# def RatingHandler_post():
#     self.getvars(AllowGuestKey=False)

# So you may be asking yourself.. Self, why did we do this as a POST, rather than
# Just a GET value, of the form self.server.com/msg123/voteup
# The answer is xsrf protection.
# We don't want people to link to the upvote button and trick you into
# voting up.

#     client_hash = self.get_argument("hash")
#     client_rating = self.get_argument("rating")
#     rating_val = int(client_rating)
#     if rating_val not in [-1, 0, 1]:
#         self.write("Invalid Rating.")
#         return -1

#     e = libtavern.envelope.Envelope()
#     e.payload.dict['class'] = "messagerating"
#     e.payload.dict['rating'] = rating_val
#     e.payload.dict['regarding'] = client_hash

# Instantiate the user who's currently logged in

#     e.payload.dict['author'] = {}
#     e.payload.dict['author']['replyto'] = self.user.new_posted_key().pubkey
#     e.payload.dict['author'][
#         'friendlyname'] = self.user.friendlyname

#     if self.user.include_location or 'include_location' in self.request.arguments:
#         gi = pygeoip.GeoIP('datafiles/GeoLiteCity.dat')
#         ip = self.request.remote_ip

# Don't check from home.
#         if ip == "127.0.0.1":
#             ip = "8.8.8.8"

#         gir = gi.record_by_name(ip)
#         e.payload.dict['coords'] = str(gir['latitude']) + \
#             "," + str(gir['longitude'])

# Add stamps to show we're the author (and optionally) we're the origin
# server
#     e.addStamp(
#         stampclass='author',
#         friendlyname=self.user.friendlyname,
#         keys=self.user.Keys['master'],
#         passkey=self.user.passkey)
#     if self.server.serversettings.settings['mark-origin']:
#         e.addStamp(
#             stampclass='origin',
#             keys=self.server.ServerKeys,
#             hostname=self.server.serversettings.settings['hostname'])

# Send to the server
#     self.server.receiveEnvelope(env=e)

#     self.write("Your vote has been recorded. Thanks!")


# def UserNoteHandler_get(user):
#     self.getvars()
# Show the Note for a user


# def UserNoteHandler_post():
#     self.getvars(AllowGuestKey=False)

#     client_pubkey = self.get_argument("pubkey")
#     client_note = self.get_argument("note")
#     self.user.set_note(client_pubkey, client_note)

# Write it back to the page
#     self.write(
#         '<input class="usernote" type="text" value="" name="note" placeholder="' +
#         client_note +
#         '">')
#     self.server.logger.debug("Note Submitted.")


# def UserTrustHandler_get(user):
#     self.getvars()
# Calculate the trust for a user.


# def UserTrustHandler_post():
#     self.getvars(AllowGuestKey=False)

#     trusted_pubkey = urllib.parse.unquote(
#         self.get_argument("trusted_pubkey"))
#     trusted_pubkey = Key(pub=trusted_pubkey).pubkey

#     client_trust = self.get_argument("trust")
#     client_topic = self.get_argument("topic")

#     trust_val = int(client_trust)
#     if trust_val not in [-100, 0, 100]:
#         self.write("Invalid Trust Score.")
#         return -1

#     e = libtavern.envelope.Envelope()
#     e.payload.dict['class'] = "usertrust"
#     e.payload.dict['trust'] = trust_val
#     e.payload.dict['topic'] = client_topic
#     e.payload.dict['trusted_pubkey'] = trusted_pubkey

# Instantiate the user who's currently logged in

#     e.payload.dict['author'] = {}
#     e.payload.dict['author']['replyto'] = self.user.new_posted_key().pubkey
#     e.payload.dict['author'][
#         'friendlyname'] = self.user.friendlyname

#     if self.user.include_location or 'include_location' in self.request.arguments:
#         gi = pygeoip.GeoIP('datafiles/GeoLiteCity.dat')
#         ip = self.request.remote_ip

# Don't check from home.
#         if ip == "127.0.0.1":
#             ip = "8.8.8.8"

#         gir = gi.record_by_name(ip)
#         e.payload.dict['coords'] = str(gir['latitude']) + \
#             "," + str(gir['longitude'])

# Add stamps to show we're the author (and optionally) we're the origin
# server
#     e.addStamp(
#         stampclass='author',
#         friendlyname=self.user.friendlyname,
#         keys=self.user.Keys['master'],
#         passkey=self.user.passkey)
#     if self.server.serversettings.settings['mark-origin']:
#         e.addStamp(
#             stampclass='origin',
#             keys=self.server.ServerKeys,
#             hostname=self.server.serversettings.settings['hostname'])

# Send to the server
#     self.server.receiveEnvelope(env=e)
#     self.server.logger.debug("Trust Submitted.")


# def EditMessageHandler_get(regarding):
#     self.getvars()
#     self.write(self.render_string('header.html',
#                title="Edit a message", rsshead=None, type=None))

#     e = libtavern.envelope.Envelope()
#     e.loadmongo(regarding)
#     oldtext = e.dict['envelope']['payload']['body']
#     topic = e.dict['envelope']['payload']['topic']

#     if 'edits' in e.dict['envelope']['local']:

#         newestedit = e.dict['envelope']['local']['edits'][-1]
#         e2 = libtavern.envelope.Envelope()
#         e2.loaddict(newestedit)
#         oldtext = e2.dict['envelope']['payload']['body']
#         topic = e2.dict['envelope']['payload']['topic']
#         regarding = e2.dict['envelope']['payload']['regarding']

#     self.write(
#         self.render_string(
#             'editmessageform.html',
#             oldtext=oldtext,
#             topic=topic, regarding=regarding))
#     self.write(self.render_string('footer.html'))
# self.finish(divs=['scrollablediv3'])
#     self.finish(divs=['wrappertable'])


# def ReplyHandler_get(topic=None, regarding=None):
#     self.getvars()
#     self.write(self.render_string('header.html',
#                title="Reply to a message", rsshead=None, type=None))
#     self.write(
#         self.render_string(
#             'replyform.html',
#             regarding=regarding,
#             topic=topic))
#     self.write(self.render_string('footer.html'))
# self.finish(divs=['scrollablediv3'])
#     self.finish(divs=['wrappertable'])

class NewMessageHandler(webbase.BaseTornado):
    """
    Create a new message.
    """
    def get(self,topic=None):
        if topic:
            self.title = "New Message for " + topic
            self.topic = libtavern.topic.Topic(topic=topic)
        else:
            self.title = "New Message"
        self.canon = self.server.url_for(topic=self.topic) + "/new"
        self.render('View-new_message.html')

class NewReplyHandler(webbase.BaseTornado):
    """
    Creates a new message in reply to a message we already have.
    """
    def get(self,regarding):
        e = libtavern.envelope.Envelope()
        if not e.loadmongo(regarding):
            raise weberror(short="The original message can't be found :(",
                                  long="I'm terribly sorry, but I can't load the original message you are trying to reply to.")

        self.displayenvelope = e
        self.canon = self.server.url_for(envelope=e) + "/reply"
        self.render('View-new_replymessage.html',regarding=e.dict['envelope']['local']['payload_sha512'])

# def NewPrivateMessageHandler_get(urlto=None):
#     self.getvars()
#     self.write(self.render_string('header.html',
#                title="Send a private message", rsshead=None, type=None))
#     self.write(self.render_string('privatemessageform.html', urlto=urlto))
#     self.write(self.render_string('footer.html'))


# def NullHandler_get(url=None):
#     return


# def NullHandler_post(url=None):
#     return


# def BinariesHandler_get(attachment, filename=None):
#     self.server.logger.info(
#         "The gridfs_nginx plugin is a much better option than this method")
#     self.set_header("Content-Type", 'application/octet-stream')

#     req = self.server.bin_GridFS.get_last_version(filename=attachment)
#     self.write(req.read())

class CatchallHandler(webbase.BaseTornado):
    """
    Handler for any requests that aren't handled anywhere else.
    Returns 404.
    """
    def get(self):
        raise weberror(short="That page doesn't exist.", long="I'm sorry, but the page you're looking for can't be found. ;(",code=404)
    def post(self):
        raise weberror(short="That page doesn't exist.", long="I'm sorry, but the page you're looking for can't be found. ;(",code=404)
    def put(self):
        raise weberror(short="That page doesn't exist.", long="I'm sorry, but the page you're looking for can't be found. ;(",code=404)
    def delete(self):
        raise weberror(short="That page doesn't exist.", long="I'm sorry, but the page you're looking for can't be found. ;(",code=404)

class AvatarHandler(webbase.BaseTornado):
    """Create Avatars using Robohashes.
    You should cache these on disk using nginx.
    """
    def get(self, avatar):
        format = 'png'
        self.set_header("Content-Type", "image/" + format)

        # Ensure proper sizing
        sizex, sizey = self.get_argument('size', '40x40').split("x")
        sizex = int(sizex)
        sizey = int(sizey)
        if sizex > 4096 or sizex < 0:
            sizex = 40
        if sizey > 4096 or sizey < 0:
            sizey = 40
        robo = Robohash(avatar)
        robo.assemble(
            roboset=self.get_argument(
                'set',
                'any'),
            format=format,
            bgset=self.get_argument(
                'bgset',
                'any'),
            sizex=sizex,
            sizey=sizey)
        robo.img.save(self, format='png')


# def RssHandler(self,action,topic):
#    """Generate an RSS feed for a given topic"""
#     """Generates RSS feeds for a Topic."""
#     def get(action, topic):
#         channel = rss.Channel('Tavern - ' + param,
#                               'http://GetTavern.com/rss/' + param,
#                               'Tavern discussion about ' + param,
#                               generator='Tavern',
#                               pubdate=datetime.datetime.utcnow())
#         for envelope in self.server.db.unsafe.find('envelopes', {'envelope.local.sorttopic': libtavern.topic.sorttopic(param), 'envelope.payload.class': 'message'}, limit=100, sortkey='envelope.local.time_added', sortdirection='descending'):
#             item = rss.Item(channel,
#                             envelope['envelope']['payload']['subject'],
#                             "http://GetTavern.com/m/" + envelope[
#                                 'envelope'][
#                                 'local'][
#                                 'sorttopic'] + '/' + envelope[
#                                 'envelope'][
#                                 'local'][
#                                 'short_subject'] + "/" + envelope[
#                                 'envelope'][
#                                 'local'][
#                                 'payload_sha512'],
#                             envelope['envelope']['local']['formattedbody'])
#             channel.additem(item)
#         self.write(channel.toprettyxml())


class SiteIndexHandler(webbase.BaseTornado):
    def get(self):
        """
        Return a sitemap index file, which includes all other sitemap files.
        Since each sitemap.xml file can only contain 50K urls, we need to split these.
        """

        max_posts = self.server.serversettings.settings['webtav']['urls_per_sitemap']


        # Without a number, we want the index, which lists the other xml files.
        # - Each one can contain up to 50K URLs
        count = self.topic.count(include_replies=True)
        messagecount = int(count / max_posts) + 1

        # Get the base URL for the server
        prefix=self.server.url_for(base=True,fqdn=True)
        prefix += "sitemap/m/"

        self.render('View-siteindex.html',messagecount=messagecount,utils=libtavern.utils,prefix=prefix)

    def get_template_path(self):
        """
        Force this request out of the robots folder, since it's not for people.
        """
        basepath = self.application.settings.get("template_path")
        return basepath + '/robots'

class SitemapMessagesHandler(webbase.BaseTornado):
    def get(self,iteration):
        """
        Create a sitemap.xml file to show a slice of messages.
        """

        max_posts = self.server.serversettings.settings['webtav']['urls_per_sitemap']

        # We want to figure out how many messages to skip.
        # We do this by multiplying the number of messages per file (max_posts) * which file we're on.
        # For aesthetic reasons, I think the sitemaps should start at 1, not 0.
        iteration = int(iteration) - 1

        # The skip is complicated because we want to avoid using .skip()
        # Instead, every time this function finishes, we store the newest date in it's slot.
        # Then, we can skip forward to date+1 millisecond for the next slot.


        # Get the highest date for one slot lower than us.
        previous_sitemap = 'messages_' + str(iteration - 1)
        results = self.server.db.unsafe.find_one('sitemap',{'_id':previous_sitemap})
        if results:
            after = results.get('last_message_date',0)
        else:
            after = 0

        messages = self.topic.messages(maxposts=max_posts,after=after,include_replies=True)
        if not messages:
            self.set_status(404)
            self.write("That sitemap does not exist.")
            return

        # Save our highest value out to the DB
        results = {}
        results['_id'] = 'messages_' + str(iteration)
        results['last_message_date'] = messages[-1].dict['envelope']['local']['time_added']
        self.server.db.unsafe.save('sitemap',results)

        self.render('View-sitemap.html',messages=messages,utils=libtavern.utils)


    def get_template_path(self):
        """
        Force this request out of the robots folder, since it's not for people.
        """
        basepath = self.application.settings.get("template_path")
        return basepath + '/robots'


class XSRFHandler(webbase.XSRFBaseHandler):
    """
    The XSRF handler returns a xsrf token

    This handler's output is included into the header via nginx SSI.
    By importing via SSI, nginx can cache the output from other handlers.

    Otherwise, each request from a non-logged in user would do a full page-load,
    since the Set-Cookie would bypass the cache.

    We do need a separate token for each request, since the site contains a login form.
    Combining them in nginx lets us have a separate xsrf value while still caching on sessionid.

    This inherits from XSRFBaseHandler so that it bypasses the regular login/session path.
    """
    def get(self):
        """
        Internal only handler that returns the xsrf token.
        This is called by nginx, not accessible to the outside world.
        """
        self.write(str(self.xsrf_token))

    def get_template_path(self):
        """
        Force this request out of the robots folder, since it's not for people.
        """
        basepath = self.application.settings.get("template_path")
        return basepath + '/robots'


class UploadMessageHandler(webbase.BaseFlask):
    """
    Receive a message POSTed to the server.
    """
    def sign_and_deliver(self, envelope):
        """
        Sign the message with the Author's info, and upload to the server.
        :return: ID of insert (if successful)
        """

        if self.request.files:
            envelope.payload.dict['attachments'] = []
            for file in self.request.files:
                envelope.payload.dict['attachments'].append(file.sha)

        if self.include_location:
            gi = pygeoip.GeoIP('data/GeoLiteCity.dat')
            ip = self.request.remote_ip
            gir = gi.record_by_name(ip)
            envelope.payload.dict['coords'] = str(gir['latitude']) + "," + str(gir['longitude'])

        # Add a Author section, with info on how to contact the author.
        envelope.payload.dict['author'] = {}
        envelope.payload.dict['author']['replyto'] = self.user.new_posted_key().pubkey
        envelope.payload.dict['author']['friendlyname'] = self.user.friendlyname


        # Import the Payload into the parent dict, then objectify it
        envelope.flatten()

        # Add a Stamp, which signs the message with the Author's key.
        envelope.addStamp(stampclass='author',friendlyname=self.user.friendlyname,keys=self.user.Keys['master'],passkey=self.user.passkey)

        # Opt-in way to debug/explore network.
        if self.server.serversettings.settings['mark-seen']:
                envelope.addStamp(stampclass='origin',keys=server.ServerKeys,hostname=server.serversettings.settings['hostname'])

        # Send to the server
        if self.server.receive_envelope(env=envelope):
            return True
        return False

    def receive_files(self):
        """
        Receive and store files.
        """


        # Each file in self.request.files is a Werkzeug FileStorage object.
        # http://werkzeug.pocoo.org/docs/datastructures/#werkzeug.datastructures.FileStorage
        for file in self.request.files:
            file.sha,file.filesize = libtavern.utils.hash_file(file.stream)
            file.mimetype = magic.from_buffer(memcopy.read(), mime=True).decode('utf-8')
            if file.filesize > self.server.serversettings.settings['webtav']['uploads']['max_size']:
                list.remove(file)
            # Make a preview image if possible
            if file.filesize < self.server.serversettings.settings['webtav']['uploads']['max_image_size']:
                memcopy = io.BytesIO()
                file.save(memcopy)
                memcopy.seek(0)
                if file.mimetype in ['image/gif', 'image/jpeg', 'image/png', 'image/bmp']:
                    # Our attachment appears to be an image -
                    # If we open and resave, it will strip the EXIF data.
                    memcopy.seek(0)
                    Image.open(memcopy)
                    Image.save(memcopy)

                    # Don't generate a preview/etc here.
                    # We need to do that as a sub-function of receiveEnvelope, so it happens for ALL envelopes.
                    file.stream = memcopy
            # Save the file out to GridFS
            if not self.server.bin_GridFS.exists(filename=file.sha):
                self.server.bin_GridFS.put(file.stream,filename=file.sha,content_type=file.mimetype)
            file.close()

    @webbase.BaseTornado.requires_acct
    def post(self):
        """Receive Envelopes and their attachments."""

        # If there are any files that were sent along with the envelope, save them out.
        self.receive_files()
        e = libtavern.envelope.Envelope()
        e.payload.dict['formatting'] = "markdown"
        e.payload.dict['class'] = "message"
        e.payload.dict['topic'] = self.get_argument("topic")
        e.payload.dict['subject'] = self.get_argument("subject")
        e.payload.dict['body'] = self.get_argument("body")
        if self.get_argument("regarding", None):
            e.payload.dict['regarding'] = self.get_argument("regarding")

        res = self.sign_and_deliver(envelope=e)
        if res:
            self.redirect(server.url_for(envelope=e))
        else:
            return "Oh Noes!"
            self.write("Failure to insert message.")


class UploadMessageReplyHandler(UploadMessageHandler):
    """Upload a reply to an earlier message."""

    @webbase.BaseTornado.requires_acct
    def post(self):
        # If there are any files that were sent along with the envelope, save them out.
        self.receive_files()

        # Load original
        original = libtavern.envelope.Envelope()
        if not original.loadmongo(mongo_id=self.get_argument("regarding")):
            raise weberror(short="The original message can't be found :(",
                                  long="I'm terribly sorry, but I can't load the original message you are trying to reply to.")

        e = libtavern.envelope.Envelope()
        e.payload.dict['formatting'] = "markdown"
        e.payload.dict['class'] = "message"
        e.payload.dict['topic'] = original.payload.dict['topic']
        e.payload.dict['subject'] = self.get_argument("subject",original.payload.dict['subject'])
        e.payload.dict['body'] = self.get_argument("body")
        e.payload.dict['regarding'] = self.get_argument("regarding")

        res = self.sign_and_deliver(envelope=e)

        if res:
            return self.redirect(self.server.url_for(envelope=e))
        else:
            return "Oh Noes!"
            self.write("Failure to insert message.")


class UploadMessageRevisionHandler(UploadMessageHandler):
    """Upload a revision to an earlier message."""

    @webbase.BaseTornado.requires_acct
    def post(self):
        """Receive Envelopes and their attachments."""

        # If there are any files that were sent along with the envelope, save them out.
        self.receive_files()


        e = libtavern.envelope.Envelope()
        e.payload.dict['formatting'] = "markdown"
        e.payload.dict['class'] = "messagerevision"
        e.payload.dict['topic'] = self.get_argument("topic")
        e.payload.dict['subject'] = self.get_argument("subject")
        e.payload.dict['body'] = self.get_argument("body")
        e.payload.dict['regarding'] = self.get_argument("regarding")

        # Save binaries (if any) from original.
        original = libtavern.envelope.Envelope()
        original.loadmongo(mongo_id=self.get_argument("regarding"))
        if 'attachments' in original.dict['envelope']['payload']:
            e.payload.dict['attachments'] = original.dict['envelope']['payload']['attachments']

        res = self.sign_and_deliver(envelope=e)
        if res:
            self.redirect(server.url_for(envelope=e))
        else:
            return "Oh Noes!"
            self.write("Failure to insert message.")

class UploadAttachmentHandler(UploadMessageHandler):

    @webbase.BaseTornado.requires_acct
    def post(self):
        """Receive a POST request containing a file from JS, and return the JSON formatted reply it's expecting."""

        # If there are any files that were sent along with the envelope, save them out.
        self.receive_files()

        # Send a JSON formatted reply to the JS upload-handler if necessary.
        details = []
        for file in self.request.files:
            detail = {}
            detail['name'] = file.name
            detail['hash'] = file.sha
            detail['size'] = file.filesize
            detail['content_type'] = file.mimetype
            detail['url'] = server.serversettings.settings['webtav']['downloads_url'] + file.sha
            details.append(detail)
        details_json = libtavern.utils.to_json(details)
        self.set_header("Content-Type", "application/json")
        self.write(details_json)
        return

class UploadPrivateMessageHandler(UploadMessageHandler):
    """Receive text, encrypt, send to dest."""

    @webbase.BaseTornado.requires_acct
    def post(self):

        # If there are any files that were sent along with the envelope, save them out.
        self.receive_files()

        e = libtavern.envelope.Envelope()
        e.payload.dict['formatting'] = "markdown"
        e.payload.dict['class'] = "privatemessage"
        e.payload.dict['to'] = self.get_argument("regarding")

        # Give a new key as the replyto, so that even if a key leaks, you only lose THAT message.
        single_use_key = self.user.get_pmkey()
        single_use_key.unlock(self.user.passkey)
        e.payload.dict['author'] = {}
        e.payload.dict['author']['replyto'] = single_use_key.pubkey
        e.payload.dict['author']['friendlyname'] = self.user.UserSettings['friendlyname']

        # We'll use our Envelope as a wrapper, and create a whole second message inside of it.
        enc = libtavern.envelope.Envelope()
        enc.payload.dict['formatting'] = "markdown"
        enc.payload.dict['class'] = 'message'
        enc.payload.dict['topic'] = "Private Message" # This is ignored
        enc.payload.dict['subject'] = self.get_argument("subject")
        enc.payload.dict['body'] = self.get_argument("body")
        if self.get_argument("regarding", None):
            enc.payload.dict['regarding'] = self.get_argument("regarding")

        if self.request.files:
            enc.payload.dict['attachments'] = []
            for file in self.request.files:
                enc.payload.dict['attachments'].append(file.sha)

        # Sign the inner-message
        enc.addStamp(stampclass='author',friendlyname=self.user.UserSettings['friendlyname'],keys=self.user.Keys['master'],passkey=self.user.passkey)

        # Encrypt the inner envelope, store in outer env.
        e.payload.dict['encrypted'] = single_use_key.encrypt(encryptstring=enc.text(),encrypt_to=e.payload.dict['to'])
        e.addStamp(stampclass='author',friendlyname=self.user.UserSettings['friendlyname'],keys=self.user.Keys['master'],passkey=self.user.passkey)
        self.server.receive_envelope(env=e)
        self.redirect("/pms")


def main():
    """
    Starts and runs the Python component of the Tavern web interface.
    You are NOT supposed to connect to Tornado directly, connections MUST go through Nginx.
    Nginx will connect to tornado through a domain socket.
    """

    # Define our App
    # Set up Command Line Parsing
    parser = optparse.OptionParser(add_help_option=False, description="The Tavern web interface")
    parser.add_option("-v", "--verbose", dest="verbose", action="count", default=0,
                      help="Set loglevel. Use more than once to log extra stuff (3 max)")
    parser.add_option("-s", "--socket", action="store", dest="socket", default=None,
                      help="Location of Unix Domain Socket to listen on")

    parser.add_option("-?", "--help", action="help",
                      help="Show this helpful message.")

    (options, args) = parser.parse_args()

    if options.socket is None:
        print("Requires Unix Socket file destination :/ ")
        sys.exit(0)


    # Create the Tavern server. This is the main interop class for dealing with Tavern.
    # We then start the server, which creates DB connections, fires up threads to create keys, etc.
    server = libtavern.server.Server()
    server.start()

    # Specify the settings which are not designed to be overwritten.
    tornado_settings = {
        "template_path": "webtav/themes",
        "autoescape": "xhtml_escape",
        "ui_modules": webtav.uimodules,
        "xsrf_cookies": True,
        # SSI requires that gzip is disabled in Tornado.
        "gzip": False,
        "cookie_secret": server.serversettings.settings['webtav']['cookie_secret']
    }
    flask_settings = {}

    # Update the settings dicts for both engines
    tornado_settings.update(server.serversettings.settings['webtav']['tornado'])
    flask_settings.update(server.serversettings.settings['webtav']['flask'])


    # Parse -v, -vvv, etc for verbosity, starting with the level in settings.
    # Parse -v for INFO, -vv for DEBUG, etc
    if options.verbose > 0:
        loglevel = server.logger.getEffectiveLevel() - (options.verbose * 10)
        if loglevel < 1:
            loglevel = 1
        server.logger.setLevel(loglevel)

        # Debug
        if loglevel <= 10:
            tornado_settings['compiled_template_cache'] = False
            tornado_settings['autoreload'] = True
            tornado_settings['serve_traceback=True'] = True
            flask_settings['DEBUG'] = True

    # Create an instance of Flask, so we can add it to the Tornado routing table, below.
    flask_app = flask.Flask(__name__)
    flask_app.config.update(flask_settings)
    flask_app.add_url_rule('/new/message', view_func=UploadMessageHandler.as_view('UploadMessageHandler'))
    flask_app.add_url_rule('/new/reply', view_func=UploadMessageReplyHandler.as_view('UploadMessageReplyHandler'))
    flask_app.add_url_rule('/new/attachment', view_func=UploadAttachmentHandler.as_view('UploadAttachmentHandler'))
    flask_app.add_url_rule('/new/pm', view_func=UploadPrivateMessageHandler.as_view('UploadPrivateMessageHandler'))
    flask_app.add_url_rule('/new/revision', view_func=UploadMessageRevisionHandler.as_view('UploadMessageRevisionHandler'))
    flask_wsgi = tornado.wsgi.WSGIContainer(flask_app)
    flask_wsgi.port = server.serversettings.settings['webtav']['port']
    paths = [
            (r"/", EntryHandler),
            (r"/__xsrf", XSRFHandler),

            # Things that effect the Topic
            # /t/TopicName
            (r"/t/(.*)/new", NewMessageHandler),
            (r"/t/(.*)/settings", TopicPropertiesHandler),

            # Things that effect a Message within a Topic
            # /t/TopicName/Subject/UUID/foo
            (r"/t/(?:.*)/(?:.*)/(.*)/history", MessageHistoryHandler),
            (r"/t/(?:.*)/(?:.*)/(.*)/reply", NewReplyHandler),
            (r"/t/(?:.*)/(?:.*)/(.*)", MessageHandler),
            (r"/t/(.*)", TopicHandler),

            (r"/all/saved", AllSavedHandler),
            (r"/all", AllMessagesHandler),

            (r"/siteindex", SiteIndexHandler),
            (r"/sitemap/m/(\d+)", SitemapMessagesHandler),

            (r"/s/(.*)", SiteContentHandler),


            (r"/showtopics/(.*)", ShowAllTopicsHandler),
            (r"/showtopics", ShowAllTopicsHandler),
            # (r"/showprivates", ShowPrivatesHandler),
            # (r"/privatem/(.*)", ShowPrivatesHandler),

            # (r"/attachment/(.*)", AttachmentHandler),
            (r"/u/(.*)", UserHandler),
            # (r"/edit/(.*)", EditMessageHandler),
            # (r"/reply/(.*)/(.*)", ReplyHandler),
            # (r"/reply/(.*)", ReplyHandler),
            # (r"/pm/(.*)", NewPrivateMessageHandler),
            (r"/register", RegisterHandler),
            (r"/login", LoginHandler),
            # (r"/changepassword", ChangepasswordHandler),
            (r"/logout", LogoutHandler),


            # (r"/vote", RatingHandler),
            # (r"/usertrust", UserTrustHandler),
            # (r"/usernote", UserNoteHandler),

            # (r"/changesetting/(.*)/(.*)", ChangeSingleSettingHandler),
            # (r"/changesetting/(.*)", ChangeSingleSettingHandler),
            # (r"/changesettings", ChangeManySettingsHandler),

            # (r"/rss/(.*)/(.*)", RSSHandler),

            (r"/avatar/(.*)", AvatarHandler),
            # (r"/binaries/(.*)/(.*)", BinariesHandler),
            # (r"/binaries/(.*)", BinariesHandler)
            (r"/new/message", webbase.FlaskHandler, dict(fallback=flask_wsgi)),
            (r"/new/attachment", webbase.FlaskHandler, dict(fallback=flask_wsgi)),
            (r"/new/pm", webbase.FlaskHandler, dict(fallback=flask_wsgi)),
            (r"/new/revision", webbase.FlaskHandler, dict(fallback=flask_wsgi)),
            (r"/new/reply", webbase.FlaskHandler, dict(fallback=flask_wsgi)),
            (r".*", CatchallHandler),
            ]

    # We want to create two application handlers inside webtav.
    # One for Tornado, and one for Flask. This allows us to send requests to either.

    tornado_app = tornado.web.Application(handlers=paths,**tornado_settings)
    flask_app.tornado = tornado_app

    # socket timeout 10s
    socket.setdefaulttimeout(10)

    http_server = tornado.httpserver.HTTPServer(tornado_app)
    unix_socket = tornado.netutil.bind_unix_socket(options.socket)
    http_server.add_socket(unix_socket)

    server.logger.debug("Started a webtav worker using socket on port " + str(options.socket))
    server.logger.info("Tavern is ready. Connect to Tavern on port " + str(server.serversettings.settings['webtav']['port'])+  ".")
    tornado.ioloop.IOLoop.instance().start()
if __name__ == "__main__":
    main()

