#!/bin/bash
# This is a wrapper script that fires up Tavern both on Linux and OSX.
# This script is written in Bash, rather than Python, so that it can load Python in the correct env.


function usage 
{
    echo "Usage: $0 {start|stop|restart} [debug]"
    echo "debug will run a single process without backgrounding"
}

function verify_tavern_dir
{
    # Verify if we're currently in a Tavern directory,
    # Check for required subdirs, abort if not found.

    SAFE=0
    SAFE=$((SAFE+`ls | grep 'tavern.sh' > /dev/null; echo $?`))
    SAFE=$((SAFE+`ls | grep 'logs' > /dev/null; echo $?`))
    SAFE=$((SAFE+`ls | grep 'utils' > /dev/null; echo $?`))
    SAFE=$((SAFE+`ls | grep 'conf' > /dev/null; echo $?`))
    SAFE=$((SAFE+`ls | grep 'tmp' > /dev/null; echo $?`))
    SAFE=$((SAFE+`ls | grep 'webtav' > /dev/null; echo $?`))
    if [ "$SAFE" -gt 0 ]
    then
        echo "This script was not run from a valid Tavern installation"
        exit 2
    fi
    SAFE=$((SAFE+`utils/mongodb/bin/mongod --help > /dev/null; echo $?`))
    SAFE=$((SAFE+`utils/nginx/sbin/nginx -? >/dev/null 2>&1; echo $?`))

    if [ "$SAFE" -gt 0 ]
    then
        echo -e "Tavern does not have all dependencies in place.\nDid you run install.sh?"
        exit 2
    fi
}

function getsetting
{
    # Gets a setting from the default settingsfile
    key=$1
    python -c "import libtavern.serversettings;settings=libtavern.serversettings.ServerSettings();print(settings.settings$key)"
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
        stop 2
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
            stop 2
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
            chflags hidden $mntpt
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
    echo "Stopping any disk images from previous unclean exits"
    for device in `diskutil list | grep '/dev/disk'`
    do
        echo $device
         if [ `diskutil info $device | grep TavernRamDisk >/dev/null; echo $?` -eq 0 ]
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
    

    echo "Terminating Required services"
    python -m utils.subservers stop

    # Remove ramdisks
    ramdisk stop

    # If we called stop with a value, like stop 2, then exit the program.
    if [ "$#" -gt 0 ]
    then
        exit $1
    fi
}

function findcommands
{
# The system commands are often different between GNU and BSD ecosystems.
# Find the versions to call.


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
        rm tmp/delete-me-please
    fi
    writearg stat "$stat"
}


function start 
{
# Start up the Tavern Web Interface.

    # Save the current dir, so we can return at the end of the script
    CURDIR=`pwd`

    # Set the current date, so it's consistant
    DATE=`date +%s`

    mkdir -p tmp/gpgfiles
    rm -rf tmp/gpgfiles/*

    mkdir -p tmp/last-run/

    mkdir -p logs
    mkdir -p conf

    # Ensure we're not leaking info to other system users.
    chmod -R og-rwx *

    # Python
    source tmp/env/bin/activate

    if [ "$1" == "debug" ]
    then
        DEBUG=1
    else
        DEBUG=0
    fi

    # Ensure we have our git hooks in place.
    if [ ! -f ".git/hooks/pre-commit" ]
    then
        ln -s "../../utils/pre-commit.sh" ".git/hooks/pre-commit"
    fi

    # Load in the StartScript settings
    loadargs
    findcommands

    # Create necessary RamDisks
    cd tmp
    ramdisk start gpgfiles 5
    ramdisk start static 15
    cd ..

    echo "Ensuring Python deps are up-to-date"
    # Ensure we have the expected Python deps
    pip install -qr datafiles/python-requirements.txt

    echo "Ensuring fontello directory compliance"
    for i in webtav/static/css/fontello*.css
    do
        if [ $(sinceFileArg $i lastrun_fontello_$i) -gt 0 ]
        then
            # Update file to change ../font to ../fonts
            # This will show up when updating fontello
            "$sed" -i 's/\.\.\/font\//\.\.\/fonts\//g' $i
            "$sed" -i 's/margin-right: 0.2em;//g' $i
        fi
        writearg lastrun_fontello_$i `date +%s`
    done

    # Convert from SCSS to CSS.
    echo "Converting from SASS to CSS"

    # Remove any old and no longer used generated css files
    for i in `ls webtav/static/sass/css/`
    do
        base=`basename $i .css`
        if [ ! -f webtav/static/sass/scss/$base.scss ]
            then
            echo webtav/static/sass/css/$i
        fi
    done

    # Convert the SCSS to CSS and put in production folder
    sass --compass --scss --update webtav/static/sass/scss/:webtav/static/css/
    
    echo "Combining and minimizing css"
    MINIMIZE=0
    for i in `find webtav/static/css -name "*.css"`
    do
        if [ $(sinceFileArg $i lastrun_mincss_$i) -gt 0 ]
        then
            basename=`basename $i ".css"`
            echo -e "\t $basename $(sinceFileArg $i lastrun)"
            MINIMIZE=1
        fi
        writearg lastrun_mincss_$i `date +%s`
    done
    # Ensure we have version of the combined css for each theme.
    for theme in `ls webtav/themes/`
    do
        if [ $MINIMIZE -gt 0 ] || [ ! -f webtav/static/css/combined-$theme.css ]
        then
            rm webtav/static/css/combined-$theme.css
            ALL_LIBS=$(for i in `find webtav/static/css -name "*.css" -not -name "combined-*" -not -name "theme-*"`; do echo -n "$i "; done)
            ALL_LIBS="$ALL_LIBS webtav/static/css/theme-$theme.css"
            $yui $ALL_LIBS -o webtav/static/css/combined-$theme.css
        fi
    done

    echo "Minimizing and combining JS libs"
    MINIMIZE=0
    echo "" > webtav/themes/default/header-debug-JS.html
    for i in `find webtav/static/scripts/combine -name "*.js"`
    do
        basename=`basename $i`
        echo "<script defer src=\"/static/scripts/combine/$basename\"></script>" >> webtav/themes/default/header-debug-JS.html

        if [ $(sinceFileArg $i lastrun_minjs_$i) -gt 0 ]
        then
            echo -e "\t $basename $(sinceFileArg $i lastrun)"
            MINIMIZE=1
        fi

        writearg lastrun_minjs_$i `date +%s`
    done
    if [ $MINIMIZE -gt 0 ] || [ ! -f webtav/static/scripts/combined.js ]
    then
        rm webtav/static/scripts/combined.js
        for i in `find webtav/static/scripts/combine -name "*.js"`
        do
            $yui $i >> webtav/static/scripts/combined.js
        done
    fi


    echo "Ensuring Proper Python formatting.."
    # Use a hash as a secondary check, because these are slow.
    for i in `find . -maxdepth 1 -name "*.py"`
    do
        if [ $(sinceFileArg $i lastrun_autopep_$i) -gt 0 ]
        then
            echo -e "\t $i"
            autopep8 --in-place -p1 --max-line-length=160 $i
            docformatter --in-place $i
        fi
        writearg lastrun_autopep_$i `date +%s`
    done

    echo "Updating Ramdisk"
    rsync -a --delete webtav/static/* tmp/static
    cp conf/gpg.conf tmp/gpgfiles
    if [ $(sinceArg onStartLastRun) -gt 3600 ]
    then
        # Run the various functions to ensure DB caches and whatnot
        echo "Running onStart functions."
        ./utils/TopicList.py || true
        ./utils/ModList.py || true
        ./utils/DiskTopics.py -l || true
        writearg onStartLastRun $DATE
    else
        echo "It's only been $(($(sinceArg onStartLastRun)/60)) minutes.. Not running onStart functions again until the hour mark."
        writearg onStartLastRun
    fi

    echo "Starting Required services"
    python -m utils.subservers start


    writearg lastrun `date +%s`

    # If we're in debug mode, watch the logs
    if [ $DEBUG -eq 1 ]
    then
        numservers=1
    else
        # Find the number of workers we should start.
        numservers=$(getsetting '["webtav"]["workers"]')
    fi

    echo "Starting Tavern with $numservers worker processes."
    for ((servernum = 0 ; servernum < numservers ; servernum++ ))
        do
            socketfile="tmp/webtav-worker-$servernum.sock"
            echo "Starting webtav worker with socket $socketfile"

            # Set pre/post conditions depenn
            if [ $DEBUG -eq 1 ]
            then
                # Run in debug mode
                python -m webtav.webfront --socket=$socketfile
            else
                # Store the log to a file instead of stdout.
                nohup python -m webtav.webfront --socket=$socketfile > logs/webtav-worker-$servernum.log 2>&1 &
            fi
        done
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

# Verify this is a valid location to run the script from.
verify_tavern_dir

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
        debug)

            if [ $# -eq 1 ]
            then

                # Stop any old processes
                for i in `ps aux | grep [w]ebfront | awk {'print $2'}`
                do
                    kill $i
                done

                start $1
            else
                usage
            fi
            ;;
        *)
            usage
            exit 1
 
esac
