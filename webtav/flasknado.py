import hashlib
import base64
import hmac
import time
import re
import flask
from flask.views import MethodView
from tornado.escape import utf8, _unicode
import tornado.escape
import libtavern.server

server = libtavern.server.Server()


class Flasknado(MethodView):
    """
    Create a Flask Handler which looks and smells like Tornado.
    """

    _remove_control_chars_regex = re.compile(r"[\x00-\x08\x0e-\x1f]")

    def get_status(self):
        """Returns the status code for our response."""
        return self.response.status_code

    def set_header(self, name, value):
        """Sets the given response header name and value."""
        self.response.headers[name] = value

    def add_header(self, name, value):
        """
        Adds the given response header and value.
        """
        self.response.headers.add(name, value)

    def clear_header(self, name):
        """Clears an outgoing header, undoing a previous `set_header` call.

        Note that this method does not apply to multi-valued headers
        set by `add_header`.
        """
        if name in self.response.headers:
            del self.response.headers[name]


    _ARG_DEFAULT = []

    def get_argument(self, name, default=_ARG_DEFAULT, strip=True):
        """Returns the value of the argument with the given name.

        If default is not provided, the argument is considered to be
        required, and we raise a `MissingArgumentError` if it is missing.

        If the argument appears in the url more than once, we return the
        last value.

        The returned value is always unicode.
        """
        return self._get_argument(name, default, self.request.arguments, strip)

    def get_arguments(self, name, strip=True):
        """Returns a list of the arguments with the given name.

        If the argument is not present, returns an empty list.

        The returned values are always unicode.
        """
        return self._get_arguments(name, self.request.arguments, strip)

    def get_body_argument(self, name, default=_ARG_DEFAULT, strip=True):
        """Returns the value of the argument with the given name
        from the request body.

        If default is not provided, the argument is considered to be
        required, and we raise a `MissingArgumentError` if it is missing.

        If the argument appears in the url more than once, we return the
        last value.

        The returned value is always unicode.

        .. versionadded:: 3.2
        """
        return self._get_argument(name, default, self.request.body_arguments, strip)

    def get_body_arguments(self, name, strip=True):
        """Returns a list of the body arguments with the given name.

        If the argument is not present, returns an empty list.

        The returned values are always unicode.

        .. versionadded:: 3.2
        """
        return self._get_arguments(name, self.request.body_arguments, strip)

    def get_query_argument(self, name, default=_ARG_DEFAULT, strip=True):
        """Returns the value of the argument with the given name
        from the request query string.

        If default is not provided, the argument is considered to be
        required, and we raise a `MissingArgumentError` if it is missing.

        If the argument appears in the url more than once, we return the
        last value.

        The returned value is always unicode.

        .. versionadded:: 3.2
        """
        return self._get_argument(name, default, self.request.query_arguments, strip)

    def get_query_arguments(self, name, strip=True):
        """Returns a list of the query arguments with the given name.

        If the argument is not present, returns an empty list.

        The returned values are always unicode.

        .. versionadded:: 3.2
        """
        return self._get_arguments(name, self.request.query_arguments, strip)


    def _get_argument(self, name, default, source, strip=True):
        args = self._get_arguments(name, source, strip=strip)
        if not args:
            if default is self._ARG_DEFAULT:
                raise Exception('MissingArgumentError',name)
            return default
        return args[-1]

    def _get_arguments(self, name, source, strip=True):
        values = []
        for v in source.get(name, []):
            v = self.decode_argument(v, name=name)
            if isinstance(v, unicode_type):
                # Get rid of any weird control chars (unless decoding gave
                # us bytes, in which case leave it alone)
                v = self._remove_control_chars_regex.sub(" ", v)
            if strip:
                v = v.strip()
            values.append(v)
        return values

    def decode_argument(self, value, name=None):
        """Decodes an argument from the request.

        The argument has been percent-decoded and is now a byte string.
        By default, this method decodes the argument as utf-8 and returns
        a unicode string, but this may be overridden in subclasses.

        This method is used as a filter for both `get_argument()` and for
        values extracted from the url and passed to `get()`/`post()`/etc.

        The name of the argument is provided if known, but may be None
        (e.g. for unnamed groups in the url regex).
        """
        try:
            return _unicode(value)
        except UnicodeDecodeError:
            raise HTTPError(400, "Invalid unicode in %s: %r" %
                            (name or "url", value[:40]))

    @property
    def cookies(self):
        """An alias for `self.request.cookies <.httpserver.HTTPRequest.cookies>`."""
        return self.request.cookies

    def get_cookie(self, name, default=None):
        """Gets the value of the cookie with the given name, else default."""
        if self.request.cookies is not None and name in self.request.cookies:
            return self.request.cookies[name].value
        return default


    def set_cookie(name,value,**kwargs):
        """Sets the given cookie name/value with the given options."""
        self.response.set_cookie(name, value,**kwargs)
    
    def clear_cookie(self, name, path="/", domain=None):
        """Deletes the cookie with the given name.

        Due to limitations of the cookie protocol, you must pass the same
        path and domain to clear a cookie as were used when that cookie
        was set (but there is no way to find out on the server side
        which values were used for a given cookie).
        """
        expires = datetime.datetime.utcnow() - datetime.timedelta(days=365)
        self.set_cookie(name, value="", path=path, expires=expires,
                        domain=domain)

    def clear_all_cookies(self, path="/", domain=None):
        """Deletes all the cookies the user sent with this request.

        See `clear_cookie` for more information on the path and domain
        parameters.

        .. versionchanged:: 3.2

           Added the ``path`` and ``domain`` parameters.
        """
        for name in self.request.cookies:
            self.clear_cookie(name, path=path, domain=domain)

    def set_secure_cookie(name,value,**kwargs):
        """Signs and timestamps a cookie so it cannot be forged.

        You must specify the ``cookie_secret`` setting in your Tornado 
        Application to use this method. It should be a long, random sequence
        of bytes to be used as the HMAC secret for the signature.

        To read a cookie set with this method, use `get_secure_cookie()`.

        Note that the ``expires_days`` parameter sets the lifetime of the
        cookie in the browser, but is independent of the ``max_age_days``
        parameter to `get_secure_cookie`.

        Secure cookies may contain arbitrary byte values, not just unicode
        strings (unlike regular cookies)
        """
        signed = self.create_signed_value(name, value)
        self.response.set_cookie(name, signed, **kwargs)

    def create_signed_value(self, name, value):
        """Signs and timestamps a string so it cannot be forged.

        Normally used via set_secure_cookie, but provided as a separate
        method for non-cookie uses.  To decode a value not stored
        as a cookie use the optional value argument to get_secure_cookie.
        """
        return create_signed_value(secret=server.serversettings.settings['webtav']['cookie_secret'],name=name, value=value)


    def get_secure_cookie(self, name, value=None, max_age_days=31):
        """Returns the given signed cookie if it validates, or None.

        The decoded cookie value is returned as a byte string (unlike
        `get_cookie`).
        """
        if value is None:
            value = self.get_cookie(name)
        return decode_signed_value(secret=server.serversettings.settings['webtav']['cookie_secret'],name=name, value=value, max_age_days=max_age_days)


    def redirect(self, url, permanent=False, status=None):
        """Sends a redirect to the given (optionally relative) URL.

        If the ``status`` argument is specified, that value is used as the
        HTTP status code; otherwise either 301 (permanent) or 302
        (temporary) is chosen based on the ``permanent`` argument.
        The default is 302 (temporary).
        """
        if self._headers_written:
            raise Exception("Cannot redirect after headers have been written")
        if status is None:
            status = 301 if permanent else 302
        self.response = flask.redirect(location=url,code=status)

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
        token = self.get_secure_cookie('_xsrf',None)
        if not token:
            # Generate a token, save it to a cookie.
            token = libtavern.utils.randstr(16)
            self.set_secure_cookie(name="_xsrf",value=token,httponly=True, max_age=31556952 * 2)
        else:
            token = token.decode('utf-8')
        self._xsrf_token = token
        return self._xsrf_token

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

    def xsrf_form_html(self):
        """An HTML ``<input/>`` element to be included with all POST forms.

        It defines the ``_xsrf`` input value, which we check on all POST
        requests to prevent cross-site request forgery. If you have set
        the ``xsrf_cookies`` application setting, you must include this
        HTML within all of your HTML forms.

        In a template, this method should be called with ``{% module
        xsrf_form_html() %}``

        See `check_xsrf_cookie()` above for more information.
        """
        return '<input type="hidden" name="_xsrf" value="' + \
            tornado.escape.xhtml_escape(self.xsrf_token) + '"/>'


    def __init__(self,*args,**kwargs):
        """Create the base object for all requests to our Tavern webserver."""
        self.server = server

        self.response = flask.make_response()
        # Create a Tornado-style self.request, for compatibility.
        self.request = tornado.wsgi.HTTPRequest(flask.request.environ)
        # Retrieve our carefully stored Tornado app server.
        super().__init__(*args,request=self.request,application=flask.current_app.tornado,**kwargs)


if hasattr(hmac, 'compare_digest'):  # python 3.3
    _time_independent_equals = hmac.compare_digest
else:
    def _time_independent_equals(a, b):
        if len(a) != len(b):
            return False
        result = 0
        if isinstance(a[0], int):  # python3 byte strings
            for x, y in zip(a, b):
                result |= x ^ y
        else:  # python2
            for x, y in zip(a, b):
                result |= ord(x) ^ ord(y)
        return result == 0

def create_signed_value(secret, name, value):
    timestamp = utf8(str(int(time.time())))
    value = base64.b64encode(utf8(value))
    signature = _create_signature(secret, name, value, timestamp)
    value = b"|".join([value, timestamp, signature])
    return value

def decode_signed_value(secret, name, value, max_age_days=31):
    if not value:
        return None
    parts = utf8(value).split(b"|")
    if len(parts) != 3:
        return None
    signature = _create_signature(secret, name, parts[0], parts[1])
    if not _time_independent_equals(parts[2], signature):
        return None
    timestamp = int(parts[1])
    if timestamp < time.time() - max_age_days * 86400:
        return None
    if timestamp > time.time() + 31 * 86400:
        # _cookie_signature does not hash a delimiter between the
        # parts of the cookie, so an attacker could transfer trailing
        # digits from the payload to the timestamp without altering the
        # signature.  For backwards compatibility, sanity-check timestamp
        # here instead of modifying _cookie_signature.
        return None
    if parts[1].startswith(b"0"):
        return None
    try:
        return base64.b64decode(parts[0])
    except Exception:
        return None

def _create_signature(secret, *parts):
    hash = hmac.new(utf8(secret), digestmod=hashlib.sha1)
    for part in parts:
        hash.update(utf8(part))
    return utf8(hash.hexdigest())