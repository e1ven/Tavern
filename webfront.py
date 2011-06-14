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
from PIL import Image
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
import urllib

import re
try: 
   from hashlib import md5 as md5_func
except ImportError:
   from md5 import new as md5_func
import NofollowExtension


define("port", default=8080, help="run on the given port", type=int)




class BaseHandler(tornado.web.RequestHandler):
    def getvars(self):
        self.username = self.get_secure_cookie("username")
        if self.username is None:
            self.username = "Guest"
            self.loggedin = False
        else:
            self.loggedin = True
        self.maxposts = self.get_secure_cookie("maxposts")
        if self.maxposts is None:
            self.maxposts = 20
        else:
            self.maxposts = int(self.maxposts)
        #Toggle this.
        self.include_loc = "on"  
           
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
        self.write(self.render_string('templates/header.html',title="Page not Found",username=self.username,loggedin=self.loggedin))
        self.write(self.render_string('templates/404.html'))
        self.write(self.render_string('templates/footer.html'))


class FrontPageHandler(BaseHandler):        
    def get(self):
        self.getvars()
        toptopics = []
        self.write(self.render_string('templates/header.html',title="Welcome to Pluric!",username=self.username,loggedin=self.loggedin))

        #db.topiclist.find().sort({value : 1})
        for topic in server.mongos['default']['topiclist'].find(limit=10).sort('value',-1):
            toptopics.append(topic)
            
        self.write(self.render_string('templates/frontpage.html',toptopics=toptopics))
        self.write(self.render_string('templates/footer.html'))

class TopicHandler(BaseHandler):        
    def get(self,topic):
        self.getvars()
        client_topic = tornado.escape.xhtml_escape(topic)
        envelopes = []
        self.write(self.render_string('templates/header.html',title="Pluric :: " + client_topic,username=self.username,loggedin=self.loggedin))
       
        for envelope in server.mongos['default']['envelopes'].find({'envelope.payload.topictag' : client_topic },limit=self.maxposts):
                envelopes.append(envelope)
        self.write(self.render_string('templates/messages-in-topic.html',envelopes=envelopes))
        self.write(self.render_string('templates/footer.html'))
        
class MessageHandler(BaseHandler):        
    def get(self,message):
        self.getvars()
        client_message_id = tornado.escape.xhtml_escape(message)
        
        envelope = server.mongos['default']['envelopes'].find_one({'envelope.payload_sha512' : client_message_id })

        u = User()
        u.load_mongo_by_username(username=self.username)
        usertrust = u.gatherTrust(envelope['envelope']['payload']['author']['pubkey'])
        messagerating = u.getRatings(client_message_id)
        
        
        #Create two lists- One of all attachments, and one of images.
        attachmentList = []
        displayableAttachmentList = []
        if envelope['envelope']['payload'].has_key('binaries'):
            for binary in envelope['envelope']['payload']['binaries']:
                if binary.has_key('sha_512'):
                    fname = binary['sha_512']
                    attachment = server.bin_GridFS.get_version(filename=fname)
                    if not binary.has_key('filename'):
                        binary['filename'] = "unknown_file"
                    #In order to display an image, it must be of the right MIME type, the right size, it must open in
                    #Python and be a valid image.
                    attachmentdesc = {'sha_512' : binary['sha_512'], 'filename' : binary['filename'], 'filesize' : attachment.length }
                    attachmentList.append(attachmentdesc)
                    if attachment.length < 512000:
                        if binary.has_key('content_type'):
                            if binary['content_type'].rsplit('/')[0].lower() == "image":
                                imagetype = imghdr.what('ignoreme',h=attachment.read())
                                acceptable_images = ['gif','jpeg','jpg','png','bmp']
                                if imagetype in acceptable_images:
                                    #If we pass -all- the tests, create a thumb once.
                                    if not server.bin_GridFS.exists(filename=binary['sha_512'] + "-thumb"):
                                        attachment.seek(0) 
                                        im = Image.open(attachment)
                                        img_width, img_height = im.size
                                        if ((img_width > 150) or (img_height > 150)): 
                                            im.thumbnail((150, 150), Image.ANTIALIAS)
                                        thumbnail = server.bin_GridFS.new_file(filename=binary['sha_512'] + "-thumb")
                                        im.save(thumbnail,format='png')    
                                        thumbnail.close()
                                    displayableAttachmentList.append(binary['sha_512'])
        if envelope['envelope']['payload'].has_key('formatting'):
                formattedbody = server.formatText(text=envelope['envelope']['payload']['body'],formatting=envelope['envelope']['payload']['formatting'])
        else:    
                formattedbody = server.formatText(text=envelope['envelope']['payload']['body'])
                

            
        self.write(self.render_string('templates/header.html',title="Pluric :: " + envelope['envelope']['payload']['subject'],username=self.username,loggedin=self.loggedin))
        self.write(self.render_string('templates/single-message.html',formattedbody=formattedbody,messagerating=messagerating,usertrust=usertrust,attachmentList=attachmentList,displayableAttachmentList=displayableAttachmentList,envelope=envelope))
        self.write(self.render_string('templates/footer.html'))

class PrivateMessageHandler(BaseHandler):        
    def get(self,message):
        self.getvars()
        client_message_id = tornado.escape.xhtml_escape(message)

        envelope = server.mongos['default']['envelopes'].find_one({'envelope.payload_sha512' : client_message_id })

        u = User()
        u.load_mongo_by_username(username=self.username)
        usertrust = u.gatherTrust(envelope['envelope']['payload']['author']['pubkey'])
        
        envelope['envelope']['payload']['body'] = u.Keys.decryptToSelf(envelope['envelope']['payload']['body'])
        envelope['envelope']['payload']['subject'] = u.Keys.decryptToSelf(envelope['envelope']['payload']['subject'])

        formattedbody = autolink(markdown.markdown(gfm(envelope['envelope']['payload']['body'])))
        self.write(self.render_string('templates/header.html',title="Pluric :: " + envelope['envelope']['payload']['subject'],username=self.username,loggedin=self.loggedin))
        self.write(self.render_string('templates/singleprivatemessage.html',formattedbody=formattedbody,usertrust=usertrust,envelope=envelope))
        self.write(self.render_string('templates/footer.html'))




class RegisterHandler(BaseHandler):
    def get(self):
        self.getvars()
        self.write(self.render_string('templates/header.html',title="Register for an Account",username=self.username,loggedin=self.loggedin))
        self.write(self.render_string('templates/registerform.html'))
        self.write(self.render_string('templates/footer.html'))
    def post(self):
        self.getvars()
        self.write(self.render_string('templates/header.html',title='Register for an account',username="",loggedin=False))

        client_newuser =  tornado.escape.xhtml_escape(self.get_argument("username"))
        client_newpass =  tornado.escape.xhtml_escape(self.get_argument("pass"))
        client_newpass2 = tornado.escape.xhtml_escape(self.get_argument("pass2"))
        if "email" in self.request.arguments:
            client_email = tornado.escape.xhtml_escape(self.get_argument("email"))
            if client_email == "":
                client_email = None
        else:
            client_email = None     
            
        if client_newpass != client_newpass2:
            self.write("I'm sorry, your passwords don't match.") 
            return

        if client_email is not None:
            users_with_this_email = server.mongos['default']['users'].find({"email":client_email.lower()})
            if users_with_this_email.count() > 0:
                self.write("I'm sorry, this email address has already been used.")  
                return
            
        users_with_this_username = server.mongos['default']['users'].find({"username":client_newuser.lower()})
        if users_with_this_username.count() > 0:
            self.write("I'm sorry, this username has already been taken.")  
            return    
            
        else:
            hashedpass = bcrypt.hashpw(client_newpass, bcrypt.gensalt(12))
            u = User()
            u.generate(hashedpass=hashedpass,username=client_newuser.lower())
            if client_email is not None:
                u.UserSettings['email'] = client_email.lower()
            
            u.UserSettings['maxposts'] = 20
            u.savemongo()
            
            self.set_secure_cookie("username",client_newuser.lower(),httponly=True)
            self.set_secure_cookie("maxposts",str(u.UserSettings['maxposts']),httponly=True)
            
            self.redirect("/")


class LoginHandler(BaseHandler):
    def get(self):
        self.getvars()        
        self.write(self.render_string('templates/header.html',title="Login to your account",username=self.username,loggedin=self.loggedin))
        self.write(self.render_string('templates/loginform.html'))
        self.write(self.render_string('templates/footer.html'))
    def post(self):
        self.getvars()
        self.write(self.render_string('templates/header.html',loggedin=False,title='Login to your account',username=""))

        client_username =  tornado.escape.xhtml_escape(self.get_argument("username"))
        client_password =  tornado.escape.xhtml_escape(self.get_argument("pass"))

        user = server.mongos['default']['users'].find_one({"username":client_username.lower()})
        if user is not None:
            u = User()
            u.load_mongo_by_username(username=client_username.lower())
            if bcrypt.hashpw(client_password,user['hashedpass']) == user['hashedpass']:
                self.set_secure_cookie("username",user['username'].lower(),httponly=True)
                self.set_secure_cookie("maxposts",str(u.UserSettings['maxposts']),httponly=True)
                self.redirect("/")
                return

        self.write("I'm sorry, we don't have that username/password combo on file.")

class LogoutHandler(BaseHandler):
     def post(self):
         self.clear_cookie("username")
         self.redirect("/")

class ShowUserPosts(BaseHandler):
    def get(self,pubkey):
        self.getvars()
        
        #Unquote it, then convert it to a PluricKey object so we can rebuild it.
        #Quoting destroys the newlines.
        pubkey = urllib.unquote(pubkey)
        k = Keys(pub=pubkey)
        k.formatkeys()
        pubkey = k.pubkey
        
        
        messages = []
        self.write(self.render_string('templates/header.html',title="Welcome to Pluric!",username=self.username,loggedin=self.loggedin))
        for message in server.mongos['default']['envelopes'].find({'envelope.payload.author.pubkey':pubkey},fields={'envelope.payload_sha512','envelope.payload.topictag','envelope.payload.subject'},limit=10,).sort('value',-1):
            messages.append(message)

        self.write(self.render_string('templates/showuserposts.html',messages=messages))
        self.write(self.render_string('templates/footer.html'))
                 
                 
class FollowUserHandler(BaseHandler):
    def get(self,pubkey):
        self.getvars()
        #Calculate the votes for that post. 

    def post(self):    
        self.getvars()
        if not self.loggedin:
            self.write("You must be logged in to follow a user.")
            return 0
        u = User()
        u.load_mongo_by_username(username=self.username)
        u.followUser(pubkey)
        u.savemongo()
        
class NoFollowUserHandler(BaseHandler):
    def get(self,topictag):
        self.getvars()
     #Calculate the votes for that post. 

    def post(self):    
        self.getvars()
        if not self.loggedin:
            self.write("You must be logged in to follow a topic.")
            return 0
        u = User()
        u.load_mongo_by_username(username=self.username)
        u.noFollowUser(topictag)
        u.savemongo()


class FollowTopicHandler(BaseHandler):
    def get(self,pubkey):
        self.getvars()

    def post(self):    
        self.getvars()
        if not self.loggedin:
            self.write("You must be logged in to follow a user.")
            return 0
        u = User()
        u.load_mongo_by_username(username=self.username)
        u.followTopic(pubkey)
        u.savemongo()

class NoFollowTopicHandler(BaseHandler):
    def get(self,topictag):
        self.getvars()
        
    def post(self):       
        self.getvars()
        if not self.loggedin:
            self.write("You must be logged in to follow a topic.")
            return 0
        u = User()
        u.load_mongo_by_username(username=self.username)
        u.noFollowTopic(topictag)
        u.savemongo()
    
            
            
        

class RatingHandler(BaseHandler):
    def get(self,posthash):
        self.getvars()
        #Calculate the votes for that post. 
         
    def post(self):    
        self.getvars()

        #So you may be asking yourself.. Self, why did we do this as a POST, rather than
        #Just a GET value, of the form server.com/msg123/voteup
        #The answer is xsrf protection.
        #We don't want people to link to the upvote button and trick you into voting up.

        if not self.loggedin:
            self.write("You must be logged in to rate a message.")
            return
        
        client_hash =  tornado.escape.xhtml_escape(self.get_argument("hash"))        
        client_rating =  tornado.escape.xhtml_escape(self.get_argument("rating"))
        rating_val = int(client_rating)
        if rating_val not in [-1,0,1]:
            self.write("Invalid Rating.")
            return -1
        
        e = Envelope()
        e.payload.dict['payload_type'] = "rating"
        e.payload.dict['rating'] = rating_val
        e.payload.dict['regarding'] = client_hash
            
        #Instantiate the user who's currently logged in
        user = server.mongos['default']['users'].find_one({"username":self.username})        
        u = User()
        u.load_mongo_by_pubkey(user['pubkey'])
        
        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['pubkey'] = u.UserSettings['pubkey']
        e.payload.dict['author']['friendlyname'] = u.UserSettings['username']
        e.payload.dict['author']['client'] = "Pluric Web frontend Pre-release 0.1"
        if self.include_loc == "on":
            gi = GeoIP.open("/usr/local/share/GeoIP/GeoIPCity.dat",GeoIP.GEOIP_STANDARD)
            ip = self.request.remote_ip
            
            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"
                
            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + "," + str(gir['longitude'])
        
        #Sign this bad boy
        usersig = u.Keys.signstring(e.payload.text())
        e.dict['sender_signature'] = usersig
        
        #Send to the server
        server.receiveEnvelope(e.text())


class UserTrustHandler(BaseHandler):
    def get(self,user):
        self.getvars()
        #Calculate the trust for a user. 

    def post(self):    
        self.getvars()
        if not self.loggedin:
            self.write("You must be logged in to trust or distrust a user.")
            return

        client_pubkey =  self.get_argument("pubkey")    
        client_trust =  tornado.escape.xhtml_escape(self.get_argument("trust"))
        trust_val = int(client_trust)
        if trust_val not in [-100,0,100]:
            self.write("Invalid Trust Score.")
            return -1

        e = Envelope()
        e.payload.dict['payload_type'] = "usertrust"
        e.payload.dict['trust'] = trust_val
                
        k = Keys(pub=client_pubkey)
        e.payload.dict['pubkey'] = k.pubkey

        #Instantiate the user who's currently logged in
        user = server.mongos['default']['users'].find_one({"username":self.username})        
        u = User()
        u.load_mongo_by_pubkey(user['pubkey'])

        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['pubkey'] = u.UserSettings['pubkey']
        e.payload.dict['author']['friendlyname'] = u.UserSettings['username']

        e.payload.dict['author']['client'] = "Pluric Web frontend Pre-release 0.1"
        if self.include_loc == "on":
            gi = GeoIP.open("/usr/local/share/GeoIP/GeoIPCity.dat",GeoIP.GEOIP_STANDARD)
            ip = self.request.remote_ip

            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"

            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + "," + str(gir['longitude'])

        #Sign this bad boy
        usersig = u.Keys.signstring(e.payload.text())
        e.dict['sender_signature'] = usersig

        #Send to the server
        server.receiveEnvelope(e.text())



      
class NewmessageHandler(BaseHandler):
    def get(self):
         self.getvars()
         self.write(self.render_string('templates/header.html',title="Login to your account",username=self.username,loggedin=self.loggedin))
         self.write(self.render_string('templates/newmessageform.html'))
         self.write(self.render_string('templates/footer.html'))

    def post(self):
        self.getvars()
        if not self.loggedin:
            self.write("You must be logged in to do this.")
            return
        
        # self.write(self.render_string('templates/header.html',title='Post a new message',username=self.username))

        client_topic =  tornado.escape.xhtml_escape(self.get_argument("topic"))
        client_subject =  tornado.escape.xhtml_escape(self.get_argument("subject"))
        client_body =  tornado.escape.xhtml_escape(self.get_argument("body"))
        self.include_loc = tornado.escape.xhtml_escape(self.get_argument("include_location"))
        if "regarding" in self.request.arguments:
            client_regarding = tornado.escape.xhtml_escape(self.get_argument("regarding"))
            if client_regarding == "":
                client_regarding = None
        else:
            client_regarding = None
   
        #Build a list of all the variables that come in with attached_fileX, 
        #so we can parse them later on. attached_fileXXXX.path
        filelist = []
        for argument in self.request.arguments:
            if argument.startswith("attached_file") and argument.endswith('.path'):
                filelist.append(argument.rsplit('.')[0])
        #Uniquify list
        filelist = dict(map(lambda i: (i,1),filelist)).keys()
        #Use this flag to know if we successfully stored or not.
        stored = False   
        client_filepath = None     
        envelopebinarylist = []
        for attached_file in filelist:
            #I've testing including this var via the page directly. 
            #It's safe to trust this path, it seems.
            #All the same, let's strip out all but the basename.
            
            client_filepath =  tornado.escape.xhtml_escape(self.get_argument(attached_file + ".path"))
            client_filetype =  tornado.escape.xhtml_escape(self.get_argument(attached_file + ".content_type"))
            client_filename =  tornado.escape.xhtml_escape(self.get_argument(attached_file + ".name"))
            client_filesize =  tornado.escape.xhtml_escape(self.get_argument(attached_file + ".size"))
           
            print "Trying client_filepath" 
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
                    
                    oid = server.bin_GridFS.put(localfile,filename=digest, content_type=client_filetype)
                    stored = True
            else:
                stored = True
            #Create a message binary.    
            bin = Envelope.binary(hash=digest)
            #Set the Filesize. Clients can't trust it, but oh-well.
            bin.dict['filesize_hint'] =  client_filesize
            bin.dict['content_type'] = client_filetype
            bin.dict['filename'] = client_filename
            envelopebinarylist.append(bin.dict)
            #Don't keep spare copies on the webservers
            os.remove(fullpath)
             
                        
        e = Envelope()
        topics = []
        topics.append(client_topic)        
        e.payload.dict['formatting'] = "markdown"
        e.payload.dict['payload_type'] = "message"
        e.payload.dict['topictag'] = topics
        e.payload.dict['body'] = client_body
        e.payload.dict['subject'] = client_subject
        if client_regarding is not None:
            print "Adding Regarding - " + client_regarding
            e.payload.dict['regarding'] = client_regarding
            
        #Instantiate the user who's currently logged in
        user = server.mongos['default']['users'].find_one({"username":self.username})        
        u = User()
        u.load_mongo_by_pubkey(user['pubkey'])
        
        if stored is True:
            e.payload.dict['binaries'] = envelopebinarylist

        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['pubkey'] = u.UserSettings['pubkey']
        e.payload.dict['author']['friendlyname'] = u.UserSettings['username']
        e.payload.dict['author']['client'] = "Pluric Web frontend Pre-release 0.1"
        if self.include_loc == "on":
            gi = GeoIP.open("/usr/local/share/GeoIP/GeoIPCity.dat",GeoIP.GEOIP_STANDARD)
            ip = self.request.remote_ip
            
            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"
                
            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + "," + str(gir['longitude'])
        
        #Sign this bad boy
        usersig = u.Keys.signstring(e.payload.text())
        e.dict['sender_signature'] = usersig
        
        #Send to the server
        server.receiveEnvelope(e.text())

class MyPrivateMessagesHandler(BaseHandler):
    def get(self):
        self.getvars()
        if not self.loggedin:
            self.write("You must be logged in to do this.")
            return
            
        messages = []
        user = server.mongos['default']['users'].find_one({"username":self.username})        
        u = User()
        u.load_mongo_by_pubkey(user['pubkey'])
        
        self.write(self.render_string('templates/header.html',title="Welcome to Pluric!",username=self.username,loggedin=self.loggedin))
        for message in server.mongos['default']['envelopes'].find({'envelope.payload.to':u.Keys.pubkey},fields={'envelope.payload_sha512','envelope.payload.subject'},limit=10,).sort('value',-1):
            message['envelope']['payload']['subject'] = u.Keys.decryptToSelf(message['envelope']['payload']['subject'])
            messages.append(message)

        self.write(self.render_string('templates/showprivatemessages.html',messages=messages))
        self.write(self.render_string('templates/footer.html'))


class NewPrivateMessageHandler(BaseHandler):
    def get(self,urlto=None):
         self.getvars()
         self.write(self.render_string('templates/header.html',title="Login to your account",username=self.username,loggedin=self.loggedin))
         self.write(self.render_string('templates/privatemessageform.html',urlto=urlto))
         self.write(self.render_string('templates/footer.html'))

    def post(self,urlto=None):
        self.getvars()
        if not self.loggedin:
            self.write("You must be logged in to do this.")
            return

        client_to =  tornado.escape.xhtml_escape(self.get_argument("to"))
        if urlto is not None:
            client_to = tornado.escape.xhtml_escape(urlto)
            
        client_subject =  tornado.escape.xhtml_escape(self.get_argument("subject"))
        client_body =  tornado.escape.xhtml_escape(self.get_argument("body"))
        self.include_loc = tornado.escape.xhtml_escape(self.get_argument("include_location"))
        if "regarding" in self.request.arguments:
            client_regarding = tornado.escape.xhtml_escape(self.get_argument("regarding"))
            if client_regarding == "":
                client_regarding = None
        else:
            client_regarding = None

        #Instantiate the user who's currently logged in
        user = server.mongos['default']['users'].find_one({"username":self.username})        
        u = User()
        u.load_mongo_by_pubkey(user['pubkey'])
        
        #Instantiate the key of the user who we're sending to
        toKey = Keys(pub=client_to)
        toKey.formatkeys()


        e = Envelope()
        topics = []
        e.payload.dict['payload_type'] = "privatemessage"
        e.payload.dict['to'] = toKey.pubkey
        e.payload.dict['body'] = toKey.encryptToSelf(client_body)
        e.payload.dict['subject'] = toKey.encryptToSelf(client_subject)
        if client_regarding is not None:
            print "Adding Regarding - " + client_regarding
            e.payload.dict['regarding'] = client_regarding

        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['pubkey'] = u.UserSettings['pubkey']
        e.payload.dict['author']['friendlyname'] = u.UserSettings['username']
        e.payload.dict['author']['client'] = "Pluric Web frontend Pre-release 0.1"
        if self.include_loc == "on":
            gi = GeoIP.open("/usr/local/share/GeoIP/GeoIPCity.dat",GeoIP.GEOIP_STANDARD)
            ip = self.request.remote_ip

            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"

            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + "," + str(gir['longitude'])

        #Sign this bad boy
        usersig = u.Keys.signstring(e.payload.text())
        e.dict['sender_signature'] = usersig

        #Send to the server
        server.receiveEnvelope(e.text())

class FormTestHandler(BaseHandler):
    def get(self):
        #Generate a test form to manually submit trust and votes
        self.getvars()
        self.write(self.render_string('templates/header.html',title="Seeeecret form tests",username=self.username,loggedin=self.loggedin))
        self.write(self.render_string('templates/formtest.html'))
        self.write(self.render_string('templates/footer.html'))

        
def main():
    tornado.options.parse_command_line()
    # timeout in seconds
    timeout = 10
    socket.setdefaulttimeout(timeout)
    print "Starting Web Frontend for " + server.ServerSettings['hostname']
    #####TAKE ME OUT IN PRODUCTION!!!!@! #####
    
    #tl = TopicList.TopicList()        
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
        (r"/vote" ,RatingHandler),
        (r"/usertrust",UserTrustHandler),  
        (r"/topictag/(.*)" ,TopicHandler), 
        (r"/message/(.*)" ,MessageHandler),    
        (r"/followuser/(.*)" ,FollowUserHandler),  
        (r"/followtopic/(.*)" ,FollowTopicHandler),  
        (r"/showuserposts/(.*)" ,ShowUserPosts),  
        (r"/showprivates" ,MyPrivateMessagesHandler),    
        (r"/uploadprivatemessage/(.*)" ,NewPrivateMessageHandler),
        (r"/uploadprivatemessage" ,NewPrivateMessageHandler),  
        (r"/privatemessage/(.*)" ,PrivateMessageHandler),  
          
        (r"/formtest" ,FormTestHandler),  
          
        
        (r"/(.*)", NotFoundHandler)
    ], **settings)
    
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
