#!/usr/bin/env python3
import pymongo
from datetime import datetime, timedelta
import Envelope
import Server
server = Server.Server()
import bson


class ModList(object):
    def __init__(self):
        MAP_FUNCTION = bson.code.Code("""
                function(){
                        if (this.envelope.payload.class == 'usertrust')
                        {
                            var timestamp = Number(new Date()/1000);
                            mtime = this.envelope.local.time_added;

                            // 60 * 60 * 24 * 7 * 26 = 15724800
                            if ( (mtime + 15724800) > timestamp )
                                {
                                    var topic = this.envelope.payload.topic;
                                    var moderator = this.envelope.payload.trusted_pubkey;
                                    var trust = this.envelope.payload.trust;
                                    emit({topic:topic,moderator:moderator},{trust:trust,count:1});
                                }

                        }
                    }
                """)

        REDUCE_FUNCTION = bson.code.Code("""
                function (key, values){
                    var count = 0;
                    var trust = 0;
                    values.forEach(function(v) {
                        count += v['count'];
                        trust += v['trust'];
                     });
                    return {trust:trust,count:count};
                }
                """)

        server.db.unsafe.map_reduce('envelopes',
                                    map=MAP_FUNCTION, reduce=REDUCE_FUNCTION, out="modlist")

M = ModList()
