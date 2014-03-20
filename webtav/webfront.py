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

import webtav.webbase as webbase
from webtav.webbase import weberror
import webtav.uimodules

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.escape


class EntryHandler(webbase.BaseHandler):
    def get(self):
        """A simple redirect, that will redirect people from / to a FAQ.

        Currently, this redirects everyone.
        Eventually, it may give a different experience for first-time visitors.
        """
        self.redirect('/t/sitecontent',permanent=False)

class MessageHandler(webbase.BaseHandler):
    def get(self,*args):
        """Retrieve and display a message."""

        # The messageid should always be the last thing passed in.
        # We can get here either via /m/uuid or /t/topic/subject/uuid
        if len(args) > 3:
            raise weberror(short='Too many directories',long='The URL you are trying to load is too many directories deep. Perhaps a copy/paste error?',code=404)
        messageid = args[-1]

        messagesenvelope = self.server.db.unsafe.find_one('envelopes', {'envelope.local.payload_sha512': messageid})

        if messagesenvelope is None:
            raise weberror(short="Can't find that message.", long="I'm sorry, but we just can't find the message you're looking for. ;(",code=404,log='Looking for ' + str(messageid))

        self.displayenvelope = libtavern.envelope.Envelope()
        self.displayenvelope.loaddict(messagesenvelope)

        self.topic = libtavern.topic.Topic(topic=self.displayenvelope.dict['envelope']['payload']['topic'])
        self.canon = self.server.url_for(envelope=self.displayenvelope)
        self.title = self.displayenvelope.dict['envelope']['payload']['subject']

        self.render('View-showmessage.html')

class MessageHistoryHandler(webbase.BaseHandler):
    def get(self, messageid, topic=None, short_name=None):
        """Display the various edits to a message."""

        e = libtavern.envelope.Envelope()
        if not e.loadmongo(messageid):
            raise weberror(short="That message's history can't be found :(",
                                  long="I'm terribly sorry, but I can't find any history for the message that's been requested.")

        # Get the original message
        if isinstance(e.payload, libtavern.envelope.Envelope.Message):
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

        self.edits = edits
        self.displayenvelope = original
        self.topic = libtavern.topic.Topic(self.displayenvelope.dict['envelope']['payload']['topic'])
        self.canon = self.server.url_for(envelope=self.displayenvelope)
        self.title = "History for " + self.displayenvelope.dict['envelope']['payload']['subject']

        self.render('View-messagehistory.html')


class TopicHandler(webbase.BaseHandler):
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
                Click the [New Message]("""+self.server.url_for(topic=self.topic) + '/newmessage' +""" "Post Something!") button, and get started.
                We're rooting you.""")

        self.render('View-showmessage.html')

class AllMessagesHandler(webbase.BaseHandler):
    def get(self):
        """
        Display all messages.
        """
        self.topic = libtavern.topic.Topic()
        self.title = "Tavern - All Messages"
        self.canon = self.server.url_for(topic=self.topic)

        self.specialtopic = True

        if self.topic.count() < 1:
            self.displayenvelope = self.server.error_envelope(
                subject="Welcome to Tavern!",
                topic="None",
                body="""This Tavern server has __NO__ messages posted yet.
                If it's public, it should sync up with some other servers soon.
                If not, click the [New Message]("""+self.server.url_for(topic=self.topic) + '/newmessage'+""" "Post Something!") button, and get things started.""")


        self.render('View-showmessage.html')

class AllSavedHandler(webbase.BaseHandler):
    def get(self):
        """
        Display all messages.
        """
        self.topic = libtavern.topic.Topic()
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




class ShowAllTopicsHandler(webbase.BaseHandler):
    """Show every known topic"""
    def get(self):
        self.title = "List of all topics"

        if self.after is None:
            limit = 1000
            skip = 0
        else:
            limit = self.after + 1000
            skip = self.after

        alltopics = Topic.toptopics(limit=limit, skip=skip,counts=True)
        self.render('View-showtopics.html',topics=alltopics)

class TopicPropertiesHandler(webbase.BaseHandler):
    """Show Properties for a topic"""
    def get(self,topic):
        self.topic = libtavern.topic.Topic(topic)
        self.title = "Properties for " + self.topic.name

        # Get a list of the most popular mods
        mods = []
        for mod in self.server.db.unsafe.find('modlist', {'_id.topic': libtavern.topic.sorttopic(topic)}, sortkey='value.trust', sortdirection='descending'):
            mods.append(mod)
        self.render('View-topicprefs.html',mods=mods)


class SiteContentHandler(webbase.BaseHandler):
    """Displays site content, such as FAQ, Ettiquite, etc, without replies or other chrome."""
    def get(self,message):
        envelope = self.server.db.unsafe.find_one(
            'envelopes', {'envelope.local.payload_sha512': client_message_id})

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

class RegisterHandler(webbase.BaseHandler):
    """
    Register a new user for the site.
    """
    def get(self):
        self.title = "Register for a new account"
        self.render('registerform.html')

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
            users_with_this_email = self.server.db.safe.find('users',{"email": client_email.lower()})
            if len(users_with_this_email) > 0:
                self.write(
                    "I'm sorry, this email address has already been used.")
                return

        u = User()
        if u.load_mongo_by_username(username=client_newuser) is not False:
            self.write("I'm sorry, this username has already been taken.")
            return
        else:
    #Generate the user
            self.user.generate(AllowGuestKey=False,
                               username=client_newuser.lower(), password=client_newpass)
            self.user.lastauth = int(time.time())

            if client_email is not None:
                self.user.email = client_email.lower()

            self.user.savemongo()

    #Save the passkey out to a separate cookie.
            self.set_secure_cookie("tavern_passkey", self.user.Keys['master'].get_passkey(
                client_newpass), httponly=True, expires_days=999)

            self.setvars()
            bottle.redirect("/")


# def LoginHandler_get(slug=None):
#     self.getvars()
#     self.write(self.render_string('header.html',
#                title="Login to your account", rsshead=None, type=None))
#     self.write(self.render_string('loginform.html', slug=slug))
#     self.write(self.render_string('footer.html'))


# def LoginHandler_post():
#     self.getvars()
#     self.write(self.render_string('header.html',
#                title='Login to your account', rsshead=None, type=None))

#     successredirect = '/'
#     client_username = self.get_argument("username")
#     client_password = self.get_argument("pass")
#     if 'slug' in self.request.arguments:
#         slug = self.get_argument("slug")
#         sluglookup = self.server.db.unsafe.find_one('redirects', {'slug': slug})
#         if sluglookup is not None:
#             if sluglookup['url'] is not None:
#                 successredirect = sluglookup['url']

#     u = User()
#     if u.load_mongo_by_username(username=client_username.lower()):
# The username exists.

#         if u.verify_password(client_password):
#             self.user = u
# You are successfully Authenticated.

#             self.clear_cookie('tavern_passkey')
#             self.set_secure_cookie(
#                 "tavern_passkey",
#                 self.user.Keys['master'].get_passkey(client_password),
#                 httponly=True,
#                 expires_days=999)
#             self.user.lastauth = int(time.time())

#             self.setvars()
#             self.server.logger.debug("Login Successful.")
#             bottle.redirect(successredirect)
#         else:
#             self.server.logger.debug("Username/password fail.")
# bottle.redirect("http://Google.com")


# def LogoutHandler_post():
#     self.clear_all_cookies()
#     bottle.redirect("/")


# def ChangepasswordHandler_get():
#     self.getvars()

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


class UserHandler(webbase.BaseHandler):
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

#     e.payload.dict['author'] = OrderedDict()
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

#     e.payload.dict['author'] = OrderedDict()
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


# def NewmessageHandler_get(topic=None):
#     self.getvars()
#     self.write(self.render_string('header.html',
#                title="Post a new message", rsshead=None, type=None))
#     self.write(self.render_string('newmessageform.html', topic=topic))
#     self.write(self.render_string('footer.html'))
#     self.finish(divs=['wrappertable'])


# """Where envelopes POST."""


# def ReceiveEnvelopeHandler_options(regarding=None):
#     self.set_header('Access-Control-Allow-Methods',
#                     'OPTIONS, HEAD, GET, POST, PUT, DELETE')
#     self.set_header('Access-Control-Allow-Origin', '*')


# def ReceiveEnvelopeHandler_get(topic=None, regarding=None):
#     bottle.redirect('/')


# def ReceiveEnvelopeHandler_post(flag=None):
#     self.getvars(AllowGuestKey=False)

#     filelist = []

# We might be getting files either through nginx, or through directly.
# If we get the file through Nginx, parse out the arguments.
#     for argument in self.request.arguments:
#         if (argument.startswith("attached_file") and argument.endswith('.path')) or (argument == 'files[].path'):
#             individual_file = {}
#             individual_file['basename'] = argument.rsplit('.')[0]
#             individual_file['clean_up_file_afterward'] = True
#             individual_file['filename'] = self.get_argument(
#                 individual_file['basename'] + ".name")
#             individual_file['content_type'] = self.get_argument(
#                 individual_file['basename'] + ".content_type")
#             individual_file['path'] = self.get_argument(
#                 individual_file['basename'] + ".path")
#             individual_file['size'] = self.get_argument(
#                 individual_file['basename'] + ".size")

#             fs_basename = os.path.basename(individual_file['path'])
#             individual_file['fullpath'] = self.server.serversettings.settings[
#                 'upload-dir'] + "/" + fs_basename

#             individual_file['filehandle'] = open(
#                 individual_file['path'], 'rb+')
#             hashname = str(individual_file['basename'] + '.sha512')

# Nginx should give us the SHA512 hash, but if not, calc it.
#             if hashname in self.request.arguments:
#                 individual_file['hash'] = self.get_argument(
#                     individual_file['basename'] + ".sha512")
#             else:
#                 print("Calculating Hash in Python. Nginx should do this.")
#                 SHA512 = hashlib.sha512()
#                 while True:
#                     buf = individual_file['filehandle'].read(0x100000)
#                     if not buf:
#                         break
#                     SHA512.update(buf)
#                 individual_file['hash'] = SHA512.hexdigest()
#             individual_file['filehandle'].seek(0)
#             filelist.append(individual_file)

# If we get files directly, calculate what we need to know.
#     for file_field in self.request.files:
#         for individual_file in self.request.files[file_field]:

#             individual_file['clean_up_file_afterward'] = False
#             individual_file['filehandle'] = io.BytesIO()
#             individual_file['filehandle'].write(individual_file['body'])
#             individual_file['size'] = len(individual_file['body'])
#             SHA512 = hashlib.sha512()
#             while True:
#                 buf = individual_file['filehandle'].read(0x100000)
#                 if not buf:
#                     break
#                 SHA512.update(buf)
#             individual_file['filehandle'].seek(0)
#             SHA512.update(individual_file['body'])
#             individual_file['hash'] = SHA512.hexdigest()
#             individual_file['filehandle'].seek(0)
#             filelist.append(individual_file)

#     envelopebinarylist = []

# Attach the files that are actually here, submitted alongside the
# message.
#     for attached_file in filelist:
# All the same, let's strip out all but the basename.
#         self.server.logger.debug("Dealing with File " + attached_file['filename']
#                                  + " with hash " + attached_file['hash'])
#         if not self.server.bin_GridFS.exists(filename=attached_file['hash']):
#             attached_file['filehandle'].seek(0)
#             imagetype = imghdr.what(
#                 'ignoreme', h=attached_file['filehandle'].read())
#             acceptable_images = ['gif', 'jpeg', 'jpg', 'png', 'bmp']
#             print(imagetype)
#             if imagetype in acceptable_images:
#                 attached_file['filehandle'].seek(0)
# If it's an image, open and re-save to strip EXIF data.
# Do so here, rather than in server, so that server->server
# messages aren't touched
#                 Image.open(attached_file['filehandle']).save(
#                     attached_file['filehandle'], format=imagetype)
#             attached_file['filehandle'].seek(0)
#             self.server.bin_GridFS.put(
#                 attached_file['filehandle'],
#                 filename=attached_file['hash'],
#                 content_type=individual_file['content_type'])
#         self.server.logger.debug("Creating Message")
# Create a message binary.
#         mybinary = Envelope.binary(sha512=attached_file['hash'])
# Set the Filesize. Clients can't trust it, but oh-well.
#         print('estimated size : ' + str(attached_file['size']))
#         mybinary.dict['filesize_hint'] = attached_file['size']
#         mybinary.dict['content_type'] = attached_file['content_type']
#         mybinary.dict['filename'] = attached_file['filename']
#         envelopebinarylist.append(mybinary.dict)

# Don't keep spare copies on the webservers
#         attached_file['filehandle'].close()
#         if attached_file['clean_up_file_afterward'] is True:
#             os.remove(attached_file['fullpath'])

# Support the Javascript upload handler.
# return the JSON formatted reply it's looking for
#     if flag == "fileonly":
#         details = []
#         for attached_file in filelist:
#             detail = {}
#             detail['name'] = attached_file['filename']
#             detail['hash'] = attached_file['hash']
#             detail['size'] = attached_file['size']
#             detail['content_type'] = attached_file['content_type']

#             detail['url'] = self.server.serversettings.settings[
#                 'downloads_url'] + attached_file['hash']
#             details.append(detail)
#         details_json = json.dumps(details, separators=(',', ':'))
#         self.set_header("Content-Type", "application/json")
#         print(details_json)
#         self.write(details_json)
#         return

# Add the binaries which are only referenced, not multipart posted.
# This is not unusual - The jQuery uploaded will upload them separately, for example.

#     for argument in self.request.arguments:
#         if argument.startswith("referenced_file") and argument.endswith('_name'):
#             r = re.compile('referenced_file(.*?)_name')
#             m = r.search(argument)
#             binarycount = m.group(1)
#             mybinary = Envelope.binary(sha512=self.get_argument(
#                 'referenced_file' + binarycount + '_hash'))
#             mybinary.dict['filesize_hint'] = self.get_argument(
#                 'referenced_file' + binarycount + '_size')
#             mybinary.dict['content_type'] = self.get_argument(
#                 'referenced_file' + binarycount + '_contenttype')
#             mybinary.dict['filename'] = self.get_argument(
#                 'referenced_file' + binarycount + '_name')
#             envelopebinarylist.append(mybinary.dict)

# Now that we have the file handled.. (Whew!) .. Let's do the Envelope
# Pull in our Form variables.
#     client_body = self.get_argument("body", None)
#     client_topic = self.get_argument("topic", None)
#     client_subject = self.get_argument("subject", None)

#     client_to = self.get_argument("to", None)
#     client_regarding = self.get_argument("regarding", None)

#     e = libtavern.envelope.Envelope()
#     e.payload.dict['formatting'] = "markdown"

#     if flag == 'message':
#         e.payload.dict['class'] = "message"
#         if client_topic is not None:
#             e.payload.dict['topic'] = client_topic
#         if client_subject is not None:
#             e.payload.dict['subject'] = client_subject
#         if client_body is not None:
#             e.payload.dict['body'] = client_body

#         if envelopebinarylist:
#             e.payload.dict['binaries'] = envelopebinarylist

#         e.payload.dict['author'] = OrderedDict()
#         e.payload.dict['author']['replyto'] = self.user.new_posted_key().pubkey
#         e.payload.dict['author'][
#             'friendlyname'] = self.user.friendlyname

#         e.addStamp(
#             stampclass='author',
#             friendlyname=self.user.friendlyname,
#             keys=self.user.Keys['master'],
#             passkey=self.user.passkey)

#     elif flag == 'reply':
#         e.payload.dict['class'] = "message"
#         if client_regarding is not None:
#             e.payload.dict['regarding'] = client_regarding
#             regardingmsg = self.server.db.unsafe.find_one(
#                 'envelopes',
#                 {'envelope.local.payload_sha512': client_regarding})
#             e.payload.dict['topic'] = regardingmsg[
#                 'envelope'][
#                 'payload'][
#                 'topic']
#             e.payload.dict['subject'] = regardingmsg[
#                 'envelope'][
#                 'payload'][
#                 'subject']
#         if client_body is not None:
#             e.payload.dict['body'] = client_body
#         if envelopebinarylist:
#             e.payload.dict['binaries'] = envelopebinarylist

#         e.payload.dict['author'] = OrderedDict()
#         e.payload.dict['author']['replyto'] = self.user.new_posted_key().pubkey

#         e.payload.dict['author'][
#             'friendlyname'] = self.user.friendlyname

#         e.addStamp(
#             stampclass='author',
#             friendlyname=self.user.friendlyname,
#             keys=self.user.Keys['master'],
#             passkey=self.user.passkey)

#     elif flag == 'messagerevision':
#         e.payload.dict['class'] = "messagerevision"
#         if client_body is not None:
#             e.payload.dict['body'] = client_body
#         if client_regarding is not None:
#             e.payload.dict['regarding'] = client_regarding
#             regardingmsg = self.server.db.unsafe.find_one(
#                 'envelopes',
#                 {'envelope.local.payload_sha512': client_regarding})
#             e.payload.dict['topic'] = regardingmsg[
#                 'envelope'][
#                 'payload'][
#                 'topic']
#             e.payload.dict['subject'] = regardingmsg[
#                 'envelope'][
#                 'payload'][
#                 'subject']
#         e.addStamp(
#             stampclass='author',
#             friendlyname=self.user.friendlyname,
#             keys=self.user.Keys['master'],
#             passkey=self.user.passkey)

#     elif flag == 'privatemessage':
# For encrypted messages we want to actually create a whole
# sub-envelope inside of it!

#         single_use_key = self.user.new_posted_key()
#         single_use_key.unlock(self.user.passkey)

#         e.payload.dict['class'] = "privatemessage"
#         touser = Key(pub=client_to)
#         e.payload.dict['to'] = touser.pubkey
#         e.payload.dict['author'] = OrderedDict()
#         e.payload.dict['author']['replyto'] = self.user.new_posted_key().pubkey

#         encrypted_msg = libtavern.envelope.Envelope()
#         encrypted_msg.payload.dict['formatting'] = "markdown"
#         encrypted_msg.payload.dict['body'] = client_body
#         encrypted_msg.payload.dict['class'] = 'privatemessage'

#         if client_regarding is not None:
#             encrypted['regarding'] = client_regarding
#             regardingmsg = self.server.db.unsafe.find_one(
#                 'envelopes',
#                 {'envelope.local.payload_sha512': client_regarding})

# The message we're referencing is likey unreadable due to encryption.
# Pull in it's subject if possible.
#             decrypted_regarding_dict = self.user.decrypt(
#                 regardingmsg['payload']['encrypted'])
#             decrypted_regarding = libtavern.envelope.Envelope()
#             decrypted_regarding.loaddict(decrypted_regarding_dict)

#             encrypted_msg.payload.dict[
#                 'subject'] = decrypted_regarding.payload.dict[
#                 'subject']
#         else:
#             encrypted_msg.payload.dict['subject'] = client_subject

#         if envelopebinarylist:
#             encrypted_msg.payload.dict['binaries'] = envelopebinarylist

#         encrypted_msg.payload.dict['author'] = OrderedDict()
#         encrypted_msg.payload.dict['author']['replyto'] = self.user.new_posted_key().pubkey

#         encrypted_msg.payload.dict['author'][
#             'friendlyname'] = self.user.friendlyname

#         if self.user.include_location or 'include_location' in self.request.arguments:
#             gi = pygeoip.GeoIP('datafiles/GeoLiteCity.dat')
#             ip = self.request.remote_ip

# Don't check from home.
#             if ip == "127.0.0.1":
#                 ip = "8.8.8.8"

#             gir = gi.record_by_name(ip)
#             encrypted_msg.payload.dict['coords'] = str(gir['latitude']) + \
#                 "," + str(gir['longitude'])

# Add stamps to show we're the author (and optionally) we're the
# origin server
#         encrypted_msg.addStamp(
#             stampclass='author',
#             friendlyname=self.user.friendlyname,
#             keys=self.user.Keys['master'],
#             passkey=self.user.passkey)
#         if self.server.serversettings.settings['mark-origin']:
#             encrypted_msg.addStamp(
#                 stampclass='origin',
#                 keys=self.server.ServerKeys,
#                 hostname=self.server.serversettings.settings['hostname'])

# Now that we've created the inner message, convert it to text,
# store it in the outer message.
#         encrypted_pmstr = encrypted_msg.text()

#         e.payload.dict['encrypted'] = single_use_key.encrypt(
#             encrypt_to=touser.pubkey,
#             encryptstring=encrypted_pmstr)

# For all classses of messages-
#     if self.user.include_location or 'include_location' in self.request.arguments:
#         gi = pygeoip.GeoIP('datafiles/GeoLiteCity.dat')
#         ip = self.request.remote_ip

# Don't check from home.
#         if ip == "127.0.0.1":
#             ip = "8.8.8.8"

#         gir = gi.record_by_name(ip)
#         e.payload.dict['coords'] = str(gir['latitude']) + \
#             "," + str(gir['longitude'])

#     if self.server.serversettings.settings['mark-origin']:
#         e.addStamp(
#             stampclass='origin',
#             keys=self.server.ServerKeys,
#             hostname=self.server.serversettings.settings['hostname'])

# Send to the server
#     newmsgid = self.server.receiveEnvelope(env=e)
#     if newmsgid:
#         if client_to is None:
#             if client_regarding is not None:
#                 bottle.redirect('/m/' + self.server.getTopMessage(
#                     newmsgid) + "?jumpto=" + newmsgid, permanent=False)
#             else:
#                 bottle.redirect('/m/' + newmsgid, permanent=False)
#         else:
#             bottle.redirect('/showprivates')
#     else:
#         self.write("Failure to insert message.")


# def ShowPrivatesHandler_get(messageid=None):
#     self.getvars(AllowGuestKey=False)

#     messages = []
#     self.write(self.render_string('header.html',
#                title="Your Private messages", rsshead=None, type=None))

# Construct a list of all current PMs
# for message in self.server.db.unsafe.find('envelopes',
# {'envelope.payload.to': {'$in': self.user.get_pubkeys()}}, limit=10,
# sortkey='value', sortdirection='descending'):

#         if self.user.decrypt(message['envelope']['payload']['encrypted']):
#             unencrypted_str = self.user.decrypt(
#                 message['envelope']['payload']['encrypted'])
#             unencrypted_env = libtavern.envelope.Envelope()
#             unencrypted_env.loadstring(unencrypted_str)
#             unencrypted_env.munge()
#             unencrypted_env.dict['parent'] = message
#             messages.append(unencrypted_env)

# Retrieve a PM to display - Either by id if requested, or top PM if
# not.
#     e = libtavern.envelope.Envelope()
#     if messageid is not None:
#         if not e.loadmongo(messageid):
#             self.write("Can't load that..")
#             return
#         else:
#             if e.dict['envelope']['payload']['to'] not in self.user.get_pubkeys():
#                 print("This is to--")
#                 print(e.dict['envelope']['payload']['to'])
#                 print("Your Keys-")
#                 print(self.user.get_pubkeys())
#                 self.write("This isn't you.")
#                 return
# TODO - Put better error here. self.server.Error?
#         unencrypted_str = self.user.decrypt(
#             e.dict['envelope']['payload']['encrypted'])

#         unencrypted_env = libtavern.envelope.Envelope()
#         unencrypted_env.loadstring(unencrypted_str)
#         unencrypted_env.munge()
#         unencrypted_env.dict['parent'] = e.dict

#         displaymessage = unencrypted_env

#     elif messages:
#         displaymessage = messages[0]
#     else:
#         displaymessage = self.server.error_envelope(
#             "You don't have any private messages yet. Silly goose!")

#     self.write(
#         self.render_string(
#             'header.html',
#             title="Private Messages",
#             rsshead=None,
#             type=None))
#     self.write(
#         self.render_string('show_privates.html', messages=messages, envelope=displaymessage))
#     self.write(self.render_string('footer.html'))


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


# def BinariesHandler_get(binaryhash, filename=None):
#     self.server.logger.info(
#         "The gridfs_nginx plugin is a much better option than this method")
#     self.set_header("Content-Type", 'application/octet-stream')

#     req = self.server.bin_GridFS.get_last_version(filename=binaryhash)
#     self.write(req.read())

class CatchallHandler(webbase.BaseHandler):
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

class AvatarHandler(webbase.BaseHandler):
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


class SiteIndexHandler(webbase.BaseHandler):
    def get(self):
        """
        Return a sitemap index file, which includes all other sitemap files.
        Since each sitemap.xml file can only contain 50K urls, we need to split these.
        """

        max_posts = self.server.serversettings.settings['webtav']['urls_per_sitemap']

        self.topic = libtavern.topic.Topic()

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

class SitemapMessagesHandler(webbase.BaseHandler):
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
        results = server.db.unsafe.find_one('sitemap',{'_id':previous_sitemap})
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
        server.db.unsafe.save('sitemap',results)

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
                      help="Set loglevel. Use more than once to log extra stuff (5 max)")
    parser.add_option("-s", "--socket", action="store", dest="socket", default=None,
                      help="Location of Unix Domain Socket to listen on")

    parser.add_option("-?", "--help", action="help",
                      help="Show this helpful message.")

    (options, args) = parser.parse_args()

    if options.socket is None:
        print("Requires Unix Socket file destination :/ ")
        sys.exit(0)

    # Specify the settings which are not designed to be overwritten.
    tornado_settings = {
        "template_path": "webtav/themes",
        "autoescape": "xhtml_escape",
        "ui_modules": webtav.uimodules,
        "xsrf_cookies": True,
        # SSI requires that gzip is disabled in Tornado.
        "gzip": False,
    }

    # Create the Tavern server. This is the main interop class for dealing with Tavern.
    # We then start the server, which creates DB connections, fires up threads to create keys, etc.
    server = libtavern.server.Server()
    server.start()

    tornado_settings.update(server.serversettings.settings['webtav']['tornado'])
    # Parse -vvvvv for DEBUG, -vvvv for INFO, etc
    if options.verbose > 0:
        loglevel = 100 - (options.verbose * 20)
        if loglevel < 1:
            loglevel = 1
        server.logger.setLevel(loglevel)

        # Debug
        if loglevel <= 20:
            tornado_settings['compiled_template_cache'] = False
            tornado_settings['autoreload'] = True
        # Info
        if loglevel <= 40:
            tornado_settings['serve_traceback=True'] = True


    paths = [
            (r"/", EntryHandler),
            (r"/__xsrf", XSRFHandler),

            (r"/t/(.*)/(.*)/(.*)", MessageHandler),
            (r"/t/(.*)/settings", TopicPropertiesHandler),
            (r"/t/(.*)", TopicHandler),

            (r"/m/(.*)", MessageHandler),
            (r"/mh/(.*)", MessageHistoryHandler),

            (r"/all/saved", AllSavedHandler),
            (r"/all", AllMessagesHandler),

            (r"/siteindex", SiteIndexHandler),
            (r"/sitemap/m/(\d+)", SitemapMessagesHandler),

            (r"/s/(.*)", SiteContentHandler),


            (r"/showtopics", ShowAllTopicsHandler),
            # (r"/showprivates", ShowPrivatesHandler),
            # (r"/privatem/(.*)", ShowPrivatesHandler),

            # (r"/attachment/(.*)", AttachmentHandler),




            (r"/u/(.*)", UserHandler),

            # (r"/newm/(.*)", NewmessageHandler),
            # (r"/newmessage", NewmessageHandler),

            # (r"/edit/(.*)", EditMessageHandler),
            # (r"/reply/(.*)/(.*)", ReplyHandler),
            # (r"/reply/(.*)", ReplyHandler),
            # (r"/pm/(.*)", NewPrivateMessageHandler),

            # (r"/upload/uploadenvelope/(.*)", ReceiveEnvelopeHandler),
            # (r"/uploadenvelope/(.*)", ReceiveEnvelopeHandler),
            # (r"/uploadfile/(.*)", ReceiveEnvelopeHandler),

            (r"/register", RegisterHandler),
            # (r"/login/(.*)", LoginHandler),
            # (r"/login", LoginHandler),
            # (r"/changepassword", ChangepasswordHandler),
            # (r"/logout", LogoutHandler),


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
            (r".*", CatchallHandler),

            ]

    application = tornado.web.Application(handlers=paths,**tornado_settings)

    # socket timeout 10s
    socket.setdefaulttimeout(10)

    http_server = tornado.httpserver.HTTPServer(application)
    unix_socket = tornado.netutil.bind_unix_socket(options.socket)
    http_server.add_socket(unix_socket)

    server.logger.debug("Started a webtav worker using socket on port " + str(options.socket))
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()

