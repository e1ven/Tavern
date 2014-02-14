import libtavern.user
import libtavern.server
import libtavern.topicfilter
import random

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.escape
from tornado.options import define, options

server = libtavern.server.Server()


class BaseHandler(tornado.web.RequestHandler):

    def load_session(self, AllowGuestKey=True):
        """Load into memory the User class by way of the session cookie.

        Generates a new user (usually guest) if it can't find one.

        """
        
        # Create a user obj - We'll either make this into a new user, the default user, or an empty user.
        self.user = libtavern.user.User()

        # Load in our saved passkey if it's available.
        if self.get_secure_cookie('passkey'):
            self.user.passkey = self.get_secure_cookie('passkey')

        # Load in our session token if we have one.
        if self.get_secure_cookie('sessionid'):
            result = self.user.load_mongo_by_sessionid(
                self.get_secure_cookie('sessionid'))

        # Ensure we have a user that is valid
        # If not, clear cookies, delete user, treat as not-logged-in.
        try:
            if self.user.Keys['master'].pubkey is None:
                raise
        except:
            self.clear_cookie('passkey')
            self.clear_cookie('sessionid')

            self.user = libtavern.user.User()

        if self.user.ensure_keys(AllowGuestKey=AllowGuestKey):
            self.user.save_mongo()
            self.save_session()

    def save_session(self):
        """Saves the current user to a session cookie.

        These are encrypted by Tornado.

        """
        
        # Note - We're using a sessionid lookup table, not storing a key from the User.
        # This abstraction is useful for 2-factor auth, API lookups, and the like.
        # It does cause a second DB hit, but for now it's worth the tradeoff.

        # If we're over https, ensure the cookie can't be read over HTTP
        if self.server.serversettings.settings['webtav']['scheme'].lower() == 'https':
            secure = True
        else:
            secure = False

        # Save our Passkey. This is the key which allows the user to decrypt their keys.
        # This passkey is never stored serverside.
        if self.user.has_unique_key:
            if self.user.passkey is not None:
                self.set_secure_cookie('passkey', user.passkey, secure=secure, httponly=True, max_age=31556952 * 2)

        # Before we save out the sessionid, make sure the user is valid
        if self.user.ensure_keys():
            self.user.save_mongo()
        self.set_secure_cookie('sessionid', self.user.save_session(), secure=secure, httponly=True, max_age=31556952 * 2)

    def setheaders(self):
        """Set various headers that each HTTP response should have."""
        # Add in a random fortune
        self.set_header("X-Fortune", self.server.fortune.random().encode('iso-8859-1', errors='ignore'))
        # Do not allow the content to load in a frame.
        # Should help prevent certain attacks
        self.set_header("X-FRAME-OPTIONS", "DENY")
        # Don't try to guess content-type.
        # This helps avoid JS sent in an image.
        self.set_header("X-Content-Type-Options", "nosniff")

        # http://cspisawesome.com/content_security_policies
        # bottle.response.set_header(
        #     "Content-Security-Policy-Report-Only",
        #     "default-src 'self'; script-src 'unsafe-inline' 'unsafe-eval' data 'self'; object-src 'none'; style-src 'self'; img-src *; media-src mediaserver; frame-src " +
        #     self.server.serversettings.settings[
        #         'embedserver'] +
        #     " https://www.youtube.com https://player.vimeo.com; font-src 'self'; connect-src 'self'")

    def __init__(self, *args, **kwargs):
        """Create the base object for all requests to our Tavern webserver."""

        print("Creating new init!")

        self.server = server

        self.html = ""
        super().__init__(*args, **kwargs)


        self.setheaders()
        self.load_session()

        # Retrieve the User-Agent if possible.
        ua = self.request.headers.get('User-Agent', 'Unknown')
        self.useragent = self.server.browserdetector.parse(ua)


        # Get the URL for the server if we didn't set it.
        # We're pulling this from the request, since we can't auto-detect our own URL.
        # We don't re-save serversettings, since we only want it saved if it was intentionally set.
        # TODO: Find some other way of finding this out without checking every request.
        if self.server.serversettings.settings['webtav']['main_url'] is None:
            server.serversettings.settings['webtav']['main_url'] = self.request.protocol + "://" + self.request.host
            print("Detected URL as " + server.serversettings.settings['webtav']['main_url'])


        # Check to see if we have support for datauris in our browser.
        # If we do, send the first ~10 pages with datauris.
        # After that switch back, since caching the images is likely to be
        # better, if you're a recurrent reader
        # If a URL explicltly asks for datauri on or off, disregard prior.

        if self.get_argument("datauri",None):
            if self.get_argument("datauri").lower() == 'true':
                self.datauri = True
            elif self.get_argument("datauri").lower() == 'false':
                self.datauri = False
        elif self.user.datauri is not None:
            self.datauri = self.user.datauri
        elif random.SystemRandom().randrange(1, 10) == 5:
                self.user.datauri = False
                self.datauri = False
                self.user.save_mongo()
        elif self.useragent['ua_family'] == 'IE' and self.useragent['ua_versions'][0] < 8:
            self.datauri = False
        else:
            self.datauri = True

        # Do we want to show the original, ignoring edits?
        if self.get_argument('showoriginal',None):
            # Convert the string to a bool.
            self.showoriginal = (self.get_argument('showoriginal').lower() == "true")
        else:
            self.showoriginal = self.user.ignore_edits

        # To move forward and backward in the results, we specify a time.
        # We then move this backward/forward, and search with it.
        # This is cheaper than skip() http://docs.mongodb.org/manual/reference/method/cursor.skip/

        self.before = self.get_argument('before',None)
        if self.before:
            self.before = float(self.before)
        self.after = self.get_argument('after',None)
        if self.after:
            self.after = float(self.after)

        # If people are accessing a URL that isn't by the canonical URL,
        # redirect them.
        self.redirected = self.get_argument('redirected', False)


        self.topicfilter = libtavern.topicfilter.TopicFilter()

        # Set default values for variables we look for.
        self.canon = None
        self.title = None
        self.topic = None


    def write_error(self, status_code, **kwargs):
        """
        Catch exceptions and print out an error message using a template.
        """

        # Return our exception objects to normal objs
        exc = kwargs['exc_info'][1]
        exccls = kwargs['exc_info'][0]
        exctrc = kwargs['exc_info'][2]

        # Ensure we have something to print, even if we have to assign it here.
        try:
            subject = exc.short
        except AttributeError:
            subject = 'Something rather unexpected has happened :/'
        try:
            body = exc.long
        except AttributeError:
            body =  """
        It looks like something rather unexpected has happened -
        It's not clear what went wrong, but clearly something did.
        Dreadfully sorry about that..."""

        # Try using the value in the exception if possible.
        try:
            code = exc.status_code
        except AttributeError:
            code = status_code

        self.set_status(code)

        self.displayenvelope = self.server.error_envelope(topic='Error',subject=subject, body=body)
        self.topic = self.displayenvelope.dict['envelope']['payload']['topic']
        self.canon = None
        self.title = self.displayenvelope.dict['envelope']['payload']['subject']
        self.render('View-showmessage.html', handler=self)

    def get_template_path(self):
        """Returns the correct template path for the current theme.

        Currently this is using the chosen theme, but eventually we can default to mobile/etc here
        Overwrite to force a handler to use a specific theme (such as SiteMap)
        """
        basepath = self.application.settings.get("template_path")

        if self.user.theme in server.availablethemes:
            return basepath + '/' + self.user.theme
        else:
            return 'default' + '/' + self.user.theme

class weberror(Exception):
    """A generic http error message that supports subject/body.

    Raising the exception is preferred to calling write_error directly,
    This way we can log, look up errors in translation, etc.
    """
    def __init__(self, code=500, short=None,long=None,log=None, *args, **kwargs):

        self.status_code = code
        self.log_message = log
        self.args = args
        self.short = short
        self.long = long

    def __str__(self):
        # Look up the HTTP status code if possible.
        # If not, use the description passed in.
        message = "HTTP " + str(self.status_code) + " " + tornado.httputil.responses.get(self.status_code, self.short)
        if self.log_message:
            return message + " (" + (self.log_message % self.args) + ")"
        else:
            return message

