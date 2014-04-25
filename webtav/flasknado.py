import hashlib
import base64
import hmac
import time
import re
import flask
from flask.views import MethodView
from tornado.escape import utf8, _unicode
import tornado.web
from tornado.util import bytes_type, import_object, ObjectDict, raise_exc_info, unicode_type
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

    def set_cookie(self,name,value,*args,**kwargs):
        """Sets the given cookie name/value with the given options."""
        self.response.set_cookie(name, value,*args,**kwargs)

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

    def __init__(self,*args,**kwargs):
        """Create the base object for all requests to our Tavern webserver."""
        self.server = server

        self.response = flask.make_response()
        # Create a Tornado-style self.request, for compatibility.
        self.request = tornado.wsgi.HTTPRequest(flask.request.environ)
        # Retrieve our carefully stored Tornado app server.
        super().__init__(*args,request=self.request,application=flask.current_app.tornado,**kwargs)

_create_signature = tornado.web._create_signature
_time_independent_equals = tornado.web._time_independent_equals
create_signed_value = tornado.web.create_signed_value
decode_signed_value = tornado.web.decode_signed_value
