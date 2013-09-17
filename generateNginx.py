#!/usr/bin/env python3
from Server import server
import os
import sys
import socket
from ServerSettings import serversettings

f = open('nginx/pluric.site', 'w')


nginxfile = """
    server {
        listen 80;

        server_name """ + serversettings.settings['hostname'] + ";" + """
        location / {
                proxy_pass http://tornados/;
                }

        location /uploadnewmessage {
                upload_pass @uploads;
                upload_store /opt/uploads/;
                upload_resumable on;
                upload_buffer_size 100K;
                upload_max_file_size 20G;

                upload_set_form_field $upload_field_name.name "$upload_file_name";
                upload_set_form_field $upload_field_name.content_type "$upload_content_type";
                upload_set_form_field $upload_field_name.path "$upload_tmp_path";
                upload_pass_form_field "submit";
                upload_pass_form_field "_xsrf";
                upload_pass_form_field "topic";
                upload_pass_form_field "subject";
                upload_pass_form_field "body";
                upload_pass_form_field "include_location";
        }

        location @uploads {
                proxy_pass   http://tornados;
        }
        location /binaries/ {
                gridfs """ + serversettings.settings['bin-mongo-db'] + """ field=filename type=string;
                mongo """ + socket.gethostbyaddr(serversettings.settings['bin-mongo-hostname'])[2][0] + ":" + str(serversettings.settings['bin-mongo-port']) + ";" + """
        }
  }
"""

# We do the whole socket.gethostbyaddr thing because the nginx GridFS
# config doesn't allow lookups by DNS name. JSYK.
f.write(nginxfile)
f.close()
