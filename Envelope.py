import json
import hashlib
import pylzma,sys
import os
from keys import *
import collections
from collections import *
json.encoder.c_make_encoder = None
import pymongo
import pprint
import postmarkup


class Envelope(object):
    postmarkup = postmarkup.create(use_pygments=False)


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
    #Modified to have more newlines. I like newlines.
    def gfm(text):
        # Extract pre blocks
        extractions = {}
        def pre_extraction_callback(matchobj):
            hash = md5_func(matchobj.group(0)).hexdigest()
            extractions[hash] = matchobj.group(0)
            return "{gfm-extraction-%s}" % hash
        pre_extraction_regex = re.compile(r'{gfm-extraction-338ad5080d68c18b4dbaf41f5e3e3e08}', re.MULTILINE | re.DOTALL)
        text = re.sub(pre_extraction_regex, pre_extraction_callback, text)

        # prevent foo_bar_baz from ending up with an italic word in the middle
        def italic_callback(matchobj):
            if len(re.sub(r'[^_]', '', matchobj.group(1))) > 1:
                return matchobj.group(1).replace('_', '\_')
            else:
                return matchobj.group(1)
        text = re.sub(r'(^(?! {4}|\t)\w+_\w+_\w[\w_]*)', italic_callback, text)


        # in very clear cases, let newlines become <br /> tags
        def newline_callback(matchobj):
            if len(matchobj.group(1)) == 1:
                return matchobj.group(0).rstrip() + '  \n'
            else:
                return matchobj.group(0)
        # text = re.sub(r'^[\w\<][^\n]*(\n+)', newline_callback, text)
        text = re.sub(r'[^\n]*(\n+)', newline_callback, text)

        # Insert pre block extractions
        def pre_insert_callback(matchobj):
            return extractions[matchobj.group(1)]
        text = re.sub(r'{gfm-extraction-([0-9a-f]{40})\}', pre_insert_callback, text)

        return text

        
    class Payload(object):
        def __init__(self,initialdict):
            self.dict = OrderedDict()
            self.dict = initialdict
        def hash(self):
            h = hashlib.sha512()
            h.update(self.text())
            #print "Hashing " + self.text()
            return h.hexdigest()
        def text(self): 
            newstr = json.dumps(self.dict,ensure_ascii=False,separators=(',',':'))
            return newstr  
        def validate(self):
            if not self.dict.has_key('author'):
                print "No Author Information"
                return False
            else:
                if not self.dict['author'].has_key('pubkey'):
                    print "No Pubkey line in Author info"
                    return False
            return True                
                          
    class Message(Payload):
        def validate(self):
            if not Envelope.Payload(self.dict).validate():
                print "Super does not Validate"
                return False
            if not self.dict.has_key('subject'):
                print "No subject"
                return False
            if not self.dict.has_key('body'):
                print "No Body"
                return False
            if self.dict.has_key('topictag_list'):
                #You are allowed to have no topictags.
                #But you can have no more than 3.
                if len(self.dict['topictag_list']) > 3:
                    print "List too long"
                    return False
            return True  
    
    
    class PrivateMessage(Payload):
        def validate(self):
            if not Envelope.Payload(self.dict).validate():
                print "Super does not Validate"
                return False
            if not self.dict.has_key('to'):
                print "No 'to' field"
                return False
            if self.dict.has_key('topictag_list'):
                print "Topictag not allowed in privmessage."
                return False
            return True
            
    class Rating(Payload):
         def validate(self):
             if not Envelope.Payload(self.dict).validate():
                 return False
             if not self.dict.has_key('rating'):
                 print "No rating number"
                 pprint.pprint(self.dict)
                 return False
             rvalue = self.dict['rating']
             if rvalue not in [-1,0,1]:
                 print "Evelope ratings must be either -1, 1, or 0."
                 return False
             return True
             
    class UserTrust(Payload):
        def validate(self):
              if not Envelope.Payload(self.dict).validate():
                  return False
              if not self.dict.has_key('pubkey'):
                  print "No pubkey to set trust for."
                  return False
              tvalue = self.dict['trust']
              if tvalue not in [-100,0,100]:
                  print "Message ratings must be either -100, 0, or 100"
                  return False
              return True             
                     
                  
    def validate(self):
        #Validate an Envelope
        
        
        if not self.dict.has_key('envelope'):
            print "Invalid Evelope. No Header"
            return False
        if not self.dict.has_key('sender_signature'):
            print "No sender signature. Invalid."
            return False        
        if not self.payload.validate():
            print "Payload does not validate."
            return False
        return True    
    class binary(object):
            def __init__(self,hash):
                self.dict = OrderedDict()
                self.dict['sha_512'] = hash
            
                
                
    def __init__(self):
        self.dict = OrderedDict()
        self.dict['envelope'] = OrderedDict()
        self.dict['envelope']['payload'] = OrderedDict()
        self.dict['envelope']['local'] = OrderedDict()
        self.dict['envelope']['local']['citedby'] = []

        self.payload = Envelope.Payload(self.dict['envelope']['payload'])
   
   
    def registerpayload(self):
        if self.dict['envelope'].has_key('payload'):
            if self.dict['envelope']['payload'].has_key('payload_type'):
                if self.dict['envelope']['payload']['payload_type'] == "message":
                    self.payload = Envelope.Message(self.dict['envelope']['payload'])
                elif self.dict['envelope']['payload']['payload_type'] == "rating":
                    self.payload = Envelope.Rating(self.dict['envelope']['payload'])
                elif self.dict['envelope']['payload']['payload_type'] == "usertrust":
                    self.payload = Envelope.UserTrust(self.dict['envelope']['payload'])
                elif self.dict['envelope']['payload']['payload_type'] == "privatemessage":
                    self.payload = Envelope.PrivateMessage(self.dict['envelope']['payload'])
                
    def loadstring(self,importstring):
        self.dict = json.loads(importstring,object_pairs_hook=collections.OrderedDict,object_hook=collections.OrderedDict)
        self.registerpayload()
        
   
    def loadfile(self,filename):
        
        #Determine the file extension to see how to parse it.
        basename,ext = os.path.splitext(filename)

        #Determine the file extension to see how to parse it.
        basename,ext = os.path.splitext(filename)
        filehandle = open(filename, 'r')
        filecontents = filehandle.read() 
        if (ext == '.7zPluricEnvelope'):
            #7zip'd JSON
            filecontents = pylzma.decompress(filecontents)
        self.dict = OrderedDict()
        self.dict = json.loads(filecontents,object_pairs_hook=collections.OrderedDict,object_hook=collections.OrderedDict)
        self.registerpayload()
        filehandle.close()
        
    def loadmongo(self,mongo_id):
        from server import server
        env = server.mongos['default']['envelopes'].find_one({'_id':mongo_id},as_class=OrderedDict)
        if env == None:
            return False
        else:
            self.dict = env
            self.registerpayload()
            return True

        
    def reloadfile(self):
        self.loadfile(self.payload.hash() + ".7zPluricEnvelope")
        self.registerpayload()
        
            
    def text(self):
        self.dict['envelope']['payload'] = self.payload.dict
        self.dict['envelope']['payload_sha512'] = self.payload.hash()
        newstr = json.dumps(self.dict,separators=(',',':'),encoding='utf8')
        return newstr

    def prettytext(self): 
        self.dict['envelope']['payload'] = self.payload.dict
        self.dict['envelope']['payload_sha512'] = self.payload.hash()
        newstr = json.dumps(self.dict,indent=2,separators=(', ',': '))
        return newstr 
        
    def savefile(self):
        self.dict['envelope']['payload'] = self.payload.dict
        self.dict['envelope']['payload_sha512'] = self.payload.hash()
        
        #Compress the whole internal Envelope for saving.
        compressed = pylzma.compress(self.text(),dictionary=27,fastBytes=255)

        # print "Compressed size " + str(sys.getsizeof(compressed))
        # print "Full Size " + str(sys.getsizeof(self.dict))        
        
        #We want to name this file to the SHA512 of the payload contents, so it is consistant across servers.
        filehandle = open(self.payload.hash() + ".7zPluricEnvelope",'w')
        filehandle.write(compressed)
        filehandle.close()
        
    def saveMongo(self):
        self.dict['envelope']['payload'] = self.payload.dict
        self.dict['envelope']['payload_sha512'] = self.payload.hash()
        
        from server import server
        self.dict['_id'] = self.payload.hash()
        server.mongos['default']['envelopes'].save(self.dict)
    
