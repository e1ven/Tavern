#!/bin/bash
# Generates a wordlist, used in the usernames, such as Anonymous@StinkyCheeseUglyBiscuit

if [ "$1" == 'debug' ]
    then
        echo "Printing output to screen. This will be slower."
    fi
sleep 2

echo "" > wordlist
echo "Sorting Badword list"
cat wordgen/list-of-badwords | sort | uniq > wordgen/list-of-unique-badwords

echo "Checking each word against the badword list"
for word in `cat wordgen/original-list-of-words`
do
    # ignore words on the badword list
    grep -i $word wordgen/list-of-unique-badwords > /dev/null
    if [ $? -ne 0 ]
    then
        # Ignore words with capital letters. Proper names are bad.
        echo $word | grep [A-Z] > /dev/null
        if [ $? -ne 0 ]
        then
            if [ "$1" == 'debug' ]
            then
                echo "$word - Added to list"
            fi
            echo $word >> wordlist
        else
            if [ "$1" == 'debug' ]
            then
                echo "$word - Rejected"
            fi
        fi
    fi
done
sort wordlist | uniq > wordlist-unique
mv wordlist-unique wordlist
