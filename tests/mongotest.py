import sys
import json


sys.path.append('..')  #So we can load modules from the main dir
from Envelope import *

import pymongo
from pymongo import Connection
connection = Connection()


mongo = Connection('localhost', 27017)
db = connection['test']
posts = db.posts
posts.ensure_index('message_sha512', unique=True)


e = Envelope(importfile='89548000f7543fbf5cdc9822e95b29564a01a5fbeb03c032937fa38c89161520b664bb9e8a323277b02883f3e696135adf83cdb610ca0a541b7f121cb52729e0.7zPluricEnvelope')
e.dict['_id'] = e.message.hash()
posts.insert(e.dict)


for post in db.posts.find({"pluric_envelope.message.subject" : "This is a super awesome message"},as_class=OrderedDict):
    tostr = json.dumps(post,separators=(',',':'),encoding='utf8')
    e2 = Envelope (importstring=tostr)


print e.text()
print "---"
print e2.text()