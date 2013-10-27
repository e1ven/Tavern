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

# Don't accidentily use comparisons to judge equality for non constants
LEN=`grep "is not" *.py | grep -v None | grep -v True | grep -v False | grep "if " | grep -v "#" | wc -l`
 if [ $LEN -gt 0 ] 
    then
    grep "is not" *.py | grep -v None | grep -v True | grep -v False | grep "if " | grep -v "#"
    echo "Ensure you are not using 'is not' when you mean !=  "

    exit 2
fi

LEN=`grep "is " *.py | grep -v None | grep -v True | grep -v False | grep "if " | grep -v "#"  | wc -l`
 if [ $LEN -gt 0 ] 
    then
    grep "is " *.py | grep -v None | grep -v True | grep -v False | grep "if " | grep -v "#" 
    echo "Ensure you are not using 'is' when you mean == "
    
    exit 2
fi
