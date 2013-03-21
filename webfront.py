# Copyright 2012 Tavern


import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.escape
import time
import datetime
import socket
import json
import os
from Envelope import Envelope
from collections import OrderedDict
import pymongo
from Server import server
import pygeoip
from keys import *
from User import User
import urllib.parse
from bs4 import BeautifulSoup
import rss
import pprint
import Image
import imghdr
import io
from TopicTool import topictool
from TavernUtils import memorise
import TavernUtils
from ServerSettings import serversettings
from tornado.options import define, options

try:
    from hashlib import md5 as md5_func
except ImportError:
    from md5 import new as md5_func


class BaseHandler(tornado.web.RequestHandler):

    """
    The BaseHandler is the baseclass for all objects in the webserver.
    It is not expected to ever be instantiated directly.
    It's main uses are:
        * Handle Cookies/logins
        * Allow modules to update just PARTS of the page
    """

    def __init__(self, *args, **kwargs):
        """
        Wrap the default RequestHandler with extra methods
        """
        self.html = ""
        super(BaseHandler, self).__init__(*args, **kwargs)

        # Add in a random fortune
        self.set_header("X-Fortune", str(server.fortune.random()))
        # Do not allow the content to load in a frame.
        # Should help prevent certain attacks
        self.set_header("X-FRAME-OPTIONS", "DENY")
        # Don't try to guess content-type.
        # This helps avoid JS sent in an image.
        self.set_header("X-Content-Type-Options", "nosniff")
        self.fullcookies = {}
        for cookie in self.request.cookies:
            self.fullcookies[cookie] = self.get_cookie(cookie)


    
    @memorise(parent_keys=['fullcookies', 'user.UserSettings'], ttl=serversettings.settings['cache']['templates']['seconds'], maxsize=serversettings.settings['cache']['templates']['size'])
    def render_string(self, template_name, **kwargs):
        """
        Overwrite the default render_string to ensure the "server" variable is always available to templates
        """
        args = dict(
            server=server,
            browser=self.browser,
            request=self.request,
            user=self.user,
            serversettings=serversettings
        )
        args.update(kwargs)
        theme = 'default'
        # Only accept valid templates
        if 'theme' in self.user.UserSettings:
            if self.user.UserSettings['theme'] in server.availablethemes:
                theme = self.user.UserSettings['theme']
        return tornado.web.RequestHandler.render_string(self, theme + '/' + template_name, **args)

    def write(self, html):
        if hasattr(html, 'decode'):
            self.html += html.decode('utf-8')
        else:
            self.html += html

    def gettext(self):
        ptext = ""
        for a in self.pagetext:
            ptext = ptext + a
        self.write(ptext)

    def finish(self, divs=['html'], message=None):
        """
        Pulls in appropriate divs and serves them out via JS if possible.
        This saves bits, and keeps the columns as you left them.
        """

        # If they ask for the JS version, we'll calculate it.
        if "js" in self.request.arguments:

            # Send the header information with the new name, then each div, then the footer.
            super(BaseHandler, self).write(self.getjssetup())
            for div in divs:
                super(BaseHandler, self).write(self.getjselement(div))
            super(BaseHandler, self).write(self.getjsfooter())


        # GetOnly is used to request only specific divs.
        # And example is requesting the message reply inline.

        elif "getonly" in self.request.arguments:
            for div in divs:
                super(BaseHandler, self).write(self.getdiv(div))

        # If we're here, send the whole page as a regular view.
        else:
            super(BaseHandler, self).write(self.html)

        if "js" in self.request.arguments:
            self.set_header("Content-Type", "application/json")

        super(BaseHandler, self).finish(message)

    @memorise(parent_keys=['html'], ttl=serversettings.settings['cache']['templates']['seconds'], maxsize=serversettings.settings['cache']['templates']['size'])
    def getdiv(self, element):
        print("getting" + element)
        soup = BeautifulSoup(self.html)
        soupyelement = soup.find(id=element)
        soupytxt = ""
        if soupyelement is not None:
            for child in soupyelement.contents:
                soupytxt += str(child)
        return soupytxt


    @memorise(parent_keys=['request.uri', 'html'], ttl=serversettings.settings['cache']['templates']['seconds'], maxsize=serversettings.settings['cache']['templates']['size'])
    def getjssetup(self):
        jsvar = self.request.uri.find("js=")
        if jsvar > -1:
            #This should always be true
            #But Are there other params?
            nextvar = self.request.uri.find("&", jsvar)
            if nextvar > 0:
                #There are Additional Variables in this URL
                finish = "?" + self.request.uri[nextvar +
                                                1:len(self.request.uri)]
            else:
                #There are no other variables. Delete until End of string
                finish = ""

            modifiedurl = self.request.uri[0:
                                           self.request.uri.find("js=") - 1] + finish

            #Also strip out the "timestamp" param
            jsvar = modifiedurl.find("timestamp=")
            if jsvar > -1:
                #This should always be true
                #But Are there other params?
                nextvar = modifiedurl.find("&", jsvar)
                if nextvar > 0:
                    #There are Additional Variables in this URL
                    finish = "?" + modifiedurl[nextvar + 1:len(modifiedurl)]
                else:
                    #There are no other variables. Delete until End of string
                    finish = ""
                modifiedurl = modifiedurl[0:modifiedurl.find("timestamp=") - 1] + finish

        try:
            soup = BeautifulSoup(self.html)
        except:
            print('malformed data in BeautifulSoup')
            raise
        if soup.html is not None:
            # Need to escape, since BS4 turns this back into evil html.
            newtitle = tornado.escape.xhtml_escape(soup.html.head.title.string.rstrip().lstrip())
        else:
            print("No Title?!??!?!")
            print(self.html)
            newtitle = "Error"

        ret =  '''
                var tavern_setup = function()
                {
                    var stateObj =
                    {
                        title: document.title,
                        url: window.location.pathname
                    };
                    document.title = "''' + newtitle + ''' ";
                    if (typeof history.pushState !== "undefined")
                    {
                        window.history.pushState(stateObj, "","''' + modifiedurl + '''");
                    }
                };
                '''

        return (ret)

    @memorise(parent_keys=['request.uri', 'html'], ttl=serversettings.settings['cache']['templates']['seconds'], maxsize=serversettings.settings['cache']['templates']['size'])
    def getjselement(self, element):
        """
        Get the element text, remove all linebreaks, and escape it up.
        Then, send that as a document replacement
        Also, rewrite the document history in the browser, so the URL looks normal.
        """

        try:
            soup = BeautifulSoup(self.html)
        except:
            print('malformed data in BeautifulSoup')
            raise
        soupyelement = soup.find(id=element)
        soupytxt = ""
        if soupyelement is not None:
            for child in soupyelement.contents:
                soupytxt += str(child)

        escapedtext = soupytxt.replace("\"", "\\\"")
        escapedtext = escapedtext.replace("\n", "")

        return ('document.getElementById("' + element + '").innerHTML="' + escapedtext + '";')

    def getjsfooter(self):
        # The stuff at the bottom of the JS file.
        ret =   '''
                jQuery('#spinner').hide();
                tavern_setup();
                tavern_setup =  null;
                ''' + server.cache['instance.js']
        return(ret)


    def chunks(self, s, n):
        """
        Produce `n`-character chunks from `s`.
        """
        for start in range(0, len(s), n):
            yield s[start:start + n]

    def setvars(self):
        """
        Saves out the current userobject to a cookie, or series of cookies.
        These are encrypted using the built-in Tornado cookie encryption.
        """
        # Zero out the stuff in 'local', since it's big.
        usersettings = self.user.UserSettings

        # Create the Cookie value, and sign it.
        signed = self.create_signed_value("tavern_preferences", json.dumps(
            usersettings, separators=(',', ':')))

        # Chunk up the cookie value, so we can spread across multiple cookies.
        numchunks = 0
        for chunk in self.chunks(signed, 3000):
            numchunks += 1
            self.set_cookie("tavern_preferences" + str(
                numchunks), chunk, httponly=True, expires_days=999)
        self.set_secure_cookie("tavern_preferences_count", str(
            numchunks), httponly=True, expires_days=999)
        server.logger.info("numchunks + " + str(numchunks))

    def recentauth(self, seconds=300):
        """
        Ensure the user has authenticated recently.
        To be used for things like change-password.
        """
        currenttime = int(time.time())

        if 'lastauth' in self.user.UserSettings:
            if currenttime - self.user.UserSettings['lastauth'] > seconds:
                print("User has not logged in recently. ;( ")
                return False
            else:
                print("Last login - " + str(currenttime -
                      self.user.UserSettings['lastauth']) + " seconds ago")
                return True
        else:
            # The user has NEVER logged in.
            print("Never Logged in Before")
            return True

    def getvars(self, ensurekeys=False):
        """
        Retrieve the basic user variables out of your cookies.
        """

        self.user = User()
        if self.get_secure_cookie("tavern_preferences_count") is not None:
            # Restore the signed cookie, across many chunks
            restoredcookie = ""
            for i in range(1, 1 + int(self.get_secure_cookie("tavern_preferences_count"))):
                restoredcookie += self.get_cookie(
                    "tavern_preferences" + str(i))

            # Validate the cookie, and load if it passes
            decodedcookie = self.get_secure_cookie(
                "tavern_preferences", value=restoredcookie)
            if not isinstance(decodedcookie, str):
                decodedcookie = decodedcookie.decode('utf-8')

            if decodedcookie is not None:
                self.user.load_string(decodedcookie)
            else:
                # We shouldn't get here.
                server.logger.info("Cookie doesn't validate. Deleting...")
                self.clear_cookie('tavern_preferences')
                self.clear_cookie('tavern_preferences1')
                self.clear_cookie('tavern_preferences2')
                self.clear_cookie('tavern_preferences3')
                self.clear_cookie('tavern_preferences_count')
                self.clear_cookie('tavern_passkey')

        # If there isn't already a cookie, make a very basic one.
        # Don't bother doing the keys, since that eats randomness.
        # Not an else, so we can be triggered by corrupt cookie above.
        if self.get_secure_cookie("tavern_preferences_count") is None:
            server.logger.info("Making cookies")
            self.user.generate(skipkeys=True)
            self.setvars()

        # If we've asked to make the keys.. Generate them.
        # This won't overwrite existing values, since user.generate() is additive.
        if ensurekeys == True:
            validkey = False
            if 'encryptedprivkey' in self.user.UserSettings:
                if self.user.UserSettings['encryptedprivkey'] is not None:
                    validkey = True
            if not validkey:
                server.logger.info("Making keys with a random password.")

                # Generate a random password with a random number of characters
                numcharacters = 100 + TavernUtils.randrange(1, 100)
                password = TavernUtils.randstr(numcharacters)
                self.user.generate(skipkeys=False, password=password)

                # Save it out.
                self.setvars()
                self.user.savemongo()
                self.set_secure_cookie('tavern_passkey', self.user.Keys.passkey(password), httponly=True, expires_days=999)
                self.user.passkey = self.user.Keys.passkey(password)

            if not hasattr(self.user, 'passkey'):
                self.user.passkey = self.get_secure_cookie('tavern_passkey')
            if self.user.passkey is None:
                self.user.passkey = self.get_secure_cookie('tavern_passkey')

        # Get the Browser version.
        if 'User-Agent' in self.request.headers:
            ua = self.request.headers['User-Agent']
            self.browser = server.browserdetector.parse(ua)
        # Check to see if we have support for datauris in our browser.
        # If we do, send the first ~10 pages with datauris.
        # After that switch back, since caching the images is likely to be better, if you're a recurrent reader
        if not 'datauri' in self.user.UserSettings:
            if TavernUtils.randrange(1, 10) == 5:
                self.user.UserSettings['datauri'] = False
        if 'datauri' in self.user.UserSettings:
            self.user.datauri = self.user.UserSettings['datauri']
        elif self.browser['ua_family'] == 'IE' and self.browser['ua_versions'][0] < 8:
            self.user.datauri = False
        elif self.browser['ua_family'] == 'IE' and self.browser['ua_versions'][0] >= 8:
            self.user.datauri = True
        else:
            self.user.datauri = True
        if 'datauri' in self.request.arguments:
            if self.get_argument("datauri").lower() == 'true':
                self.user.datauri = True
            elif self.get_argument("datauri").lower() == 'false':
                self.user.datauri = False

        return self.user.UserSettings['username']


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
                                "http://GetTavern.com/message/" + envelope['envelope']['local']['sorttopic'] + '/' + envelope['envelope']['local']['short_subject'] + "/" + envelope['envelope']['payload_sha512'],
                                envelope['envelope']['local']['formattedbody'])
                channel.additem(item)
            self.write(channel.toprettyxml())


class RawMessageHandler(BaseHandler):
    def get(self, message):
        envelope = server.db.unsafe.find_one(
            'envelopes', {'envelope.payload_sha512': message})
        envelope = server.formatEnvelope(envelope)
        self.write(envelope['envelope']['local']['formattedbody'])


class TriPaneHandler(BaseHandler):

    """
    The TriPane Handler is the beefiest handler in the project.
    It renders the main tri-panel interface, and only pushes out the parts that are needed.
    """
    def get(self, param1=None, param2=None, param3=None):
        
        # We want to assign the parameters differently, depending on how many there are.
        # Normally, we'd just say get(action=None,param=None,bullshit=None)
        # But in this scenerio, we want the second param to be the text, if there are three, and have the ID as #3
        # But if there are only two, the second param should be the ID.

        self.getvars()

        # Mark this as None up here, so if it changes we know.
        displayenvelope = None

        # Count up our number of parameters.
        if param3 is None:
            if param2 is None:
                if param1 is None:
                    numparams = 0
                else:
                    numparams = 1
            else:
                numparams = 2
                param2 = tornado.escape.xhtml_escape(
                    urllib.parse.unquote(param2))
        else:
            numparams = 3
            param3 = tornado.escape.xhtml_escape(urllib.parse.unquote(param3))

        #Decide what to do, based on the number of incoming actions.
        if numparams < 2:
            # Defaults all around
            action = "topic"
            topic = "sitecontent"
        else:
            action = param1
            if action == "t" or action == "topic" or action == "topictag":
                action = "topic"
            elif action == "m" or action == "message":
                action = "message"
            else:
                action = "message"
            if action == "message":
                if numparams == 2:
                    messageid = param2
                if numparams == 3:
                    messageid = param3
            elif action == "topic":
                topic = param2

        if "before" in self.request.arguments:
            # Used for multiple pages, because skip() is slow
            # Don't really need xhtml escape, since we're converting to a float
            before = float(self.get_argument('before'))
        else:
            before = None

        if action == "topic":
            divs = ['column2','column3']

            if topic != 'sitecontent':
                canon = "topic/" + topic
                title = topic
            else:
                canon = ""
                title = "Discuss what matters"
            topicEnvelopes = topictool.messages(topic=topic,maxposts=1)

            if len(topicEnvelopes) > 0:
                displayenvelope = topicEnvelopes[0]

        if action == "message":
            # We need both col2 and col3, since the currently active message changes in the col2.
            divs = ['column2', 'column3']

            displayenvelope = server.db.unsafe.find_one('envelopes',
                                                        {'envelope.payload_sha512': messageid})
            if displayenvelope is not None:
                topic = displayenvelope['envelope']['payload']['topic']
                canon = "message/" + displayenvelope['envelope']['local']['sorttopic'] + '/' + displayenvelope['envelope']['local']['short_subject'] + "/" + displayenvelope['envelope']['payload_sha512']
                title = displayenvelope['envelope']['payload']['subject']



        # Detect people accessing via odd URLs, but don't do it twice.
        # Check for a redirected flag.
        if 'redirected' in self.request.arguments:
            redirected = tornado.escape.xhtml_escape(
                self.get_argument("redirected"))
            if redirected == 'true':
                redirected = True
            else:
                redirected = False
        else:
            redirected = None

        if self.request.path[1:] != canon and redirected is None:
            if not "?" in canon:
                canonbubble = "?redirected=true"
            else:
                canonbubble = "&redirected=true"
            server.logger.info(
                "Redirecting URL " + self.request.path[1:] + " to " + canon)
#       self.redirect("/" + canon + canonbubble, permanent=True)
#       self.finish()

        #Gather up all the replies to this message, so we can send those to the template as well
        self.write(self.render_string('header.html', title=title, canon=canon, type="topic", rsshead=displayenvelope['envelope']['payload']['topic']))
        self.write(self.render_string('showmessage.html',
                   envelope=displayenvelope, before=before, topic=topic))
        self.write(self.render_string('footer.html'))

        if action == "message" or action == "topic":
            self.finish(divs=divs)
        else:
            self.finish()


class AllTopicsHandler(BaseHandler):
    def get(self, start=0):
        self.getvars()

        alltopics = []
        for quicktopic in server.db.unsafe.find('topiclist', limit=start + 1000, skip=start, sortkey='value', sortdirection='descending'):
            alltopics.append(quicktopic)

        toptopics = []
        for quicktopic in server.db.unsafe.find('topiclist', limit=10, sortkey='value', sortdirection='descending'):
            toptopics.append(quicktopic)

        self.write(
            self.render_string('header.html', title="List of all Topics",
                               rsshead=None, type=None))
        self.write(self.render_string('alltopics.html',
                   topics=alltopics, toptopics=toptopics))
        self.write(self.render_string('footer.html'))
        #self.finish(divs=['column3'])


class TopicPropertiesHandler(BaseHandler):
    def get(self, topic):
        self.getvars()

        mods = []
        for mod in server.db.unsafe.find('modlist', {'_id.topic': server.sorttopic(topic)}, max_scan=10000, sortkey='value.trust', sortdirection='descending'):
            mod['_id']['moderator_pubkey_sha512'] = hashlib.sha512(
                mod['_id']['moderator'].encode('utf-8')).hexdigest()
            mods.append(mod)

        toptopics = []
        for quicktopic in server.db.unsafe.find('topiclist', limit=10, sortkey='value', sortdirection='descending'):
            toptopics.append(quicktopic)
        subjects = []
        for envelope in server.db.unsafe.find('envelopes', {'envelope.local.sorttopic': server.sorttopic(topic), 'envelope.payload.class': 'message', 'envelope.payload.regarding': {'$exists': False}}, limit=self.user.UserSettings['maxposts']):
            subjects.append(envelope)

        title = "Properties for " + topic
        self.write(self.render_string('header.html', title=title,
                                      rsshead=topic, type="topic"))
        self.write(self.render_string('topicprefs.html', topic=topic,
                   toptopics=toptopics, subjects=subjects, mods=mods))
        self.write(self.render_string('footer.html'))
        self.finish(divs=['column3'])


class SiteContentHandler(BaseHandler):
    def get(self, message):
        self.getvars()
        client_message_id = tornado.escape.xhtml_escape(message)

        envelope = server.db.unsafe.find_one(
            'envelopes', {'envelope.payload_sha512': client_message_id})

        self.write(self.render_string('header.html', title="Tavern :: " + envelope['envelope']['payload']['subject'], canon="sitecontent/" + envelope['envelope']['payload_sha512'], rss="/rss/topic/" + envelope['envelope']['payload']['topic'], topic=envelope['envelope']['payload']['topic']))
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
            'attachments.html', myattach=myattach, preview=preview, attachment=client_attachment_id, stack=stack))
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
            self.user.generate(
                username=client_newuser.lower(), password=client_newpass)
            self.user.UserSettings['lastauth'] = int(time.time())

            if client_email is not None:
                self.user.UserSettings['email'] = client_email.lower()

            self.user.savemongo()

            # Save the passkey out to a separate cookie.
            self.set_secure_cookie("tavern_passkey", self.user.Keys.passkey(
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
                server.logger.info(
                    "Passkey - " + self.user.Keys.passkey(client_password))

                self.clear_cookie('tavern_passkey')
                self.set_secure_cookie("tavern_passkey", self.user.Keys.passkey(client_password), httponly=True, expires_days=999)
                self.user.UserSettings['lastauth'] = int(time.time())

                self.setvars()
                server.logger.info("Login Successful.")
                self.redirect(successredirect)
            else:
                server.logger.info("Username/password fail.")
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
        self.getvars(ensurekeys=True)

        client_newpass = self.get_argument("pass")
        client_newpass2 = self.get_argument("pass2")

        if client_newpass != client_newpass2:
            self.write("I'm sorry, your passwords don't match.")
            return

        client_oldpasskey = self.get_secure_cookie("tavern_passkey")

        # Encrypt the the privkey with the new password
        self.user.changepass(
            oldpasskey=client_oldpasskey, newpass=client_newpass)

        # Set the Passkey, to be able to unlock the Privkey
        self.set_secure_cookie("tavern_passkey", self.user.Keys.passkey(
            password=client_newpass), httponly=True, expires_days=999)

        self.setvars()
        server.logger.info("Password Change Successful.")
        self.redirect("/")


class UserHandler(BaseHandler):
    def get(self, pubkey):
        self.getvars()

        #Unquote it, then convert it to a TavernKey object so we can rebuild it.
        #Quoting destroys the newlines.
        pubkey = urllib.parse.unquote(pubkey)
        pubkey = Keys(pub=pubkey).pubkey

        u = User()
        u.UserSettings['pubkey'] = pubkey
        u.generate(self, skipkeys=True)
        u.UserSettings['author_wordhash'] = server.wordlist.wordhash(pubkey)

        envelopes = []
        for envelope in server.db.safe.find('envelopes', {'envelope.payload.author.pubkey': pubkey, 'envelope.payload.class': 'message'}, sortkey='envelope.local.time_added', sortdirection='descending'):
            envelopes.append(envelope)

        self.write(self.render_string('header.html', title="User page",
                                      rsshead=None, type=None))

        if pubkey == self.user.Keys.pubkey:
            if not 'author_wordhash' in self.user.UserSettings:
                self.user.UserSettings['author_wordhash'] = u.UserSettings[
                    'author_wordhash']
            self.write(self.render_string('mysettings.html'))

        self.write(self.render_string(
            'userpage.html', me=self.user, thatguy=u, envelopes=envelopes))

        self.write(self.render_string(
            'showuserposts.html', envelopes=envelopes, thatguy=u))

        self.write(self.render_string('footer.html'))


class ChangeManySettingsHandler(BaseHandler):
    def post(self):
        self.getvars(ensurekeys=True)

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

        server.logger.info("set")
        if "js" in self.request.arguments:
            self.finish(divs=['column3'])
        else:
            keyurl = ''.join(self.user.Keys.pubkey.split())
            self.redirect('/user/' + keyurl)


class ChangeSingleSettingHandler(BaseHandler):

    def post(self, setting, option=None):
        self.getvars(ensurekeys=True)
        redirect = True
        if setting == "followtopic":
            self.user.followTopic(
                self.get_argument("topic"))
        elif setting == "unfollowtopic":
            self.user.unFollowTopic(
                self.get_argument("topic"))
        elif setting == "showembeds":
            self.user.UserSettings['allowembed'] = 1
            server.logger.info("allowing embeds")
            if option == 'ajax':
                self.write('Tavern will now display all external media.')
                redirect = False
        elif setting == "dontshowembeds":
            self.user.UserSettings['allowembed'] = -1
            server.logger.info("forbidding embeds")
        else:
            server.logger.info("Warning, you didn't do anything!")

        self.user.savemongo()
        self.setvars()
        if "js" in self.request.arguments:
            self.finish(divs=['column3'])
        else:
            if redirect == True:
                self.redirect("/")


class RatingHandler(BaseHandler):
    def get(self, posthash):
        self.getvars()
        #Calculate the votes for that post.

    def post(self):
        self.getvars(ensurekeys=True)

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
        e.payload.dict['class'] = "rating"
        e.payload.dict['rating'] = rating_val
        e.payload.dict['regarding'] = client_hash

        #Instantiate the user who's currently logged in

        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['pubkey'] = self.user.Keys.pubkey
        e.payload.dict['author'][
            'friendlyname'] = self.user.UserSettings['friendlyname']
        e.payload.dict['author']['useragent'] = {}
        e.payload.dict['author']['useragent']['name'] = 'Tavern Web Frontend'
        e.payload.dict['author']['useragent']['version'] = .01
        if self.user.UserSettings['include_location'] == True or 'include_location' in self.request.arguments:
            gi = pygeoip.GeoIP('/usr/local/share/GeoIP/GeoIPCity.dat')
            ip = self.request.remote_ip

            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"

            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + \
                "," + str(gir['longitude'])

        #Sign this bad boy
        usersig = self.user.Keys.signstring(
            e.payload.text(), self.user.passkey)

        stamp = OrderedDict()
        stamp['class'] = 'author'
        stamp['pubkey'] = self.user.Keys.pubkey
        stamp['signature'] = usersig
        utctime = time.time()
        stamp['time_added'] = int(utctime)
        stamplist = []
        stamplist.append(stamp)
        e.dict['envelope']['stamps'] = stamplist

        #Send to the server
        server.receiveEnvelope(e.text())

        self.write("Your vote has been recorded. Thanks!")


class UserNoteHandler(BaseHandler):
    def get(self, user):
        self.getvars()
        #Show the Note for a user

    def post(self):
        self.getvars(ensurekeys=True)

        client_pubkey = self.get_argument("pubkey")
        client_note = self.get_argument("note")
        self.user.setNote(client_pubkey, client_note)

        # Write it back to the page
        self.write('<input class="usernote" type="text" value="" name="note" placeholder="' + client_note + '">')
        server.logger.info("Note Submitted.")


class UserTrustHandler(BaseHandler):
    def get(self, user):
        self.getvars()
        #Calculate the trust for a user.

    def post(self):
        self.getvars(ensurekeys=True)

        trusted_pubkey = urllib.parse.unquote(
            self.get_argument("trusted_pubkey"))
        trusted_pubkey = Keys(pub=trusted_pubkey).pubkey

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
        e.payload.dict['author']['pubkey'] = self.user.Keys.pubkey
        e.payload.dict['author'][
            'friendlyname'] = self.user.UserSettings['friendlyname']
        e.payload.dict['author']['useragent'] = {}
        e.payload.dict['author']['useragent']['name'] = 'Tavern Web Frontend'
        e.payload.dict['author']['useragent']['version'] = .01

        if self.user.UserSettings['include_location'] == True or 'include_location' in self.request.arguments:
            gi = pygeoip.GeoIP('/usr/local/share/GeoIP/GeoIPCity.dat')
            ip = self.request.remote_ip

            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"

            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + \
                "," + str(gir['longitude'])

        #Sign this bad boy
        usersig = self.user.Keys.signstring(
            e.payload.text(), self.user.passkey)

        stamp = OrderedDict()
        stamp['class'] = 'author'
        stamp['pubkey'] = self.user.Keys.pubkey
        stamp['signature'] = usersig
        utctime = time.time()
        stamp['time_added'] = int(utctime)
        stamplist = []
        stamplist.append(stamp)
        e.dict['envelope']['stamps'] = stamplist

        #Send to the server
        server.receiveEnvelope(e.text())
        server.logger.info("Trust Submitted.")


class NewmessageHandler(BaseHandler):

    def options(self, regarding=None):
        self.set_header('Access-Control-Allow-Methods',
                        'OPTIONS, HEAD, GET, POST, PUT, DELETE')
        self.set_header('Access-Control-Allow-Origin', '*')

    def get(self, topic=None, regarding=None):
        self.getvars()
        self.write(self.render_string('header.html',
                   title="Post a new message", rsshead=None, type=None))
        self.write(self.render_string('newmessageform.html',regarding=regarding, topic=topic, args=self.request.arguments))
        self.write(self.render_string('footer.html'))
        self.finish(divs=['column3'])

    def post(self, flag=None):
        self.getvars(ensurekeys=True)
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
                individual_file['fullpath'] = serversettings.settings[
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
            server.logger.info("Dealing with File " + attached_file['filename']
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
            server.logger.info("Creating Message")
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

                detail['url'] = serversettings.settings[
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

        client_body = self.get_argument("body")
        # Pull in our Form variables.
        # The reason for the uncertainty is the from can be used two ways; One for replies, one for new messages.
        # It acts differently in the two scenerios.
        if "topic" in self.request.arguments:
            client_topic = self.get_argument("topic")
            if client_topic == "":
                client_topic = None
        else:
            client_topic = None

        if "subject" in self.request.arguments:
            client_subject = self.get_argument("subject")
            if client_subject == "":
                client_subject = None
        else:
            client_subject = None
        if "to" in self.request.arguments:
            client_to = self.get_argument("to")
            if client_to == "":
                client_to = None
        else:
            client_to = None
        if "regarding" in self.request.arguments:
            client_regarding = self.get_argument("regarding")
            if client_regarding == "":
                client_regarding = None
        else:
            client_regarding = None

        e = Envelope()

        e.payload.dict['formatting'] = "markdown"

        if client_to is None:
            e.payload.dict['class'] = "message"
            e.payload.dict['body'] = client_body

            if client_regarding is not None:
                server.logger.info("Adding Regarding - " + client_regarding)
                e.payload.dict['regarding'] = client_regarding
                regardingmsg = server.db.unsafe.find_one('envelopes', {'envelope.payload_sha512': client_regarding})
                e.payload.dict['topic'] = regardingmsg['envelope'][
                    'payload']['topic']
                e.payload.dict['subject'] = regardingmsg[
                    'envelope']['payload']['subject']
            else:
                e.payload.dict['topic'] = client_topic
                e.payload.dict['subject'] = client_subject

        else:
            e.payload.dict['class'] = "privatemessage"
            touser = Keys(pub=client_to)
            touser.format_keys()
            e.payload.dict['to'] = touser.pubkey
            e.payload.dict['body'] = self.user.Keys.encrypt(encrypt_to=touser.pubkey, encryptstring=client_body, passkey=self.user.passkey)

            if client_regarding is not None:
                server.logger.info("Adding Regarding - " + client_regarding)
                e.payload.dict['regarding'] = client_regarding
                regardingmsg = server.db.unsafe.find_one('envelopes', {'envelope.payload_sha512': client_regarding})
                oldsubject = self.user.decrypt(
                    regardingmsg['envelope']['payload']['subject'])
                e.payload.dict['subject'] = self.user.Keys.encrypt(encrypt_to=touser.pubkey, encryptstring=oldsubject, passkey=self.user.passkey)
            else:
                e.payload.dict['subject'] = self.user.Keys.encrypt(encrypt_to=touser.pubkey, encryptstring=client_subject, passkey=self.user.passkey)

        if len(envelopebinarylist) > 0:
            e.payload.dict['binaries'] = envelopebinarylist

        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['pubkey'] = self.user.Keys.pubkey
        e.payload.dict['author'][
            'friendlyname'] = self.user.UserSettings['friendlyname']
        e.payload.dict['author']['useragent'] = {}
        e.payload.dict['author']['useragent']['name'] = 'Tavern Web Frontend'
        e.payload.dict['author']['useragent']['version'] = .01

        if self.user.UserSettings['include_location'] == True or 'include_location' in self.request.arguments:
            gi = pygeoip.GeoIP('/usr/local/share/GeoIP/GeoIPCity.dat')
            ip = self.request.remote_ip

            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"

            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + \
                "," + str(gir['longitude'])

        #Sign this bad boy
        usersig = self.user.Keys.signstring(
            e.payload.text(), self.user.passkey)

        stamp = OrderedDict()
        stamp['class'] = 'author'
        stamp['pubkey'] = self.user.Keys.pubkey
        stamp['signature'] = usersig
        utctime = time.time()

        stamp['time_added'] = int(utctime)
        stamplist = []
        stamplist.append(stamp)
        e.dict['envelope']['stamps'] = stamplist

        #Send to the server
        newmsgid = server.receiveEnvelope(e.text())
        if newmsgid != False:
            if client_to is None:
                if client_regarding is not None:
                    self.redirect('/message/' + server.find_top_parent(
                        newmsgid) + "?jumpto=" + newmsgid, permanent=False)
                else:
                    self.redirect('/message/' + newmsgid, permanent=False)
            else:
                self.redirect('/showprivates')
        else:
            self.write("Failure to insert message.")


class ShowPrivatesHandler(BaseHandler):
    def get(self):
        self.getvars(ensurekeys=True)

        messages = []
        self.write(self.render_string('header.html',
                   title="Welcome to the Tavern!", rsshead=None, type=None))

        for message in server.db.unsafe.find('envelopes', {'envelope.payload.to': self.user.Keys.pubkey}, fields=['envelope.payload_sha512', 'envelope.payload.subject'], limit=10, sortkey='value', sortdirection='descending'):
            message['envelope']['payload']['subject'] = "Message: " + self.user.Keys.decrypt(message['envelope']['payload']['subject'], passkey=self.user.passkey)
            messages.append(message)

        self.write(
            self.render_string('showprivatemessages.html', messages=messages))
        self.write(self.render_string('footer.html'))


class PrivateMessageHandler(BaseHandler):
    def get(self, message):
        self.getvars(ensurekeys=True)

        message = server.db.unsafe.find_one('envelopes', {'envelope.payload.to': self.user.Keys.pubkey, 'envelope.payload_sha512': message})
        if message is not None:
            decrypted_subject = self.user.Keys.decrypt(message['envelope']['payload']['subject'], passkey=self.user.passkey)
        else:
            decrypted_subject = ""
        self.write(self.render_string('header.html', title="Private Message - " + decrypted_subject, rsshead=None, type=None))
        self.write(
            self.render_string('showprivatemessage.html', envelope=message))
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

class VerificationHandler(BaseHandler):
    """
    For users who aren't using nginx (like in dev), this will pull in the avatars
    """
    def get(self):
        self.write("loaderio-a80dc3024db2124fb7410acd64bb7e19")



class AvatarHandler(BaseHandler):
    """
    For users who aren't using nginx (like in dev), this will pull in the avatars
    """
    def get(self, avatar):
        server.logger.info("Bouncing to offsite avatar. Install the NGINX package to avoid this! ")
        self.redirect('https://robohash.org/' + avatar + "?" + "set=" + self.get_argument('set') + "&bgset=" + self.get_argument('bgset') + "&size=" + self.get_argument('size'))


define("port", default=8080, help="run on the given port", type=int)
def main():
    tornado.options.parse_command_line()
    # timeout in seconds
    timeout = 10
    socket.setdefaulttimeout(timeout)
    server.logger.info(
        "Starting Web Frontend for " + serversettings.settings['hostname'])

    # Generate a default user, to use when no one is logged in.
    # This can't be done in the Server module, because it requires User, which requires Server, which can't then require User....
    if not 'guestacct' in serversettings.settings:
        serveruser = User()
        serveruser.generate(skipkeys=False, password=serversettings.settings[
                            'serverkey-password'])
        serversettings.settings['guestacct'] = serveruser.UserSettings
        serversettings.saveconfig()

    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "cookie_secret": serversettings.settings['cookie-encryption'],
        "login_url": "/login",
        "xsrf_cookies": True,
        "template_path": "themes",
        "autoescape": "xhtml_escape"
    }
    application = tornado.web.Application([
        (r"/", TriPaneHandler),
        (r"/register", RegisterHandler),
        (r"/login/(.*)", LoginHandler),
        (r"/login", LoginHandler),
        (r"/user/(.*)", UserHandler),
        (r"/changepassword", ChangepasswordHandler),
        (r"/logout", LogoutHandler),
        (r"/rss/(.*)/(.*)", RSSHandler),
        (r"/raw/(.*)", RawMessageHandler),
        (r"/newmessage", NewmessageHandler),
        (r"/uploadfile/(.*)", NewmessageHandler),
        (r"/reply/(.*)/(.*)", NewmessageHandler),
        (r"/reply/(.*)", NewmessageHandler),
        (r"/uploadnewmessage", NewmessageHandler),
        (r"/vote", RatingHandler),
        (r"/usertrust", UserTrustHandler),
        (r"/usernote", UserNoteHandler),
        (r"/alltopics", AllTopicsHandler),
        (r"/attachment/(.*)", AttachmentHandler),
        (r"/topicinfo/(.*)", TopicPropertiesHandler),
        (r"/changesetting/(.*)/(.*)", ChangeSingleSettingHandler),
        (r"/changesetting/(.*)", ChangeSingleSettingHandler),
        (r"/changesettings", ChangeManySettingsHandler),
        (r"/showprivates", ShowPrivatesHandler),
        (r"/newprivatemessage/(.*)", NewPrivateMessageHandler),
        (r"/privatemessage/(.*)", PrivateMessageHandler),
        (r"/sitecontent/(.*)", SiteContentHandler),
        (r"/avatar/(.*)", AvatarHandler),
        (r"/binaries/(.*)/(.*)", BinariesHandler),
        (r"/binaries/(.*)", BinariesHandler),
        (r"/loaderio-a80dc3024db2124fb7410acd64bb7e19.txt",VerificationHandler), 
        (r"/static/(.*)", tornado.web.StaticFileHandler, {"path":
         os.path.join(os.path.dirname(__file__), "static/")}),
        (r"/(.*)/(.*)/(.*)", TriPaneHandler),
        (r"/(.*)/(.*)", TriPaneHandler),
        (r"/(.*)", TriPaneHandler),
    ], **settings)

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)

    server.logger.info(
        serversettings.settings['hostname'] + ' is ready for requests on port ' + str(options.port) )
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
