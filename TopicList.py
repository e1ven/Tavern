#!/usr/bin/env python3
from datetime import datetime, timedelta
import bson
import Envelope
from Server import server
import logging

def main():

    MAP_FUNCTION = """
        function(){
                if (this.envelope.payload.class == 'message')
                {
                    var timestamp = Number(new Date()/1000);
                    mtime = this.envelope.local.time_added;

                    // 60 * 60 * 24 * 7 * 2 = 1209600
                    if ((mtime + 11209600) > timestamp )

                        {
                        tag = this.envelope.local.sorttopic;
                        if (tag != '222sitecontent')
                        {
                                emit({tag:tag},{count:1});
                        }

                    }

                }

        }
        """

    REDUCE_FUNCTION = """
            function(key, values){
                var count = 0;
                values.forEach(function(v)
                {
                    count += v['count'];
                });

                return {count: count};
            }

            """

    server.db.safe.map_reduce('envelopes',
                          map=MAP_FUNCTION, reduce=REDUCE_FUNCTION, out="topiclist");


# Run the main() function.
if __name__ == "__main__":
    main()
    