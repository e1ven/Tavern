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
        self.write(self.render_string('templates/header.html',title="Page not Found",username=self.username))
        self.write(self.render_string('templates/404.html'))
        self.write(self.render_string('templates/footer.html'))


class FrontPageHandler(BaseHandler):
    def get(self):
        self.getvars()
        self.write(self.render_string('templates/header.html',title="Welcome to Pluric!",username=self.username))
        self.write("Hello, world")
        self.write(self.render_string('templates/footer.html'))

class RegisterHandler(BaseHandler):
    def get(self):
        self.getvars()
        self.write(self.render_string('templates/header.html',title="Register for an Account",username=self.username))
        self.write(self.render_string('templates/registerform.html'))
        self.write(self.render_string('templates/footer.html'))
    def post(self):
        self.getvars()
        self.write(self.render_string('header.html',newmail=0,title='Register for an account',uid=self.uid,user=self.name,ustatus=self.ustatus))
        client_newuser =  unicode(tornado.escape.xhtml_escape(self.get_argument("name")),'utf8')
        client_newpass =  unicode(tornado.escape.xhtml_escape(self.get_argument("pass")),'utf8')
        client_newpass2 =  unicode(tornado.escape.xhtml_escape(self.get_argument("pass2")),'utf8')
        client_newemail = unicode(tornado.escape.xhtml_escape(self.get_argument("email")),'utf8')

        if client_newpass != client_newpass2:
            self.write("I'm sorry, your passwords don't match.") 
            return

        db = psycopg2.connect("dbname='lonava' user='YOURUSER' host='localhost' password='YOURPASS'")
        cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        #Make sure this email is unused
        cur.execute("select count(*) as count from usrs where upper(email) = upper(%s);",[client_newemail])
        count = cur.fetchone()['count']

        if count != 0:
            self.write("I'm sorry, this email address has already been used.")  
            return
        else:
            hashed = bcrypt.hashpw(client_newpass, bcrypt.gensalt())
            cur.execute("insert into usrs (name,password,email) values (%s,%s,%s) returning usrid;",[client_newuser,hashed,client_newemail])
            ## Copy in Default Channels
            newid = cur.fetchone()[0]
    
            #defaultchans = ({"usr":str(newid), "chan":"1"})    
            cur.execute("select subbedchan from usrsubs where usr = 0")
            rows = cur.fetchall()
            for row in rows:
                cur.execute("insert into usrsubs(usr,subbedchan) values (%s,%s)",[newid,row['subbedchan']])
            self.write("User# " + str(newid) + " Created. You are now logged in. <br><a href='/' class='ul'>Return to main page</a>.")  
    
            #Go Ahead and Log you in by default

            usrid = str(newid)
            self.set_secure_cookie("usrid", usrid)
            cur.execute('select name FROM usrs WHERE usrid = %s;', [usrid])
            row = cur.fetchone()
            self.set_secure_cookie("name", row['name'])
            self.name = row['name']

            #set cookie with hidden story votes
            cur.execute('select * from storyvotes where usr = %s order by storyvoteid desc limit 100;',[self.uid])
            rows = cur.fetchall()
            cookiearry = "["
            for row in rows:
                cookiearry = cookiearry + '"' + "storyid||" + str(row['story']) + "||" + str(row['pointchange']) + '",'

            #set cookie for replies
            cur.execute('select * from replyvotes where usr = %s order by replyvoteid desc limit 100;',[self.uid])
            rows = cur.fetchall()
            for row in rows:
                cookiearry = cookiearry + '"' + "replyid||" + str(row['reply']) + "||" + str(row['pointchange']) + '",'

            cookiearry = cookiearry + '"storyid||0||1"]'

            self.set_cookie("hidden-post-votes",cookiearry)
            self.redirect("/")



            db.commit() 
            db.close()
            self.redirect("/")





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
        (r"/" ,FrontPageHandler),
        (r"/register" ,RegisterHandler),
        (r"/(.*)", NotFoundHandler)
    ], **settings)
    
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
