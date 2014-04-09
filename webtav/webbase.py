import libtavern.user
import libtavern.server
import libtavern.topic
import libtavern.utils
import random

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.escape
import tornado.httputil
import flask
from flask.views import MethodView
from functools import wraps
import webtav.flasknado

server = libtavern.server.Server()

class XSRFBaseHandler(tornado.web.RequestHandler):
    """
    A version of the Tornado RequestHandler with additional security in the XSRF token.
    """

    @property
    def is_secure(self):
        """Returns if the connection is loaded over https"""
        if hasattr(self, "_secure"):
            return self._secure

        if self.request.protocol == 'https':
            self._secure = True
        else:
            self._secure = False
        return self._secure

    @property
    def xsrf_token(self):
        """
        The XSRF value is a randomly generated string that is set in both POST requests and cookies.

        Overwritten from the Tornado default to use systemrandom rather than uuid.
        Like tornado, this method will set a cookie with the xsrf value if it does not currently exist.
        """
        # Only generate once/session
        if hasattr(self, "_xsrf_token"):
            return self._xsrf_token
        # Use cookie one if it exists, otherwise random str.
        token = self.get_signed_cookie('_xsrf',None)
        if not token:
            # Generate a token, save it to a cookie.
            token = libtavern.utils.randstr(16)
            self.set_secure_cookie(name="_xsrf",value=token,httponly=True, max_age=31556952 * 2)
        self._xsrf_token = token
        return self._xsrf_token

    def set_secure_cookie(self,name,value,*args,**kwargs):

        # Set secure flag when connecting over HTTPS
        # If so, set secure flag on cookie by default.
        if self.is_secure:
            kwargs['secure'] = True
        else:
            # If the 'secure' key exists, even if it's set to False, the flag will get sent/used.
            try:
                del kwargs['secure']
            except KeyError:
                pass

        self.set_cookie(name, self.create_signed_value(name, value),*args, **kwargs)

    def get_signed_cookie(self,name,value=None,max_age_days=31):
        """
        Gets a secure cookie, via Tornado, and returns it as a Unicode string.
        :param name:The name of the cookie
        :param value (optional): If passed, get_signed_cookie will get the value from `value` instead of a cookie
        :return: Unicode string of the cookie
        """
        result =  self.get_secure_cookie(name=name,value=value,max_age_days=max_age_days)
        if result:
            return result.decode('utf-8')
        else:
            return result

    def check_xsrf_cookie(self):
        """Verifies that the ``_xsrf`` cookie matches the ``_xsrf`` argument.

        To prevent cross-site request forgery, we set an ``_xsrf``
        cookie and include the same value as a non-cookie
        field with all ``POST`` requests. If the two do not match, we
        reject the form submission as a potential forgery.

        The ``_xsrf`` value may be set as either a form field named ``_xsrf``
        or in a custom HTTP header named ``X-XSRFToken`` or ``X-CSRFToken``
        (the latter is accepted for compatibility with Django).

        See http://en.wikipedia.org/wiki/Cross-site_request_forgery

        Prior to release 1.1.1, this check was ignored if the HTTP header
        ``X-Requested-With: XMLHTTPRequest`` was present.  This exception
        has been shown to be insecure and has been removed.  For more
        information please see
        http://www.djangoproject.com/weblog/2011/feb/08/security/
        http://weblog.rubyonrails.org/2011/2/8/csrf-protection-bypass-in-ruby-on-rails
        """
        token = (self.get_argument("_xsrf", None) or
                 self.request.headers.get("X-Xsrftoken") or
                 self.request.headers.get("X-Csrftoken"))
        if not token:
            raise Exception("HTTPError","'_xsrf' argument missing from POST")
        if self.xsrf_token != token:
            raise Exception("HTTPError","XSRF cookie does not match POST argument")

class BaseTornado(XSRFBaseHandler):
    """
    The default HTTPHandler for webtavern Tornado objects
    """

    def __init__(self, *args, **kwargs):
        """Create the base object for all requests to our Tavern webserver."""

        self.server = server
        super().__init__(*args, **kwargs)

        # Pull a timestamp to use as the canonical time for this request
        self.timestamp = libtavern.utils.gettime(format='timestamp')


        # Before we do anything, see if we have a XSRF cookie set.
        # If not, either set it or abort, depending on the HTTP verb.
        if not self.get_signed_cookie('_xsrf',None) and not self.get_argument('skipxsrf',None):
            self._rewrite_verbs()
            return



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
            self.server.serversettings.settings['webtav']['main_url'] = self.request.protocol + "://" + self.request.host
            self.server.serversettings.saveconfig()
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


        # Determine if we should include our location in the post. (default to no)
        self.include_location = False
        if self.user.include_location or 'include_location' in self.request.arguments:
            if self.request.remote_ip != "127.0.0.1":
                self.include_location = True

        # Set default values for variables we look for.
        self.canon = None
        self.title = None
        self.messages = None
        self.newmessage = "/newmessage"
        self.topic = libtavern.topic.Topic()
        self.displayenvelope = None
        self.scripts = []

        # Add default JS that is needed everywhere.
        self.add_js('jquery.min.js')        # Selector Library
        self.add_js('garlic.min.js')        # Remember user input between refreshes
        self.add_js('colresizable.min.js')  # Slidable columns
        self.add_js('jquery.unveil.min.js') # LazyLoad Images
        self.add_js('mousetrap.min.js')     # Keyboard Shortcuts
        self.add_js('default.min.js')       # Tavern stuff

        if self.useragent['ua_family'] == 'IE' and browser['ua_versions'][0] < 9:
            self.add_js('IE9.js')

    def add_js(self,file=None,files=None):
        """Add a Javascript file to this request"""
        if not files:
            files = []
        if file:
            files.append(file)
        for script in files:
            if script not in self.scripts:
                self.scripts.append(file)

    def load_session(self, AllowGuestKey=True):
        """Load into memory the User class by way of the session cookie.

        Generates a new user (usually guest) if it can't find one.
        """

        # Create a user obj - We'll either make this into a new user, the default user, or an empty user.
        self.user = libtavern.user.User()

        # Load in our saved passkey if it's available.
        if self.get_signed_cookie('passkey'):
            self.user.passkey = self.get_signed_cookie('passkey')

        # Load in our session token if we have one.
        if self.get_signed_cookie('sessionid'):
            result = self.user.load_mongo_by_sessionid(self.get_signed_cookie('sessionid'))
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

        # Save our Passkey. This is the key which allows the user to decrypt their keys.
        # This passkey is never stored serverside.
        if self.user.has_unique_key:
            if self.user.passkey is not None:
                self.set_secure_cookie('passkey', self.user.passkey, httponly=True, max_age=31556952 * 2)
        self.set_secure_cookie('sessionid', self.user.save_session(), httponly=True, max_age=31556952 * 2)

    def setheaders(self):
        """Set various headers that each HTTP response should have."""
        # Add in a random fortune
        self.set_header("X-Fortune", self.server.fortune.random().encode('iso-8859-1', errors='ignore'))

        # Do not allow the content to load in a frame.
        # Should help prevent certain attacks
        self.set_header("X-FRAME-OPTIONS", "DENY")
        self.set_header("FRAME-OPTIONS", "DENY")

        # Don't try to guess content-type.
        # This helps avoid JS sent in an image.
        self.set_header("X-Content-Type-Options", "nosniff")

        # Disable prefetching of content. Since we allow offsite links, this avoids some leakage.
        self.set_header("X-dns-prefetch-control", "off")

        # IE has additional XSS protection.
        # http://msdn.microsoft.com/en-us/library/dd565647%28v=vs.85%29.aspx
        self.set_header("X-XSS-Protection","1; mode=block;")

        # STS header says to always load over HTTPS
        if self.is_secure or self.server.serversettings.settings['webtav']['force_sts'] is True:
            self.set_header("Strict-Transport-Security","max-age=" + self.server.serversettings.settings['webtav']['sts_time'])


        # http://cspisawesome.com/content_security_policies
        # bottle.response.set_header(
        #     "Content-Security-Policy-Report-Only",
        #     "default-src 'self'; script-src 'unsafe-inline' 'unsafe-eval' data 'self'; object-src 'none'; style-src 'self'; img-src *; media-src mediaserver; frame-src " +
        #     self.server.serversettings.settings[
        #         'embedserver'] +
        #     " https://www.youtube.com https://player.vimeo.com; font-src 'self'; connect-src 'self'")


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
        self.topic = libtavern.topic.Topic(self.displayenvelope.dict['envelope']['payload']['topic'])

        self.canon = None
        self.title = self.displayenvelope.dict['envelope']['payload']['subject']
        self.render('View-showmessage.html')

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


    def _rewrite_verbs(self):
        """
        Replaces all verbs is a handler with safe values in the case where a XSRF token is missing.

        Note - This does not overwrite the protection against POST request without matching XSRF tokens.
        That is defined in check_xsrf_cookie()
        """
        def retryget(*args,**kwargs):
            _ = self.xsrf_token
            argsdict = {'skipxsrf' : True}
            newurl = tornado.httputil.url_concat(self.request.uri, argsdict)
            self.write('<!--# include virtual="' + newurl + '" wait="yes" -->')
        def errorpost(*args,**kwargs):
            raise weberror(short="You're not supposed to do that ;)",long="The URL you that you tried to load requires authentication, but we didn't receive any. <br> This could be due to a coding error, a network problem such as a proxy server, or someone trying to trick you into clicking a link. ",code=403)
        def notimplemented(*args,**kwargs):
            raise HTTPError(405)
        setattr(self,'get',retryget)
        setattr(self,'post',errorpost)
        setattr(self,'head',notimplemented)
        setattr(self,'delete',notimplemented)
        setattr(self,'patch',notimplemented)
        setattr(self,'put',notimplemented)
        setattr(self,'options',notimplemented)

    def get_template_namespace(self):
        """
        Provides a dict of variables/functions that are available to templates.

        :returns: dict
        """
        namespace = dict(
            handler=self,
            request=self.request,
            locale=self.locale,
            _=self.locale.translate,
            xsrf_form_html=self.xsrf_form_html,
            utils=libtavern.utils,
            url_for=self.server.url_for,
            Topic=libtavern.topic.Topic,
        )
        namespace.update(self.ui)
        return namespace


    def requires_acct(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Pull in the `self` argument, so we can access members
            handler = args[0]
            handler.server.logger.debug("This function requires a unique acct")
            if not handler.user.has_unique_key or not handler.user.passkey:
                handler.server.logger.debug("The user now has one ;)")
                handler.user.ensure_keys(AllowGuestKey=False)
                handler.save_session()
            return f(*args, **kwargs)
        return decorated


class BaseFlask(webtav.flasknado.Flasknado,BaseTornado):
    """
    Create a basic Flask object which looks and smells very much like a Tornado object.
    Pass through a copy of our Tornado app.
    """
    def __init__(self,*args,**kwargs):
        super().__init__(*args, **kwargs)


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

class FlaskHandler(XSRFBaseHandler):
    """A `RequestHandler` instead calls Flask. This is needed so that we can properly load our own _XSRF records.
    """
    def initialize(self, fallback):
        self.fallback = fallback

    def prepare(self):
        self.fallback(self.request)
        self._finished = True


