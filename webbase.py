import libtavern.user
import libtavern.server
import libtavern.topicfilter
import random


class BaseHandler(object):

    def load_session(self, AllowGuestKey=True):
        """Load into memory the User class by way of the session cookie.

        Generates a new user (usually guest) if it can't find one.

        """
        pass
        # Create a user obj - We'll either make this into a new user, the default user, or an empty user.
        self.user = libtavern.user.User()

        # Load in our saved passkey if it's available.
        if self.request.get_cookie('passkey', secret=self.server.serversettings.settings['session-key']):
            self.user.passkey = self.request.get_cookie('passkey', secret=self.server.serversettings.settings['session-key'])

        # Load in our session token if we have one.
        if self.request.get_cookie('sessionid', secret=self.server.serversettings.settings['session-key']):
            result = self.user.load_mongo_by_sessionid(
                self.request.get_cookie('sessionid', secure=True, secret=self.server.serversettings.settings['session-key']))

        # Ensure we have a user that is valid
        # If not, clear cookies, delete user, treat as not-logged-in.
        try:
            if self.user.Keys['master'].pubkey is None:
                raise
        except:
            self.response.delete_cookie('passkey')
            self.response.delete_cookie('sessionid')

            self.user = libtavern.user.User()

        if self.user.generate(AllowGuestKey=AllowGuestKey):
            self.user.save_mongo()
            self.save_session()

    def save_session(self):
        """Saves the current user to a session cookie.

        These are encrypted using the Bottle encryption system.

        """
        pass
        # Note - We're using a sessionid lookup table, not storing a key from the User.
        # This abstraction is useful for 2-factor auth, API lookups, and the like.
        # It does cause a second DB hit, but for now it's worth the tradeoff.

        # If we're over https, ensure the cookie can't be read over HTTP
        if self.server.serversettings.settings['url-scheme'].lower() == 'https':
            secure = True
        else:
            secure = False

        # Save our Passkey. This is the key which allows the user to decrypt their keys.
        # This passkey is never stored serverside.
        if self.user.has_unique_key:
            if self.user.passkey is not None:
                self.response.set_cookie('passkey', user.passkey, secure=secure, httponly=True, max_age=31556952 * 2,
                                         secret=self.server.serversettings.settings['session-key'])

        # Before we save out the sessionid, make sure the user is valid
        if self.user.generate():
            self.user.save_mongo()
        self.response.set_cookie('sessionid', self.user.save_session(), secure=secure, httponly=True,
                                 max_age=31556952 * 2, secret=self.server.serversettings.settings['session-key'])

    def setheaders(self):
        """Set various headers that each HTTP response should have."""
        # Add in a random fortune
        self.response.headers.replace("X-Fortune", self.server.fortune.random().encode('iso-8859-1', errors='ignore'))
        # Do not allow the content to load in a frame.
        # Should help prevent certain attacks
        self.response.headers.replace("X-FRAME-OPTIONS", "DENY")
        # Don't try to guess content-type.
        # This helps avoid JS sent in an image.
        self.response.headers.replace("X-Content-Type-Options", "nosniff")

        # http://cspisawesome.com/content_security_policies
        # bottle.response.set_header(
        #     "Content-Security-Policy-Report-Only",
        #     "default-src 'self'; script-src 'unsafe-inline' 'unsafe-eval' data 'self'; object-src 'none'; style-src 'self'; img-src *; media-src mediaserver; frame-src " +
        #     self.server.serversettings.settings[
        #         'embedserver'] +
        #     " https://www.youtube.com https://player.vimeo.com; font-src 'self'; connect-src 'self'")

    def __init__(self, request, response, server):

        print("Creating new init!")
        """Create the base object for all requests to our Tavern webserver."""
        self.response = response
        self.request = request
        self.server = server

        self.setheaders()
        self.load_session()

        # Retrieve the User-Agent if possible.
        ua = self.request.headers.get('User-Agent', 'Unknown')
        self.useragent = self.server.browserdetector.parse(ua)
        # Check to see if we have support for datauris in our browser.
        # If we do, send the first ~10 pages with datauris.
        # After that switch back, since caching the images is likely to be
        # better, if you're a recurrent reader
        # If a URL explicltly asks for datauri on or off, disregard prior.

        if 'datauri' in self.request.query:
            if self.request.query["datauri"].lower() == 'true':
                self.datauri = True
            elif self.request.query["datauri"].lower() == 'false':
                self.datauri = False

        elif self.user.UserSettings['datauri'] is not None:
            self.datauri = self.user.UserSettings['datauri']

        elif random.SystemRandom().randrange(1, 10) == 5:
                self.user.UserSettings['datauri'] = False
                self.datauri = False
                self.user.save_mongo()

        elif self.useragent['ua_family'] == 'IE' and self.useragent['ua_versions'][0] < 8:
            self.datauri = False
        else:
            self.datauri = True

        # Do we want to show the original, ignoring edits?
        if 'showoriginal' in self.request.query:
            # Convert the string to a bool.
            self.showoriginal = (self.request.query['showoriginal'].lower() == "true")
        else:
            self.showoriginal = self.user.UserSettings['ignore_edits']

        # To move forward and backward in the results, we specify a time.
        # We then move this backward/forward, and search with it.
        # This is cheaper than skip() http://docs.mongodb.org/manual/reference/method/cursor.skip/

        if 'before' in self.request.query:
            self.before = float(self.request.query['before'])
        else:
            self.before = None

        if 'after' in self.request.query:
            self.after = float(self.request.query['after'])
        else:
            self.after = None

        self.topicfilter = libtavern.topicfilter.TopicFilter()
