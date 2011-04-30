#!/usr/bin/env python
#
# Copyright 2011 Pluric


import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.escape
import bcrypt
import time
import datetime
import os
import markdown
import imghdr 
import random
import socket
import pymongo
import json
from collections import OrderedDict
import pymongo
from tornado.options import define, options
from server import server,User




import re
try: 
   from hashlib import md5 as md5_func
except ImportError:
   from md5 import new as md5_func
import NofollowExtension


define("port", default=8080, help="run on the given port", type=int)


            

#Autolink from http://greaterdebater.com/blog/gabe/post/4
def autolink(html):
    # match all the urls
    # this returns a tuple with two groups
    # if the url is part of an existing link, the second element
    # in the tuple will be "> or </a>
    # if not, the second element will be an empty string
    urlre = re.compile("(\(?https?://[-A-Za-z0-9+&@#/%?=~_()|!:,.;]*[-A-Za-z0-9+&@#/%=~_()|])(\">|</a>)?")
    urls = urlre.findall(html)
    clean_urls = []

    # remove the duplicate matches
    # and replace urls with a link
    for url in urls:
        # ignore urls that are part of a link already
        if url[1]: continue
        c_url = url[0]
        # ignore parens if they enclose the entire url
        if c_url[0] == '(' and c_url[-1] == ')':
            c_url = c_url[1:-1]

        if c_url in clean_urls: continue # We've already linked this url

        clean_urls.append(c_url)
        # substitute only where the url is not already part of a
        # link element.
        html = re.sub("(?<!(=\"|\">))" + re.escape(c_url), 
                      "<a rel=\"nofollow\" href=\"" + c_url + "\">" + c_url + "</a>",
                      html)
    return html

# Github flavored Markdown, from http://gregbrown.co.nz/code/githib-flavoured-markdown-python-implementation/
def gfm(text):
    # Extract pre blocks.
    extractions = {}
    def pre_extraction_callback(matchobj):
        digest = md5(matchobj.group(0)).hexdigest()
        extractions[digest] = matchobj.group(0)
        return "{gfm-extraction-%s}" % digest
        pattern = re.compile(r'<pre>.*?</pre>', re.MULTILINE | re.DOTALL)
        text = re.sub(pattern, pre_extraction_callback, text)

    # Prevent foo_bar_baz from ending up with an italic word in the middle.
    def italic_callback(matchobj):
        s = matchobj.group(0)
        if list(s).count('_') >= 2:
            return s.replace('_', '\_')
        return s
        text = re.sub(r'^(?! {4}|\t)\w+_\w+_\w[\w_]*', italic_callback, text)

    # In very clear cases, let newlines become <br /> tags.
    def newline_callback(matchobj):
        if len(matchobj.group(1)) == 1:
            return matchobj.group(0).rstrip() + '  \n'
        else:
            return matchobj.group(0)
        pattern = re.compile(r'^[\w\<][^\n]*(\n+)', re.MULTILINE)
        text = re.sub(pattern, newline_callback, text)

    # Insert pre block extractions.
    def pre_insert_callback(matchobj):
        return '\n\n' + extractions[matchobj.group(1)]
        text = re.sub(r'{gfm-extraction-([0-9a-f]{32})\}', pre_insert_callback, text)

    return text



class BaseHandler(tornado.web.RequestHandler):
    def getvars(self):
        self.username = self.get_secure_cookie("username")
        if self.username is None:
            self.username = "Guest"

        return str(self.username)
           
    
class FancyDateTimeDelta(object):
    """
    Format the date / time difference between the supplied date and
    the current time using approximate measurement boundaries
    """

    def __init__(self, dt):
        now = datetime.datetime.now()
        delta = now - dt
        self.year = delta.days / 365
        self.month = delta.days / 30 - (12 * self.year)
        if self.year > 0:
            self.day = 0
        else: 
            self.day = delta.days % 30
        self.hour = delta.seconds / 3600
        self.minute = delta.seconds / 60 - (60 * self.hour)
        self.second = delta.seconds - ( self.hour * 3600) - (60 * self.minute) 
        self.millisecond = delta.microseconds / 1000

    def format(self):
        #Round down. People don't want the exact time.
        #For exact time, reverse array.
        fmt = ""
        for period in ['millisecond','second','minute','hour','day','month','year']:
            value = getattr(self, period)
            if value:
                if value > 1:
                    period += "s"

                fmt = str(value) + " " + period
        return fmt + " ago"
    



class NotFoundHandler(BaseHandler):
    def get(self,whatever):
        self.getvars()
        print ("---")
        self.write(self.render_string('templates/header.html',uid=self.username))
        self.write(self.render_string('templates/404.html'))
        self.write(self.render_string('templates/footer.html'))


class PageHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")




def main():
    tornado.options.parse_command_line()
    # timeout in seconds
    timeout = 10
    socket.setdefaulttimeout(timeout)
    print "Starting Web Frontend for " + server.ServerSettings['hostname']
            
    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "cookie_secret": "7cxqGjRMzxv7E9Vxq2mnXalZbeUhaoDgnoTSvn0B",
        "login_url": "/login",
        "xsrf_cookies": True,
    }
    application = tornado.web.Application([
        (r"/" ,PageHandler),
        (r"/(.*)", NotFoundHandler)
    ], **settings)
    
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
