#!/bin/bash
autopep8 -i *.py
sudo killall nginx
sudo /opt/nginx/sbin/nginx 
kill `ps aux | grep [w]ebfront | awk {'print $2'}`; nohup ./webfront.py &
kill `ps aux | grep [a]pi | awk {'print $2'}`; nohup ./api.py &
./ensureindex.sh
./TopicList.py
./ModList.py
./DiskTopics.py -l
tail -f `hostname`.log nohup.out
