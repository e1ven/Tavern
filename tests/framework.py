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
import random
import socket
import pymongo
import json
from collections import OrderedDict
import pymongo
from tornado.options import define, options
import pprint
from gridfs import GridFS
import hashlib
import urllib
#import TopicList
import lxml.html
import re
from time import gmtime, strftime


define("port", default=8080, help="run on the given port", type=int)



class Page(tornado.web.RequestHandler):

    def __init__(self, *args, **kwargs):
        #Ensure we have a html variable set.
        self.html = ""
        super(Page,self).__init__(*args,**kwargs)
        
    def write(self,html):
        self.html = self.html + html
# 
#     def finish(self,message=None):
#         super(Page,self).write("----")
#         super(Page,self).write(self.html)
#         super(Page,self).write("????")
#         super(Page,self).finish(message)
#                   
    def gettext(self):
        ptext = ""
        for a in self.pagetext:
            ptext = ptext + a
        self.write(ptext)
        

    def finish(self,div='limits',message=None):
        if "js" in self.request.arguments:
            #if JS is set at all, send the JS script version.
            super(Page, self).write(self.getjs(div))
        else:
            super(Page, self).write(self.html)
        super(Page,self).finish(message) 
   
    
    def getjs(self,element):
        #Get the element text, remove all linebreaks, and escape it up.
        #Then, send that as a document replacement
        print self.html
        parsedhtml = lxml.html.fromstring(self.html)
        eletext = parsedhtml.get_element_by_id(element)
        escapedtext = lxml.html.tostring(eletext).replace("\"","\\\"")
        escapedtext = escapedtext.replace("\n","")
        return ("document.getElementById('" + element + "').innerHTML=\"" + escapedtext + "\";")
    

def header():
    return """
            <html>
            <title>Yo, Dawg</title>
            <script src="//ajax.googleapis.com/ajax/libs/jquery/1.6.2/jquery.min.js" type="text/javascript"></script>
            <script src="default.js"></script>
            <body><div id='limits'>"""
            
def footer():
    return """</div></body><br>Copyright &copy Testius. """ +  strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime()) + """</body></html>"""


class DefaultJSHandler(Page):
    def get(self):
    
        #Find all internal links, replace them with JSLoaders
        self.write("""
        
function include_dom(script_filename) {
    var html_doc = document.getElementsByTagName('head').item(0);
    var js = document.createElement('script');
    js.setAttribute('language', 'javascript');
    js.setAttribute('type', 'text/javascript');
    js.setAttribute('src', script_filename);
    html_doc.appendChild(js);
    return false;
}


$(document).ready(function() {


    $('a.internal').each( function ()
    {            
        $(this).click(function()
            {
                include_dom($(this).attr('link-destination') + "?js=yes");
            });
        $(this).attr("link-destination",this.href);
        this.href = 'javascript:;';
    });
});

    """)
    
        
class IndexHandler(Page):
    def get(self):
        self.write (header() )
        self.write ( """
        <div id='left'>This is left</div>
        <br>
        <div id='center'>This is center</div>
        <br>
        <div id='right'>This is right</div>
        <a href="test" class='internal' >This is an internal link</a>
        <a href="test" class='external' >This is an external link</a>

        """)
        self.write( footer())
        
class TestHandler(Page):
    def get(self):
        self.write( header())
        self.write("""
        <div id='left'>This is left</div>
        <br>
        <div id='center'>This is BLAMO!</div>
        <br>
        <div id='right'>This is right</div>
        <a href="test" class='internal' >This is an internal link</a>
        <a href="test" class='external' >This is an external link</a>
        
         """ + footer())
         
        self.finish('center')

        
        
def main():
    tornado.options.parse_command_line()
    # timeout in seconds
    timeout = 10
    socket.setdefaulttimeout(timeout)
    
    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "cookie_secret": "7cxqGjRMzxv7E9Vxq2mnXalZbeUhaoDgnoTSvn0B",
        "login_url": "/login",
        "xsrf_cookies": True,
    }
    application = tornado.web.Application([
        (r"/" ,IndexHandler),  
        (r"/test" ,TestHandler), 
        (r"/default.js" ,DefaultJSHandler),  
 
        ], **settings)
    
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
