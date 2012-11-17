#!/bin/bash
autopep8 -i *.py
sudo killall nginx
sudo /opt/nginx/sbin/nginx 
if [ $1 == 'daemon' ]
then
    kill `ps aux | grep [w]ebfront | awk {'print $2'}`; nohup ./webfront.py &
    kill `ps aux | grep [a]pi | awk {'print $2'}`; nohup ./api.py &
fi
./ensureindex.sh
./TopicList.py
./ModList.py
./DiskTopics.py -l
if [ $1 == 'daemon' ]
then
    tail -f `hostname`.log nohup.out
else
    ./webfront.py
fi


