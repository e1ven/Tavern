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
from libs import rss
import pprint
import Image
import imghdr
import io
from TopicTool import topictool
from TavernUtils import memorise
import TavernUtils
from ServerSettings import serversettings
from tornado.options import define, options
from UserGenerator import UserGenerator
import inspect, sys
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
        super().__init__(*args, **kwargs)
        
        # Set the canonical URL, if possible.
        self.canon = None

        # Ensure we don't run finish() twice.
        self._basefinish = False

        # If people are accessing a URL that isn't by the canonical URL, redirect them.
        if 'redirected' in self.request.arguments:
            # Set a bool, to ensure we don't redirect twice....
            self.redirected = (self.get_argument('redirected') == "True")
            print("Was redirected")
        else:
            self.redirected = False
            print("Was not redirected")

        # Is this necessary EVERY time? It's quick, I suppose...
        if serversettings.settings['primaryurl'] == False:
            serversettings.settings['primaryurl'] = self.request.protocol + "://" + (self.request.host or socket.gethostbyaddr(socket.gethostbyname(socket.gethostname())) )
            serversettings.saveconfig()

        # Add in a random fortune
        self.set_header("X-Fortune", str(server.fortune.random()))
        # Do not allow the content to load in a frame.
        # Should help prevent certain attacks
        self.set_header("X-FRAME-OPTIONS", "DENY")
        # Don't try to guess content-type.
        # This helps avoid JS sent in an image.
        self.set_header("X-Content-Type-Options", "nosniff")
        
        # http://cspisawesome.com/content_security_policies
        self.set_header("Content-Security-Policy-Report-Only","default-src 'self'; script-src 'unsafe-inline' 'unsafe-eval' data 'self'; object-src 'none'; style-src 'self'; img-src *; media-src mediaserver; frame-src " + serversettings.settings['embedserver'] + " https://www.youtube.com https://player.vimeo.com; font-src 'self'; connect-src 'self'")
        
        self.fullcookies = {}
        for cookie in self.request.cookies:
            self.fullcookies[cookie] = self.get_cookie(cookie)

        # Get the Browser version.
        if 'User-Agent' in self.request.headers:
            ua = self.request.headers['User-Agent']
            self.browser = server.browserdetector.parse(ua)
        else:
            self.browser = server.browserdetector.parse("Unknown") 
    
    # @memorise(parent_keys=['fullcookies', 'user.UserSettings'], ttl=serversettings.settings['cache']['templates']['seconds'], maxsize=serversettings.settings['cache']['templates']['size'])
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

    def finish(self, divs=['wrappertable'], message=None):
        """
        Pulls in appropriate divs and serves them out via JS if possible.
        This saves bits, and keeps the columns as you left them.

        Finish() is a function defined by tornado, so this will be called automatically if not included manually.
        """

        # Don't run this function twice. If we're called a second time, get the frig out.
        if self._basefinish == True:
            print("short circuiting")
            return

        self._basefinish = True

        # First off, we may be at the wrong URL. Check to see if this is the canonical version of this URL.
        # If it's not, and it's safe, go there.
        if not self.redirected:
            if self.request.method == "GET":
                if (self.canon != None):
                    # Break apart current and canonical URLs to check to see if they match.
                    canon_scheme, canon_netloc, canon_path, canon_query_string, canon_fragment = urllib.parse.urlsplit(serversettings.settings['primaryurl'] + '/' + self.canon)
                    orig_scheme, orig_netloc, orig_path, orig_query_string, orig_fragment = urllib.parse.urlsplit(self.request.full_url())
                    if (orig_path != canon_path) or (orig_scheme != canon_scheme) or (orig_netloc != canon_netloc):
                        # This is not the canonical URL, bounce us.    
                        # Merge canon with current url
                        query_params = urllib.parse.parse_qs(orig_query_string)
                        query_params['redirected'] = ['True']
                        fixed_query_string = urllib.parse.urlencode(query_params, doseq=True)

                        newurl =  urllib.parse.urlunsplit((canon_scheme, canon_netloc, canon_path, fixed_query_string, canon_fragment))
                        self.redirected = True
                        self.redirect(newurl)
                        return super().finish(message)



        # If they ask for the JS version, we'll calculate it.
        if "js" in self.request.arguments:

            if "divs" in self.request.arguments:
                # if they just want one, just give them that one.
                client_div=self.get_argument('divs')
                divs= tornado.escape.xhtml_escape(client_div).split(',')
                print(divs)
            # Send the header information with the new name, then each div, then the footer.
            super(BaseHandler, self).write(self.getjssetup())
            for div in divs:
                print("For Div - " + div)
                super(BaseHandler, self).write(self.getjselement(div))
            super(BaseHandler, self).write(self.getjsfooter())


        # GetOnly is used to request only specific divs.
        # And example is requesting the message reply inline.

        elif "getonly" in self.request.arguments:
            client_get=self.get_argument('getonly')
            get=tornado.escape.xhtml_escape(client_get)
            super(BaseHandler, self).write(self.getdiv(get))

        # If we're here, send the whole page as a regular view.
        else:
            super(BaseHandler, self).write(self.html)

        if "js" in self.request.arguments:
            self.set_header("Content-Type", "application/json")

        return super().finish(message)

    @memorise(parent_keys=['html'], ttl=serversettings.settings['cache']['getpagelemenent']['seconds'], maxsize=serversettings.settings['cache']['getpagelemenent']['size'])
    def getdiv(self, element):
        print("getting" + element)
        soup = BeautifulSoup(self.html,"html.parser")
        soupyelement = soup.find(id=element)
        soupytxt = ""
        if soupyelement is not None:
            for child in soupyelement.contents:
                soupytxt += str(child)
        return soupytxt


    @memorise(parent_keys=['request.uri', 'html'], ttl=serversettings.settings['cache']['templates']['seconds'], maxsize=serversettings.settings['cache']['templates']['size'])
    def getjssetup(self):
        # Strip out GET params we don't need to display to the user.
        urlargs = urllib.parse.parse_qs(self.request.query,keep_blank_values=True)
        print(urlargs)
        if 'timestamp' in urlargs:
            del urlargs['timestamp']
        if 'divs' in urlargs:
            del urlargs['divs']
        if 'js' in urlargs:
            del urlargs['js']
        newargs = urllib.parse.urlencode(urlargs,doseq=True)
        modifiedurl = self.request.path + newargs

        try:
            soup = BeautifulSoup(self.html,"html.parser")
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

    @memorise(parent_keys=['request.uri', 'html'], ttl=serversettings.settings['cache']['getpagelemenent']['seconds'], maxsize=serversettings.settings['cache']['getpagelemenent']['size'])
    def getjselement(self, element):
        """
        Get the element text, remove all linebreaks, and escape it up.
        Then, send that as a document replacement
        Also, rewrite the document history in the browser, so the URL looks normal.
        """
        try:
            soup = BeautifulSoup(self.html,"html.parser")
        except:
            print('malformed data in BeautifulSoup')
            raise
        soupyelement = soup.find(id=element)
        soupytxt = str(soupyelement)
        escapedtext = soupytxt.replace("\"", "\\\"")
        escapedtext = escapedtext.replace("\n", "")

        return ('jQuery("#' + element + '").replaceWith("' + escapedtext  + '");')

    def getjsfooter(self):
        # The stuff at the bottom of the JS file.
        ret =   '''
                jQuery('#spinner').hide();
                jQuery('.spinner').removeClass("spinner");
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
        server.logger.debug("numchunks + " + str(numchunks))

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
            server.logger.debug("Making cookies")
            self.user.generate(GuestKey=True)
            self.setvars()

        # If a method has asked us to ensure a user is full, with a privkey and everything, do so.
        # This is done here, rather than in user, so we can save the passkey out to a cookie.
        if ensurekeys == True:
            validkey = False
            if 'encryptedprivkey' in self.user.UserSettings['keys']['master']:
                if self.user.UserSettings['keys']['master']['encryptedprivkey'] is not None:
                    validkey = True
            if not validkey:
                newuser = server.GetUnusedUser()
                
                self.user = newuser['user']
                password = newuser['password']

                # ensure user is fleshed out
                self.user.generate()

                # Save it out.
                self.setvars()
                self.user.savemongo()
                self.set_secure_cookie('tavern_passkey', self.user.Keys['master'].passkey(password), httponly=True, expires_days=999)
                self.user.passkey = self.user.Keys['master'].passkey(password)

            if not hasattr(self.user, 'passkey'):
                self.user.passkey = self.get_secure_cookie('tavern_passkey')
            if self.user.passkey is None:
                self.user.passkey = self.get_secure_cookie('tavern_passkey')

        # Ensure we have any missing fields.
        self.user.generate(GuestKey=True)

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

    def write_error(self, status_code, **kwargs):
        """
        Errors? We don't need no stinkin errors. Just ignore for now, redirect.
        """
        self.write(self.render_string('header.html', title="Error", canon="/error", type="topic", rsshead=None))
        self.write(self.render_string('error.html',topic='sitecontent'))
        self.write(self.render_string('footer.html'))


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

# What happens when people request the root level?
# for now, send them to that Welcome message ;)
class EntryHandler(tornado.web.RequestHandler):
    def get(self):
        self.redirect('/topic/sitecontent')

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
    # @memorise(parent_keys=['fullcookies','request.arguments'], ttl=serversettings.settings['cache']['message-page']['seconds'], maxsize=serversettings.settings['cache']['message-page']['size'])
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
            displayenvelope = messagesenvelope
            topic = displayenvelope['envelope']['payload']['topic']
            self.canon = "message/" + displayenvelope['envelope']['local']['sorttopic'] + '/' + displayenvelope['envelope']['local']['short_subject'] + "/" + displayenvelope['envelope']['local']['payload_sha512']
            title = displayenvelope['envelope']['payload']['subject']
        else:
            # If we didn't find that message, throw an error.
            displayenvelope = server.error_envelope("The Message you are looking for can not be found.").dict
            title = displayenvelope['envelope']['payload']['subject']
            topic = displayenvelope['envelope']['payload']['topic']

        # Gather up all the replies to this message, so we can send those to the template as well
        self.write(self.render_string('header.html', title=title, canon=self.canon, type="topic", rsshead=displayenvelope['envelope']['payload']['topic']))
        self.write(self.render_string('showmessage.html',
                   envelope=displayenvelope, before=before, topic=topic))
        self.write(self.render_string('footer.html'))
        print("Func complete.")
        #self.finish(divs=divs)


class TopicHandler(BaseHandler):

    """
    The Topic Handler displays a topic, and the messages that are in it.
    """

    #@memorise(parent_keys=['fullcookies','request.arguments'], ttl=serversettings.settings['cache']['topic-page']['seconds'], maxsize=serversettings.settings['cache']['topic-page']['size'])
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
            displayenvelope = server.error_envelope("That topic does not have any messages in it yet.").dict
            canon = None
            title = displayenvelope['envelope']['payload']['subject']
            topic = displayenvelope['envelope']['payload']['topic']

        # Gather up all the replies to this message, so we can send those to the template as well
        self.write(self.render_string('header.html', title=title, canon=self.canon, type="topic", rsshead=displayenvelope['envelope']['payload']['topic']))
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
            self.user.generate(GuestKey=False,
                username=client_newuser.lower(), password=client_newpass)
            self.user.UserSettings['lastauth'] = int(time.time())

            if client_email is not None:
                self.user.UserSettings['email'] = client_email.lower()

            self.user.savemongo()

            # Save the passkey out to a separate cookie.
            self.set_secure_cookie("tavern_passkey", self.user.Keys['master'].passkey(
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
                self.set_secure_cookie("tavern_passkey", self.user.Keys['master'].passkey(client_password), httponly=True, expires_days=999)
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
        self.set_secure_cookie("tavern_passkey", self.user.Keys['master'].passkey(
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
        pubkey = Keys(pub=pubkey).pubkey

        u = User()
        u.UserSettings['keys']['master']['pubkey'] = pubkey
        u.generate(GuestKey=True)

        self.write(self.render_string('header.html', title="User page",
                                      rsshead=None, type=None))

        self.write(self.render_string(
            'userpage.html', thatguy=u,topic=None))

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

        if "js" in self.request.arguments:
            self.finish(divs=['scrollablediv3'])
        else:
            keyurl = ''.join(self.user.Keys['master'].pubkey.split())
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
        e.payload.dict['class'] = "messagerating"
        e.payload.dict['rating'] = rating_val
        e.payload.dict['regarding'] = client_hash

        #Instantiate the user who's currently logged in

        #TODO - set comm key
        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['pubkey'] = self.user.Keys['master'].pubkey
        e.payload.dict['author'][
            'friendlyname'] = self.user.UserSettings['friendlyname']
        e.payload.dict['author']['useragent'] = {}
        e.payload.dict['author']['useragent']['name'] = 'Tavern Web Frontend'
        e.payload.dict['author']['useragent']['version'] = .01
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
        if serversettings.settings['mark-origin'] == True:
                e.addStamp(stampclass='origin',keys=server.ServerKeys,hostname=serversettings.settings['hostname'])


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
        server.logger.debug("Note Submitted.")


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
        e.payload.dict['author']['pubkey'] = self.user.Keys['master'].pubkey
        e.payload.dict['author'][
            'friendlyname'] = self.user.UserSettings['friendlyname']
        e.payload.dict['author']['useragent'] = {}
        e.payload.dict['author']['useragent']['name'] = 'Tavern Web Frontend'
        e.payload.dict['author']['useragent']['version'] = .01

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
        if serversettings.settings['mark-origin'] == True:
                e.addStamp(stampclass='origin',keys=server.ServerKeys,hostname=serversettings.settings['hostname'])


        #Send to the server

        server.receiveEnvelope(e.text())
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

        self.write(self.render_string('newmessageform.html',regarding=regarding, topic=topic, oldtext=oldtext,edit=True))
        self.write(self.render_string('footer.html'))
        self.finish(divs=['scrollablediv3'])

class NewmessageHandler(BaseHandler):

    def options(self, regarding=None):
        self.set_header('Access-Control-Allow-Methods',
                        'OPTIONS, HEAD, GET, POST, PUT, DELETE')
        self.set_header('Access-Control-Allow-Origin', '*')

    def get(self, topic=None, regarding=None):
        self.getvars()
        self.write(self.render_string('header.html',
                   title="Post a new message", rsshead=None, type=None))
        self.write(self.render_string('newmessageform.html',regarding=regarding, topic=topic, oldtext=None,edit=False))
        self.write(self.render_string('footer.html'))
        self.finish(divs=['scrollablediv3'])

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
            if flag == "edit":
                e.payload.dict['class'] = "messagerevision"
            else:
                e.payload.dict['class'] = "message"
            e.payload.dict['body'] = client_body

            if client_regarding is not None:
                server.logger.debug("Adding Regarding - " + client_regarding)
                e.payload.dict['regarding'] = client_regarding
                regardingmsg = server.db.unsafe.find_one('envelopes', {'envelope.local.payload_sha512': client_regarding})
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
            e.payload.dict['to'] = touser.pubkey
            e.payload.dict['body'] = self.user.Keys['master'].encrypt(encrypt_to=touser.pubkey, encryptstring=client_body, passkey=self.user.passkey)

            if client_regarding is not None:
                server.logger.debug("Adding Regarding - " + client_regarding)
                e.payload.dict['regarding'] = client_regarding
                regardingmsg = server.db.unsafe.find_one('envelopes', {'envelope.local.payload_sha512': client_regarding})
                oldsubject = self.user.decrypt(
                    regardingmsg['envelope']['payload']['subject'])
                e.payload.dict['subject'] = self.user.Keys['master'].encrypt(encrypt_to=touser.pubkey, encryptstring=oldsubject, passkey=self.user.passkey)
            else:
                e.payload.dict['subject'] = self.user.Keys['master'].encrypt(encrypt_to=touser.pubkey, encryptstring=client_subject, passkey=self.user.passkey)

        if len(envelopebinarylist) > 0:
            e.payload.dict['binaries'] = envelopebinarylist

        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['pubkey'] = self.user.Keys['master'].pubkey
        e.payload.dict['author'][
            'friendlyname'] = self.user.UserSettings['friendlyname']
        e.payload.dict['author']['useragent'] = {}
        e.payload.dict['author']['useragent']['name'] = 'Tavern Web Frontend'
        e.payload.dict['author']['useragent']['version'] = .01

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
        if serversettings.settings['mark-origin'] == True:
                e.addStamp(stampclass='origin',keys=server.ServerKeys,hostname=serversettings.settings['hostname'])


        #Send to the server
        newmsgid = server.receiveEnvelope(e.text())
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
    def get(self):
        self.getvars(ensurekeys=True)

        messages = []
        self.write(self.render_string('header.html',
                   title="Welcome to the Tavern!", rsshead=None, type=None))

        for message in server.db.unsafe.find('envelopes', {'envelope.payload.to': self.user.Keys['master'].pubkey}, limit=10, sortkey='value', sortdirection='descending'):
            message['envelope']['payload']['subject'] = "Message: " + self.user.Keys['master'].decrypt(message['envelope']['payload']['subject'], passkey=self.user.passkey)
            messages.append(message)

        self.write(
            self.render_string('showprivatemessages.html', messages=messages))
        self.write(self.render_string('footer.html'))


class PrivateMessageHandler(BaseHandler):
    def get(self, message):
        self.getvars(ensurekeys=True)

        message = server.db.unsafe.find_one('envelopes', {'envelope.payload.to': self.user.Keys['master'].pubkey, 'envelope.local.payload_sha512': message})
        if message is not None:
            decrypted_subject = self.user.Keys['master'].decrypt(message['envelope']['payload']['subject'], passkey=self.user.passkey)
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

class AvatarHandler(tornado.web.RequestHandler):
    """
    For users who aren't using nginx (like in dev), this will pull in the avatars
    """
    def get(self, avatar):
        server.logger.info("Bouncing to offsite avatar. Install the NGINX package to avoid this! ")
        self.redirect('https://robohash.org/' + avatar + "?" + "set=" + self.get_argument('set') + "&bgset=" + self.get_argument('bgset') + "&size=" + self.get_argument('size'))

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
        "Starting Web Frontend for " + serversettings.settings['hostname'])

    # Generate a default user, to use when no one is logged in.
    # This can't be done in the Server module, because it requires User, which requires Server, which can't then require User....
    if not 'guestacct' in serversettings.settings:
    
        server.logger.info("NO GUEST...?")
        serveruser = User()
        serveruser.generate(GuestKey=False,password=serversettings.settings[
                            'serverkey-password'])
        serversettings.settings['guestacct'] = serveruser.UserSettings
        serversettings.saveconfig()

    if options.loglevel != "UNSET":
        serversettings.settings['temp']['loglevel'] = options.loglevel
        serversettings.settings['temp']['writelog'] = options.writelog


    server.debug = options.debug
    # Tell the server process to fire up and run for a while.
    server.start()


    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "cookie_secret": serversettings.settings['cookie-encryption'],
        "login_url": "/login",
        "xsrf_cookies": True,
        "template_path": "themes",
        "autoescape": "xhtml_escape"
    }
    application = tornado.web.Application([
        (r"/", EntryHandler),
        (r"/message/(.*)/(.*)/(.*)", MessageHandler),
        (r"/message/(.*)/(.*)", MessageHandler),
        (r"/message/(.*)", MessageHandler),
        (r"/messagehistory/(.*)", MessageHistoryHandler),
        (r"/m/(.*)/(.*)/(.*)", MessageHandler),
        (r"/m/(.*)/(.*)", MessageHandler),
        (r"/m/(.*)", MessageHandler),
        (r"/topic/(.*)", TopicHandler),
        (r"/t/(.*)", TopicHandler),
        (r"/register", RegisterHandler),
        (r"/login/(.*)", LoginHandler),
        (r"/login", LoginHandler),
        (r"/user/(.*)", UserHandler),
        (r"/changepassword", ChangepasswordHandler),
        (r"/logout", LogoutHandler),
        (r"/rss/(.*)/(.*)", RSSHandler),
        (r"/newmessage", NewmessageHandler),
        (r"/edit/(.*)", EditMessageHandler),
        (r"/uploadfile/(.*)", NewmessageHandler),
        (r"/reply/(.*)/(.*)", NewmessageHandler),
        (r"/reply/(.*)", NewmessageHandler),
        (r"/uploadnewmessage", NewmessageHandler),
        (r"/vote", RatingHandler),
        (r"/usertrust", UserTrustHandler),
        (r"/usernote", UserNoteHandler),
        (r"/showtopics", ShowTopicsHandler),
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
        (r"/static/(.*)", tornado.web.StaticFileHandler, {"path":
         os.path.join(os.path.dirname(__file__), "static/")})
    ], **settings)

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)

    server.logger.info(
        serversettings.settings['hostname'] + ' is ready for requests on port ' + str(options.port) )
    if options.initonly is False:
        tornado.ioloop.IOLoop.instance().start()
    else:
        server.logger.info("Exiting immediatly as requested")

if __name__ == "__main__":
    main()
