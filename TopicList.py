#!/usr/bin/env python3
import pymongo
from datetime import datetime, timedelta
from pymongo.code import Code
from server import server
class TopicList(object):
    def __init__(self):
        MAP_FUNCTION = Code("""
                function() {
                        if (this.envelope.payload.class == 'message')
                        {
                            for (var i =0; i < this.envelope.payload.topic.length; i++) 
                                {
                                    var timestamp = Number(new Date()/1000);
                                    mtime = this.envelope.local.time_added;
                                    print(mtime)
                                    print(timestamp)
                                    if ((mtime + 1186400) > timestamp )
                                        {
                                        singletag = this.envelope.payload.topic;
                                        if (singletag != 'sitecontent')
                                        {
                                                emit({tag:singletag},{count:1}); 
                                        }

                                    }
                                }
                        }
                                              
                }
                """)
        REDUCE_FUNCTION = Code("""
                function(key, values) {
                    var count = 0;
                    values.forEach(function(v) {
                        count += v['count'];
                        });
                        return {count: count};
                        }
                """)

        server.mongos['default']['envelopes'].map_reduce(map=MAP_FUNCTION, reduce=REDUCE_FUNCTION, out="topiclist")
T = TopicList()
