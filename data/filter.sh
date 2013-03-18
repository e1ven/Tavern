#!/bin/bash
echo "Sorting Badword list"
cat badwords | sort | uniq > badwords2
mv badwords2 badwords

echo "Adding words to nono list"
for word in `cat originlist`
do
    grep $word badwords  > /dev/null
    if [ $? -ne 0 ]
    then
        echo $word >> wordlist
    fi
done
sort wordlist | uniq > wordlist2
mv wordlist2 wordlist