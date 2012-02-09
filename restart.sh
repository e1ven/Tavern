kill `ps aux | grep [w]ebfront | awk {'print $2'}`; nohup ./webfront.py &
kill `ps aux | grep [a]pi | awk {'print $2'}`; nohup ./api.py &
./TopicList.py
./ModList.py
./DiskTopics.py
