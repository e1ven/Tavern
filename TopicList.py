import datetime
import pymongo
from bson.code import Code
from server import server
from User import User

class TopicList(object):
    def __init__(self): 
        #We put this in an init function so I can just create one a TopicList
        #This allows me to create one at Runtime if nec. 
        map = Code("""
        function() {
                if (this.envelope.payload.payload_type == 'message')
                {
                    for (var i =0; i < this.envelope.payload.topictag.length; i++) 
                	{ 
                	    var timestamp = Number(new Date()/1000);
                	    mtime = this.envelope.servers[0].time_seen;
                	    if ((mtime + 86400) > timestamp )
                	        {
                                singletag = this.envelope.payload.topictag[i];
                                emit({tag:singletag},{count:1}); 
                            }
                	}
            	}
                                              
        }
        """)

        reduce = Code("""
        function(key, values) {
            var count = 0;
            values.forEach(function(v) {
                count += v['count'];
                });
                return {count: count};
                }
        """)

        server.mongos['default']['envelopes'].map_reduce(map, reduce, "topiclist")
T = TopicList()
