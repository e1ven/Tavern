#!/usr/bin/env python3
import pymongo
from datetime import datetime, timedelta
import pymongo
import bson
import Envelope
from server import server


class TopicList(object):
    def __init__(self):
        MAP_FUNCTION = bson.code.Code("""
                function(){
                        if (this.envelope.payload.class == 'message')
                        {
                            var timestamp = Number(new Date()/1000);
                            mtime = this.envelope.local.time_added;

                            // 60 * 60 * 24 * 7 * 2 = 1209600
                            if ((mtime + 11209600) > timestamp )

                                {
                                tag = this.envelope.payload.topic;
                                if (tag != 'sitecontent')
                                {
                                        emit({tag:tag},{count:1});
                                }

                            }

                        }

                }
                """)

        REDUCE_FUNCTION = bson.code.Code("""
                function(key, values){
                    var count = 0;
                    values.forEach(function(v)
                    {
                        count += v['count'];
                    });

                    return {count: count};
                }

                """)

        server.db.safe.map_reduce('envelopes', 
                   map=MAP_FUNCTION, reduce=REDUCE_FUNCTION, out="topiclist")
T = TopicList()
