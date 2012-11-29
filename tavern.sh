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




echo "Testing ability to Minimize" 

yui-compressor -h > /dev/null 2>&1
if [ $? -eq 0 ]
then
    yui='yui-compressor'
fi

yuicompressor -h  > /dev/null 2>&1
if [ $? -eq 0 ]
then
    yui='yuicompressor'
fi

if [ -z $yui ]
then
    # No minimization
    yui='cat'
fi


echo "Minimizing JS"
for i in `find static/scripts/ -name "*.js"| grep -v '.min.js' | grep -v 'unified'`
do
    basename=`basename $i ".js"`
    echo -n "$basename"..
    $yui $i > static/scripts/$basename.min.js --nomunge    
done
echo ""
echo "Minimizing CSS"
for i in `find static/css/ -name "*.css"| grep -v '.min.css'`
do
    basename=`basename $i ".css"`
    echo -n "$basename"..
    $yui $i > static/css/$basename.min.css
done
echo ""

cat static/scripts/json2.min.js static/scripts/jquery.min.js static/scripts/jstorage.min.js static/scripts/jquery.json.min.js static/scripts/vsplit.min.js static/scripts/mousetrap.min.js static/scripts/default.min.js static/scripts/garlic.min.js static/scripts/video.min.js static/scripts/audio.min.js static/scripts/retina.min.js > static/scripts/unified.js
echo "Combining JS"
$yui static/scripts/unified.js > static/scripts/unified.min.js

autopep8 -i *.py > /dev/null 2>&1
# If we're not in daemon mode, fire up the server
if [ "$1" == 'daemon' ]
then
    tail -f `hostname`.log nohup.out
else
    ./webfront.py
fi


