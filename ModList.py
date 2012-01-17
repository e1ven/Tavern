#!/usr/bin/env python3
import pymongo
from datetime import datetime, timedelta
from pymongo.code import Code
from server import server

class ModList(object):
    def __init__(self):
        MAP_FUNCTION = Code("""
                function(){
                        if (this.envelope.payload.class == 'usertrust')
                        {
                            var timestamp = Number(new Date()/1000);
                            mtime = this.envelope.local.time_added;

                            // 60 * 60 * 24 * 7 * 26 = 15724800
                            if ( (mtime + 15724800) > timestamp )
                                {
                                    emit({moderator:this.envelope.payload.trusted_pubkey},{count:1,trust:this.envelope.payload.trust}); 
                                }

                        }
                                              
                }
                """)
                
        REDUCE_FUNCTION = Code("""
                function(key, values){
                    var record = {};

                    values.forEach(function(v)
                    {
                        print(v);
                        if (typeof(record[v[0]]) == 'undefined')
                        {
                            record[v[0]] = {};
                            record[v[0]]['count'] = 0;
                            record[v[0]]['trust'] = 0;
                        };
                        record[v[0]]['count'] += v['count'];
                        record[v[0]]['trust'] += v['trust'];
                    });

                    return record;
                }
                """)
                
        server.mongos['default']['envelopes'].map_reduce(map=MAP_FUNCTION, reduce=REDUCE_FUNCTION, out="modlist")
        
M = ModList()
