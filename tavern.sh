#!/bin/bash
user=`whoami`

if [ $user == 'root' ]
then
    # Kill nginx if possible.
    killall nginx
    /opt/nginx/sbin/nginx 
else
    echo "Not killing nginx, as I am not root."
    echo "If you want nginx murdered, use sudo."
fi

if [ "$1" == 'daemon' ]
then
    kill `ps aux | grep [w]ebfront | awk {'print $2'}`; nohup ./webfront.py &
    kill `ps aux | grep [a]pi | awk {'print $2'}`; nohup ./api.py &
fi

echo "Running onStart functions."

./ensureindex.sh
./TopicList.py
./ModList.py
./DiskTopics.py -l

echo "Minimizing JS"
for i in `find static/scripts/ -name "*.js"| grep -v '.min.js'`
do
    basename=`basename $i ".js"`
    echo -n "$basename"..
    squeeze yuicompressor $i > static/scripts/$basename.min.js --nomunge    
done
echo ""
echo "Minimizing CSS"
for i in `find static/css/ -name "*.css"| grep -v '.min.css'`
do
    basename=`basename $i ".css"`
    echo -n "$basename"..
    squeeze yuicompressor $i > static/css/$basename.min.css
done
echo ""


autopep8 -i *.py
# If we're not in daemon mode, fire up the server
if [ "$1" == 'daemon' ]
then
    tail -f `hostname`.log nohup.out
else
    ./webfront.py
fi


