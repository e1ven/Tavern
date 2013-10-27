
#!/bin/bash
# This is a wrapper script that fires up Tavern both on Linux and OSX.
# To do so, it performs a few tests, as well as compressing files where possible.



function usage 
{
    echo "Usage: $0 {start|stop|restart} [debug/initonly]"
    echo "initonly will startup, create config files, then exit"
    echo "debug will run a single process without backgrounding"
}


function getarg 
{
    # Get an argument.. Or if it doesn't exist, echo 0
    # This way, we don't get "unary operator expected" errors.

    key=`echo $1 | $sed 's/[^a-zA-Z0-9_]/_/g'`
    v=${!key}

    if [ ! -z "$v" ]
    then
        echo $v
    else
        echo 0
    fi
}


function sinceArg
{
    # Calculate time elapsed between the stored-variable $1, and the date $2
    # Example: sinceArg lastrun would give the seconds since timestamp in the `lastrun` variable.
    ODATE=$(getarg $1)
    if [ -z $2 ]
    then
        NDATE=$DATE
    else
        NDATE=$2
    fi
    echo $(($NDATE-$ODATE))
}

function sinceFileArg
{

    # Calculate the time elapsed between mtime of $1 and the stored-variable $2
    # Example: sinceFileArg test.txt lastrun would determine if test.txt had been updated since `lastrun` was saved.
    sinceArg $2 `$stat $1`
}

function loadargs 
{
# Load in args the quick and dirty (and fast!) way

    if [ -s tmp/startup-settings ]
    then
        source tmp/startup-settings
        true > tmp/startup-settings
    fi
}

function writearg 
{
# Write out an argument
    if [ $# -eq 2 ]
    then
        # Remove unspeakable chars
        key=`echo $1 | $sed 's/[^a-zA-Z0-9_]/_/g'`
        value=$2
        echo $key=\"$value\" >> tmp/startup-settings
    elif [ $# -eq 1 ]
    then
        writearg $1 $(getarg $1)
    fi
}

function ramdisk
{
 # [start/stop] [dir] [size in mb]   

control=$1
mntpt=$2
size=$3

if [ "$control" == 'start' ]
then
    if [ -z "$3" ]
    then
        echo "Bad call to ramdisk"
        stop
        # Using exit, not return here, since this should abort the script.
    fi
    # Determine if we should use OSX or Linux style ramdisks
    which diskutil > /dev/null
    if [ $? -eq 0 ]
    then #OSX

        # Make sure it's not ALREADY a ramdisk
        diskutil info $mntpt | grep "Volume Name" | grep TavernRamDisk
        if [ "$?" -eq 0 ]
        then
            echo "Ramdisk already exists!"
            return
        fi
        # Calculate the size, in blocks
        disksize=$(($size*1024*1024/512))
        # Create the ramdisk
        virt_disk=`hdiutil attach -nomount ram://$disksize`
        # Verify the Ramdisk. Make extra damn sure.
        actual_size=`diskutil info $virt_disk | grep Total | awk -F'exactly ' {'print $2'} | awk {'print $1'}`
        if [ "$actual_size" != "$disksize" ]
        then
            echo "Error creating Ramdisk! - $actual_size + $disksize"
            stop
        else
            diskutil erasevolume HFS+ "TavernRamDisk-$mntpt" $virt_disk
            umount $virt_disk
            mkdir -p $mntpt
            # Union to mount locally in the FS tree
            # noowners so non-root can access
            # noauto so it doesn't mount on it's own, outside of Tavern
            # nobrowse so we don't clutter up the finder
            # noexec to head off any vulns from the local file
            # nosuid for the same reason. Not needed, so disable by default.
            # noatime since atime isn't needed, and just slows things down slightly
            mount -t hfs -o union,noowners,noauto,noexec,nosuid,noatime,nobrowse $virt_disk $mntpt
            if [ $? -eq 0 ]
                then
                echo $mntpt >> mounted
            fi
        fi
    else
        # Linux
        mkdir -p $mntpt
        mount -t tmpfs -o size="$size"M,noauto,noexec,nosuid,noatime tmpfs $mntpt
        echo $mntpt >> mounted
    fi
elif [ "$control" == "stop" ]
then
    echo "stopping disk images"
    for i in `cat tmp/mounted`
    do
        device=`mount | grep $(pwd) | grep $i|awk '{print $1}'`
        umount -f $device

        # Detect if we're on OSX, and need to remove the attached ramdisk
        which diskutil > /dev/null
        if [ $? -eq 0 ]
        then
            hdiutil detach -force $device
        fi
    done
    # We're done here.
    mv tmp/mounted tmp/mounted-old
fi
}



function stop 
{
# Stop the Tavern servers

    user=`whoami`

    for i in `ps aux | grep [w]ebfront | awk {'print $2'}`
    do
        kill $i
    done
    for i in `ps aux | grep [a]pi | awk {'print $2'}`
    do
        kill $i
    done

    # Remove ramdisks
    ramdisk stop
    exit
}

function findcommands
{
# The system commands are often different between GNU and BSD ecosystems.
# Find the versions to call.

    if [ $DEBUG -eq 1 ]
    then
        echo "Avoiding compressing JS due to debug mode.."
        yui='cat'
    else
        if [ -z "$yui" ]
        then
            # The yui-compressor will compress JS and CSS.
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
        fi
        writearg yui $yui
    fi
    # Find which version of sed we should use.
    if [ -z "$sed" ]
    then
        echo "Setting Sed."
        echo foo | gsed 's/foo/bar/' > /dev/null 2>&1
        if [ $? -eq 0 ]
        then
            #Use Gnu sed
            sed='gsed'
        else
            sed='sed'
        fi
    fi
    writearg sed $sed


    # Test our ability to take a hash
    # OSX uses md5, linux uses md5sum.
    # We will use the identifier generated in the next section

    if [ $DEBUG -eq 1 ]
    then
        echo "Using faster/less secure hashes for debug mode."
        hash='cksum'
    else
        if [ -z "$hash" ]
        then
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
                hash='cksum'
            fi
            writearg hash $hash
        fi
    fi

    # Find which version of stat we should use, OS X or GNU
    if [ -z "$stat" ]
    then
        echo "Determining which version of stat to use."
        touch tmp/delete-me-please
        stat -f "%m"  tmp/delete-me-please > /dev/null
        if [ $? -eq 0 ]
        then
            #Use OSX stat
            stat='stat -f %m'
        else
            stat='stat -c %Y'
        fi
    fi
    writearg stat "$stat"
}


function start 
{
# Start up Tavern.

    # Save the current dir, so we can return at the end of the script
    CURDIR=`pwd`
    cd /opt/Tavern

    numservers=2

    # Set the current date, so it's consistant
    DATE=`date +%s`

    # First, create working directories for the functions below.
    mkdir -p tmp/checked
    mkdir -p tmp/unchecked
    mkdir -p tmp/gpgfiles

    mkdir -p tmp/gzipchk
    mkdir -p tmp/unchecked-gzipchk

    mkdir -p tmp/last-run/

    mkdir -p logs
    mkdir -p data/conf

    #### Ensure we're living in isolated envs, so we don't screw up the overall system
    # Ruby
    source ~/.rvm/scripts/rvm || source /etc/profile.d/rvm.sh
    rvm use system@Tavern --install --create
    # Python
    source tmp/env/bin/activate

    if [ "$1" == "debug" ]
    then
        DEBUG=1
    else
        DEBUG=0
    fi
    if [ "$1" == "initonly" ]
    then
        INITONLY=1
    else
        INITONLY=0
    fi

    # Load in the StartScript settings
    loadargs
    findcommands

    # Create necessary RamDisks
    cd tmp
    ramdisk start gpgfiles 5
    ramdisk start Robohash 20
    ramdisk start static 15
    cd ..

    echo "Ensuring Python deps are up-to-date"
    # Ensure we have the expected Python deps
    pip install -qr requirements.txt

    echo "Ensuring fontello directory compliance"
    for i in static/css/fontello*.css
    do
        if [ $(sinceFileArg $i lastrun_fontello_$i) -gt 0 ]
        then
            # Update file to change ../font to ../fonts
            # This will show up when updating fontello
            "$sed" -i 's/\.\.\/font\//\.\.\/fonts\//g' $i
        fi
        writearg lastrun_fontello_$i `date +%s`
    done

    if [ $(sinceFileArg static/css/fontello.css lastrun_fontello2_$i) -gt 0 ]
    then
        # Update file to remove margin if it's there.
        "$sed" -i 's/margin-right: 0.2em;//g' static/css/fontello.css
    fi
    writearg lastrun_fontello2_$i `date +%s`

    # Convert from SCSS to CSS.
    echo "Converting from SASS to CSS"

    # Remove any old and no longer used generated css files
    for i in `ls static/sass/css/`
    do
        base=`basename $i .css`
        if [ ! -f static/sass/scss/$base.scss ]
            then
            echo static/sass/css/$i
        fi
    done
    # Convert the SCSS to CSS and put in production folder
    compass compile static/sass/ -q -e production
    rsync -a static/sass/css/* static/css/


    # Go through each JS file in the project, and check to see if we've minimized it already.
    # If we haven't, minimize it. Otherwise, just skip forward, for speed.
    echo "Minimizing JS"
    for i in `find static/scripts -name "*.js"| grep -v '.min.js' | grep -v 'unified'`
    do
        if [ $(sinceFileArg $i lastrun_minjs_$i) -gt 0 ]
        then
            basename=`basename $i ".js"`
            echo -e "\t $basename $(sinceFileArg $i lastrun)"
            $yui $i > static/scripts/$basename.min.js $flags
        fi
        writearg lastrun_minjs_$i `date +%s`
    done

    echo "Minimizing CSS"
    for i in `find static/css -name "*.css"| grep -v '.min.css'`
    do
        if [ $(sinceFileArg $i lastrun_mincss_$i) -gt 0 ]
        then
            basename=`basename $i ".css"`
            echo -e "\t $basename $(sinceFileArg $i lastrun)"
            $yui $i > static/css/$basename.min.css
        fi
        writearg lastrun_mincss_$i `date +%s`
    done

    echo "Combining CSS.."
    for i in `ls static/css/style-*.min.css`
    do  
        # Find the basename we're working with, such as 'style-default.min.css'
        STYLE=`echo $i | awk -F- {'print $2'} |  awk -F. {'print $1'}`
        echo -e "\t $STYLE"
        cat $i static/css/fontello.min.css static/css/video-js.min.css static/css/animation.min.css static/css/fonts.min.css  > static/css/unified-$STYLE.min.css
    done

    echo "Combining and further minimizing JS.."
    # This uses hashes, rather than timestamps, for simplicity.
    # By using hashes, we can always cat them, then compare one file for differences
    # Otherwise, we'd need to compare dates N times.
    JSFILES="static/scripts/json3.min.js static/scripts/jquery.min.js static/scripts/mousetrap.min.js static/scripts/jstorage.min.js static/scripts/jquery.json.min.js static/scripts/colresizable.min.js static/scripts/jquery-throttle.min.js static/scripts/default.min.js static/scripts/garlic.min.js static/scripts/video.min.js static/scripts/audio.min.js static/scripts/retina.min.js"
    if [ $DEBUG -eq 0 ]
    then    
        cat $JSFILES > static/scripts/unified.js
        # Check to see if we already have a hashed copy of this file.
        # If we do, then don't minimize it.
        filehash=`cat static/scripts/unified.js | $hash | cut -d" " -f 1`
        if [ ! -f tmp/unchecked/$filehash.exists ]
        then
            $yui static/scripts/unified.js > static/scripts/unified.min.js
        else
            : # No Reformatting needed 
        fi
        touch tmp/checked/$filehash.exists
    else
        # If we're in DEBUG mode, we want to directly include the files, rather than inlinine them.
        # This makes it MUCH easier to find/fix errors.
        echo "" > themes/default/header-debug-JS.html
        for script in $JSFILES
        do 
            # Get the basename, to avoid getting the static/tmp dir
            bn=`basename $script`
            echo "<script defer src=\"/static/scripts/$bn\"></script>" >> themes/default/header-debug-JS.html
        done
    fi

    echo "Ensuring Proper Python formatting.."
    # Use a hash as a secondary check, because these are slow.
    for i in `find . -maxdepth 1 -name "*.py"`
    do
        if [ $(sinceFileArg $i lastrun_autopep_$i) -gt 0 ]
        then
            echo -e "\t $i"
            autopep8 --in-place -p1 --aggressive $i
            docformatter --in-place $i
        fi
        writearg lastrun_autopep_$i `date +%s`
    done

    echo "Validating code correctness.."
    # Run our manual validations. 
    ./validate.sh
    if [ "$?" -ne 0 ]
        then
        echo "Aborting due to code issue."
        stop 2
    fi
    # Run automated tests against the code.
    for i in `find . -maxdepth 1 -name "*.py"`
    do
        if [ $(sinceFileArg $i lastrun_validate_$i) -gt 0 ]
        then
            echo -e "\t $i"
            pep8 --show-source --show-pep8 --ignore=E501 $i
            if [ "$?" -ne 0 ]
            then
                echo "Aborting due to unfixable style issue."
                stop 2
            fi
        fi
        writearg lastrun_validate_$i `date +%s`
    done

    echo "Gzipping individual files"
    # Compress static files with gzip, so nginx can serve pre-compressed version of them (if so configured)
    for file in `find static -not -name "*.gz" -and -not -path "static/scripts/*" -and -not -path "static/css/*" -and -not -path "static/sass/*" -type f`
    do 
        if [ $(sinceFileArg $file lastrun_gzip_$i) -gt 0 ]
        then
            echo -e "\t $file"
            gzip --best < $file > $file.gz
        fi
        writearg lastrun_gzip_$i `date +%s`

    done

    echo "Gzipping Unified files"
    # Gzip CSS files which need it.
    # This uses hashes rather than timestamps since Unified.min.js is created every time.
    for file in `echo "static/css/unified-*.min.css static/scripts/unified.min.js" `
    do 
        filehash=`cat $file | $hash | cut -d" " -f 1`
        if [ ! -f tmp/unchecked-gzipchk/$filehash.exists ]
        then
            echo -e "\t $file"
            gzip --best < $file > $file.gz
            # Compressed
        else
            : # No compressing needed 
        fi
        touch tmp/gzipchk/$filehash.exists
    done

    rm tmp/unchecked-gzipchk/*.exists > /dev/null 2>&1 
    rm tmp/unchecked/*.exists > /dev/null 2>&1 


    echo "Updating Ramdisk"
    rsync -a --delete static/* tmp/static
    rsync -a --delete libs/Robohash/* tmp/Robohash

    if [ $(sinceArg onStartLastRun) -gt 3600 ]
    then
        # Run the various functions to ensure DB caches and whatnot
        echo "Running onStart functions."
        ./ensureindex.sh
        ./TopicList.py
        ./ModList.py
        ./DiskTopics.py -l
        writearg onStartLastRun $DATE
    else
        echo "It's only been $(($(sinceArg onStartLastRun)/60)) minutes.. Not running onStart functions again until the hour mark."
        writearg onStartLastRun
    fi

    writearg lastrun `date +%s`
    echo "Starting Tavern..."
    if [ $DEBUG -eq 1 ]
    then
        python3 ./webfront.py --loglevel=DEBUG --writelog=False --debug=True
    elif [ $INITONLY -eq 1 ]
    then
        python3 ./webfront.py --initonly=True
    else    
        # -1 in the line below, since we start the count at 0, so we can be starting on 8080
        for ((i=0;i<=$((numservers -1));i++))
        do            
            port=$((8080 +i))
            echo "Starting on port $port"
            nohup python3 ./webfront.py --port=$port > logs/webfront-$port.log &
        done
        tail -n 10 logs/*
    fi
    # Write out the last successful start

    cd $CURDIR

}


function restart 
{
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
