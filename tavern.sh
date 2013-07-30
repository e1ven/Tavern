#!/bin/bash
# This is a wrapper script that fires up Tavern both on Linux and OSX.
# To do so, it performs a few tests, as well as compressing files where possible.


function usage {
    echo "Usage: $0 {start|stop|restart} [debug/initonly]"
    echo "initonly will startup, create config files, then exit"
    echo "debug will run a single process without backgrounding"
}

function stop {

    user=`whoami`

    for i in `ps aux | grep [w]ebfront | awk {'print $2'}`
    do
        kill $i
    done
    for i in `ps aux | grep [a]pi | awk {'print $2'}`
    do
        kill $i
    done
}

function start {
    CURDIR=`pwd`
    cd /opt/Tavern
    numservers=2
    # First, create two working directories
    mkdir -p tmp/checked
    mkdir -p tmp/unchecked
    mkdir -p tmp/gpgfiles

    mkdir -p tmp/gzipchk
    mkdir -p tmp/unchecked-gzipchk

    mkdir -p logs


    # Run the various functions to ensure DB caches and whatnot
    echo "Running onStart functions."

    ./ensureindex.sh
    ./TopicList.py
    ./ModList.py
    ./DiskTopics.py -l


    echo "Ensuring fontello directory compliance"
    echo foo | gsed 's/foo/bar/' > /dev/null 2>&1
    if [ $? -eq 0 ]
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

    if [ "$yui" != "cat" ]
    then 
        flags='--nomunge'
    fi


    # Test our ability to take a hash
    # OSX uses md5, linux uses md5sum.
    # We will use the identifier generated in the next section
    echo "Testing ability to hash"

    if [ "$1" == 'debug' ]
    then
        echo "Using faster/less secure hashes for debug mode."
        hash='cksum'
    else
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
            hash='cksum'
        fi
    fi

    # Go through each JS file in the project, and check to see if we've minimized it already.
    # If we haven't, minimize it. Otherwise, just skip forward, for speed.
    echo "Minimizing JS"
    mv tmp/checked/* tmp/unchecked/ > /dev/null
    mv tmp/gzipchk/* tmp/unchecked-gzipchk

    result=255
    for i in `find static/scripts/ -name "*.js"| grep -v '.min.js' | grep -v 'unified'`
    do
        filehash=`cat $i | $hash | cut -d" " -f 1`
        basename=`basename $i ".js"`
        if [ ! -f tmp/unchecked/$filehash.exists ]
        then
            # No pre-hashed version available
            $yui $i > static/scripts/$basename.min.js $flags
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

    echo "Gzipping individual files"
    # Compress the files with gzip
    for file in `find static -not -name "*.gz" -and -not -path "static/scripts/*" -and -not -path "static/css/*" -and -not -path "static/sass/*" -type f`
    do 
        filehash=`cat $file | $hash | cut -d" " -f 1`
        if [ ! -f tmp/unchecked-gzipchk/$filehash.exists ]
        then
            gzip --best < $file > $file.gz
            echo -e "\t $file"
            # Compressed
        else
            : # No compressing needed 
        fi
        touch tmp/gzipchk/$filehash.exists
    done


    echo "Gzipping Unified files"
    # Compress the files with gzip
    for file in `echo 'static/css/unified-*.min.css static/scripts/unified.min.js' `
    do 
        filehash=`cat $file | $hash | cut -d" " -f 1`
        if [ ! -f tmp/unchecked-gzipchk/$filehash.exists ]
        then
            gzip --best < $file > $file.gz
            echo -e "\t $file"
            # Compressed
        else
            : # No compressing needed 
        fi
        touch tmp/gzipchk/$filehash.exists
    done

    rm tmp/unchecked-gzipchk/*.exists
    rm tmp/unchecked/*.exists


    echo "Starting Tavern..."
    if [ "$1" == 'debug' ]
    then
        /usr/bin/env python3 ./webfront.py --loglevel=DEBUG --writelog=False
    elif [ "$1" == 'initonly' ]
    then
        /usr/bin/env python3 ./webfront.py --initonly=True
    else    
        # -1 in the line below, since we start the count at 0, so we can be starting on 8080
        for ((i=0;i<=$((numservers -1));i++))
        do            
            port=$((8080 +i))
            echo "Starting on port $port"
            nohup /usr/bin/env python3 ./webfront.py --port=$port > logs/webfront-$port.log &
        done
        tail -n 10 logs/*
    fi
    cd $CURDIR
}


function restart {
    stop
    sleep 2
    start
}


if [ $# -lt 1 ]
then
    usage
    exit 1
fi

case "$1" in
        start)
            start $2
            ;;
        stop)
            stop
            ;;
        restart)
            stop
            start
            ;;
        debug|initonly)
            if [ $# -eq 1 ]
            then
                start $1
            else
                usage
            fi
            ;;
        *)
            usage
            exit 1
 
esac
