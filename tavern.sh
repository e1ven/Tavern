#!/bin/bash
# This is a wrapper script that fires up Tavern both on Linux and OSX.
# To do so, it performs a few tests, as well as compressing files where possible.

numservers=4
# First, create two working directories
mkdir -p tmp/checked
mkdir -p tmp/unchecked
mkdir -p tmp/gpgfiles
mkdir -p logs

# First, determine if we're running the program as root.
# If we are, restart nginx if possible.
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
    kill `ps aux | grep [w]ebfront | awk {'print $2'}`
    for ((i=0;i<=numservers;i++))
	do
		port=$((8080 +i))
		echo "Starting on port $port"
 		nohup /usr/bin/env python3 ./webfront.py --port=$port > logs/webfront-$port.log &
	done
    kill `ps aux | grep [a]pi | awk {'print $2'}`; nohup /usr/bin/env python3 ./api.py > logs/api.log &
fi


# Run the various functions to ensure DB caches and whatnot
echo "Running onStart functions."

./ensureindex.sh
./TopicList.py
./ModList.py
./DiskTopics.py -l




echo "Ensuring fontello directory compliance"
gsed > /dev/null 2&>1
if [ $? -eq 1 ]
    then
    #Use Gnu sed
    sed='gsed'
else
    sed='sed'
fi

"$sed" -i 's/\.\.\/font\//\.\.\/fonts\//g' static/css/fontello*.css
"$sed" -i 's/margin-right: 0.2em;//g' static/css/fontello.css


# Convert from SCSS to CSS.
echo "Converting from SASS to CSS"

# Remove any old and no longer used generated css files
for i in `ls static/sass/css/`
do
    base=`basename $i .css`
    if [ ! -f static/sass/scss/$base.scss ]
        then
        rm static/sass/css/$i
    fi
done
# Convert the SCSS to CSS and put in production folder
compass compile static/sass/ -e production
cp static/sass/css/* static/css/



# The yui-compressor will compress JS and CSS
# The command to run it is different on OSX and Linux, however, so figure out which one we have
# If we don't have either, use 'cat' as an alternate 'compressor'
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


# Test our ability to take a hash
# OSX uses md5, linux uses md5sum.
# We will use the identifier generated in the next section
echo "Testing ability to hash"
echo "foo" | md5 > /dev/null 2>&1
if [ $? -eq 0 ]
then
    hash='md5'
fi
echo "foo" | md5sum > /dev/null 2>&1
if [ $? -eq 0 ]
then
    hash='md5sum'
fi
if [ -z $hash ]
then
    # No minimization
    hash='date +%s -r'
fi


# Go through each JS file in the project, and check to see if we've minimized it already.
# If we haven't, minimize it. Otherwise, just skip forward, for speed.
echo "Minimizing JS"
mv tmp/checked/* tmp/unchecked/ > /dev/null
result=255
for i in `find static/scripts/ -name "*.js"| grep -v '.min.js' | grep -v 'unified'`
do
    filehash=`cat $i | $hash | cut -d" " -f 1`
    basename=`basename $i ".js"`
    if [ ! -f tmp/unchecked/$filehash.exists ]
    then
        # No pre-hashed version available
        $yui $i > static/scripts/$basename.min.js --nomunge
        result=$?
        echo -e "\t $basename"
        # Reformatted
    else
        : # No Reformatting needed 
        result=0
    fi
    if [ $result -eq 0 ]
    # only write the touchfile if the minimize worked
        then
        touch tmp/checked/$filehash.exists
    fi
done


echo "Minimizing CSS"
for i in `find static/css/ -name "*.css"| grep -v '.min.css'`
do
    filehash=`cat $i | $hash | cut -d" " -f 1`
    basename=`basename $i ".css"`
    if [ ! -f tmp/unchecked/$filehash.exists ]
    then
        $yui $i > static/css/$basename.min.css
        echo -e "\t $basename"
        # Reformatted
    else
        : # No Reformatting needed 
    fi
    touch tmp/checked/$filehash.exists
done

echo "Combining CSS.."
# No need to re-minimize the CSS, it's already OK.
for i in `ls static/css/style-*.min.css`
do  
    echo $i
    cat $i static/css/fontello.min.css static/css/video-js.min.css static/css/animation.min.css > static/css/unified-default.min.css
done


echo "Combining and further minimizing JS.."
cat static/scripts/json3.min.js static/scripts/jquery.min.js static/scripts/mousetrap.min.js static/scripts/jstorage.min.js static/scripts/jquery.json.min.js static/scripts/colresizable.min.js static/scripts/jquery-throttle.min.js static/scripts/default.min.js static/scripts/garlic.min.js static/scripts/video.min.js static/scripts/audio.min.js static/scripts/retina.min.js  static/scripts/spin.min.js > static/scripts/unified.js

# It's smaller if we re-minimize afterwords. 
filehash=`cat static/scripts/unified.js | $hash | cut -d" " -f 1`
if [ ! -f tmp/unchecked/$filehash.exists ]
then
    $yui static/scripts/unified.js > static/scripts/unified.min.js
else
    : # No Reformatting needed 
fi
touch tmp/checked/$filehash.exists



echo "Ensuring Proper Python formatting.."
for i in `find . -maxdepth 1 -name "*.py"`
do
    filehash=`cat $i | $hash | cut -d" " -f 1`
    basename=`basename $i ".css"`
    if [ ! -f tmp/unchecked/$filehash.exists ]
    then
        autopep8 $i > /dev/null 2>&1
        echo -e "\t $basename"
        # Reformatted
    else
        : # No Reformatting needed 
    fi
    touch tmp/checked/$filehash.exists
done



rm tmp/unchecked/*.exists
# If we're not in daemon mode, fire up the server
if [ "$1" == 'daemon' ]
then
    tail -f logs/*
else
    /usr/bin/env python3 ./webfront.py
fi


