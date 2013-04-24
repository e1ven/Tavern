#!/bin/bash

echo "" > wordlist
echo "Sorting Badword list"
cat badwords | sort | uniq > badwords2
mv badwords2 badwords

echo "Checking each word against the badword list"
for word in `cat originlist`
do
    # ignore words on the badword list
    grep -i $word badwords  > /dev/null
    if [ $? -ne 0 ]
    then
        # Ignore words with capital letters. Proper names are bad.
        echo $word | grep [A-Z] > /dev/null
        if [ $? -ne 0 ]
        then
            echo $word >> wordlist
        fi
    fi
done
sort wordlist | uniq > wordlist2
mv wordlist2 wordlist
