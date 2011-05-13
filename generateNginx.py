#!/usr/bin/env python
from server import server
import os,sys

f = open('nginx/pluric.site', 'w')


nginxfile = """
    server {
        listen 80;

        server_name""" +  server.ServerSettings['hostname'] + ";" + """
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
                gridfs """ + server.ServerSettings['bin-mongo-db'] + """ field=filename type=string;
                mongo """ + server.ServerSettings['bin-mongo-hostname'] + ":" + str(server.ServerSettings['bin-mongo-port']) + ";" +"""
        }
  }
"""
f.write(nginxfile)
f.close()