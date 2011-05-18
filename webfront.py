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
from Envelope import Envelope
from collections import OrderedDict
import pymongo
from tornado.options import define, options
from server import server
import GeoIP
import pprint
from keys import *
from User import User
from gridfs import GridFS
import hashlib


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
        self.maxposts = self.get_secure_cookie("maxposts")
        if self.maxposts is None:
            self.maxposts = 20
        else:
            self.maxposts = int(self.maxposts)
            
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
        toptopics = []
        self.write(self.render_string('templates/header.html',title="Welcome to Pluric!",username=self.username))

        #db.topiclist.find().sort({value : 1})
        for topic in server.mongo['topiclist'].find(limit=10).sort('value',-1):
            toptopics.append(topic)
            
        self.write(self.render_string('templates/frontpage.html',toptopics=toptopics))
        self.write(self.render_string('templates/footer.html'))

class TopicHandler(BaseHandler):        
    def get(self,topic):
        self.getvars()
        client_topic = tornado.escape.xhtml_escape(topic)
        envelopes = []
        self.write(self.render_string('templates/header.html',title="Pluric :: " + client_topic,username=self.username))
       
        for envelope in server.mongo['envelopes'].find({'pluric_envelope.message.topictag' : client_topic },limit=self.maxposts):
                envelopes.append(envelope)
        self.write(self.render_string('templates/messages-in-topic.html',envelopes=envelopes))
        self.write(self.render_string('templates/footer.html'))
        
class MessageHandler(BaseHandler):        
    def get(self,message):
        self.getvars()
        client_message_id = tornado.escape.xhtml_escape(message)
        
        envelope = server.mongo['envelopes'].find_one({'pluric_envelope.message_sha512' : client_message_id })
                                        
        self.write(self.render_string('templates/header.html',title="Pluric :: " + envelope['pluric_envelope']['message']['subject'],username=self.username))

        self.write(self.render_string('templates/single-message.html',envelope=envelope))
        self.write(self.render_string('templates/footer.html'))




class RegisterHandler(BaseHandler):
    def get(self):
        self.getvars()
        self.write(self.render_string('templates/header.html',title="Register for an Account",username=self.username))
        self.write(self.render_string('templates/registerform.html'))
        self.write(self.render_string('templates/footer.html'))
    def post(self):
        self.getvars()
        self.write(self.render_string('templates/header.html',title='Register for an account',username=""))

        client_newuser =  tornado.escape.xhtml_escape(self.get_argument("username"))
        client_newpass =  tornado.escape.xhtml_escape(self.get_argument("pass"))
        client_newpass2 = tornado.escape.xhtml_escape(self.get_argument("pass2"))
        client_newemail = tornado.escape.xhtml_escape(self.get_argument("email"))

        if client_newpass != client_newpass2:
            self.write("I'm sorry, your passwords don't match.") 
            return

        
        users_with_this_email = server.mongo['users'].find({"email":client_newemail})
        if users_with_this_email.count() > 0:
            self.write("I'm sorry, this email address has already been used.")  
            return
            
        users_with_this_username = server.mongo['users'].find({"username":client_newuser})
        if users_with_this_username.count() > 0:
            self.write("I'm sorry, this username has already been taken.")  
            return    
            
        else:
            hashedpass = bcrypt.hashpw(client_newpass, bcrypt.gensalt(12))
            u = User()
            u.generate(hashedpass=hashedpass,username=client_newuser,email=client_newemail)
            u.UserSettings['maxposts'] = 20
            u.savemongo()
            
            self.set_secure_cookie("username",client_newuser,httponly=True)
            self.set_secure_cookie("maxposts",str(u.UserSettings['maxposts']),httponly=True)
            
            self.redirect("/")


class LoginHandler(BaseHandler):
    def get(self):
        self.getvars()        
        self.write(self.render_string('templates/header.html',title="Login to your account",username=self.username))
        self.write(self.render_string('templates/loginform.html'))
        self.write(self.render_string('templates/footer.html'))
    def post(self):
        self.getvars()
        self.write(self.render_string('templates/header.html',title='Login to your account',username=""))

        client_username =  tornado.escape.xhtml_escape(self.get_argument("username"))
        client_password =  tornado.escape.xhtml_escape(self.get_argument("pass"))

        print server.mongo['users'].find({"username":client_username}).count()
        user = server.mongo['users'].find_one({"username":client_username})
        if user is not None:
            u = User()
            u.load_mongo_by_username(username=client_username)
            if bcrypt.hashpw(client_password,user['hashedpass']) == user['hashedpass']:
                self.set_secure_cookie("username",user['username'],httponly=True)
                self.set_secure_cookie("maxposts",str(u.UserSettings['maxposts']),httponly=True)
                self.redirect("/")
                return

        self.write("I'm sorry, we don't have that username/password combo on file.")

class LogoutHandler(BaseHandler):
     def post(self):
         self.clear_cookie("username")
         self.redirect("/")

class NewmessageHandler(BaseHandler):
    def get(self):
         self.getvars()
         self.write(self.render_string('templates/header.html',title="Login to your account",username=self.username))
         self.write(self.render_string('templates/newmessageform.html'))
         self.write(self.render_string('templates/footer.html'))

    def post(self):
        self.getvars()
        if self.username == "Guest":
            self.write("You must be logged in to do this.")
            return
        
        # self.write(self.render_string('templates/header.html',title='Post a new message',username=self.username))

        client_topic =  tornado.escape.xhtml_escape(self.get_argument("topic"))
        client_subject =  tornado.escape.xhtml_escape(self.get_argument("subject"))
        client_body =  tornado.escape.xhtml_escape(self.get_argument("body"))
        client_include_loc = tornado.escape.xhtml_escape(self.get_argument("include_location"))
        #Use this flag to know if we successfully stored or not.
        stored = False        
        try:
            #I've testing including this var via the page directly. 
            #It's safe to trust this path, it seems.
            #All the same, let's strip out all but the basename.
            
            client_filepath =  tornado.escape.xhtml_escape(self.get_argument("attached_file.path"))
            client_filetype =  tornado.escape.xhtml_escape(self.get_argument("attached_file.content_type"))
            client_filename =  tornado.escape.xhtml_escape(self.get_argument("attached_file.name"))
            client_filesize =  tornado.escape.xhtml_escape(self.get_argument("attached_file.size"))
            
            fs_basename = os.path.basename(client_filepath)
            fullpath = server.ServerSettings['upload-dir'] + "/" + fs_basename
       
            #Hash the file in chunks
            sha512 = hashlib.sha512()
            with open(fullpath,'rb') as f: 
                for chunk in iter(lambda: f.read(128 * sha512.block_size), ''): 
                     sha512.update(chunk)
            digest =  sha512.hexdigest()
            
            if not server.bin_GridFS.exists(filename=digest):
                with open(fullpath) as localfile:
                    oid = server.bin_GridFS.put(localfile, filename=digest)
                    stored = True
            else:
                stored = True
            #Create a message binary.    
            bin = Envelope.binary(hash=digest)
            #Set the Filesize. Clients can't trust it, but oh-well.
            bin.dict['filesize_hint'] =  client_filesize
            bin.dict['content_type'] = client_filetype
            bin.dict['filename'] = client_filename
            
            #Don't keep spare copies on the webservers
            os.remove(fullpath)
            
        except:
            client_filepath = None
                    
        e = Envelope()
        topics = []
        topics.append(client_topic)
        e.message.dict['topictag'] = topics
        e.message.dict['body'] = client_body
        e.message.dict['subject'] = client_subject
        
        #Instantiate the user who's currently logged in
        user = server.mongo['users'].find_one({"username":self.username})        
        u = User()
        u.load_mongo_by_pubkey(user['pubkey'])
        
        if stored is True:
            e.message.dict['binary'] = bin.dict

        e.message.dict['author'] = OrderedDict()
        e.message.dict['author']['from'] = u.UserSettings['pubkey']
        
        e.message.dict['author']['client'] = "Pluric Web frontend Pre-release 0.1"
        if client_include_loc == "on":
            gi = GeoIP.open("/usr/local/share/GeoIP/GeoIPCity.dat",GeoIP.GEOIP_STANDARD)
            ip = self.request.remote_ip
            
            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"
                
            gir = gi.record_by_name(ip)
            e.message.dict['coords'] = str(gir['latitude']) + "," + str(gir['longitude'])
        
        #Sign this bad boy
        usersig = u.Keys.signstring(e.message.text())
        e.dict['sender_signature'] = usersig
        
        #Send to the server
        server.receiveEnvelope(e.text())
        
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
        (r"/login" ,LoginHandler),
        (r"/logout" ,LogoutHandler), 
        (r"/newmessage" ,NewmessageHandler), 
        (r"/uploadnewmessage" ,NewmessageHandler), 
        (r"/topictag/(.*)" ,TopicHandler), 
        (r"/message/(.*)" ,MessageHandler),    
        (r"/(.*)", NotFoundHandler)
    ], **settings)
    
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
