#!/bin/bash

# It occurs to me that we should do a few sanity checks, to make sure I don't forget certain things.
# It's really easy at 3AM to call various functions that you otherwise know aren't the way you want to do it.

# We shouldn't use the Python Random, since it doesn't use MT.
# Instead, we should use TavernUtils.SystemRandom functions. 

LEN=`awk '/random\./ && !/random.SystemRandom/' *.py themes/default/*.html | wc -l`
 if [ $LEN -gt 0 ] 
	then
	echo "Do not use the Python Random module."
	exit 2
fi

LEN=`cat Server.py | grep serversettings | grep -v self | grep -v memor | grep -v 'default.TavernSettings' | grep -v 'server.serversett' | wc -l`
 if [ $LEN -gt 0 ] 
	then
	echo "Server should use self.serversettings, not the root module."
	exit 2
fi

pep8 --show-source --show-pep8 --ignore=E501 *.py
