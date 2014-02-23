#!/bin/bash

# It occurs to me that we should do a few sanity checks, to make sure I don't forget certain things.
# It's really easy at 3AM to call various functions that you otherwise know aren't the way you want to do it.


# We shouldn't use the Python Random, since it doesn't use MT.
# Instead, we should use tavern.utils.SystemRandom functions. 

DIRECTORIES='libtavern/*.py webtav/*.py utils/*.py'

LEN=`awk '/random\./ && !/random.SystemRandom/' $DIRECTORIES webtav/themes/default/*.html | wc -l`
if [ $LEN -gt 0 ] 
	then
	echo "Do not use the Python Random module."
	exit 2
fi

LEN=`cat libtavern/Server.py | grep serversettings | grep -v self | grep -v memor | grep -v 'default.TavernSettings' | grep -v 'import' |  grep -v 'server.serversett' | wc -l`
if [ $LEN -gt 0 ] 
	then
	echo "Server should use self.serversettings, not the root module."
	exit 2
fi

LEN=`grep "datetime" $DIRECTORIES | grep -v 'utc'| grep -v 'delta'| grep -v 'import' | grep -v 'format'| wc -l`
if [ $LEN -gt 0 ]
    then
    echo "Make sure that you're using UTC for all dates"
    exit 2
fi


LEN=`grep "upper()" $DIRECTORIES | wc -l`
if [ $LEN -gt 0 ] 
    then
    echo "When possible, it's nicer to compare using lower() rather than upper()"
    echo "Uppercase jumps out at you in the code, and is a bit ugly"
    exit 2
fi

