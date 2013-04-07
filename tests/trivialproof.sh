#!/bin/bash

if [ -z $1 ]
then
    str='foo'
else
    str=$1
fi

echo "Starting Str is $str"
results=''
count=0
while [ "$results" != "00" ]
do
    results=`echo $str | shasum | cut -c 1-2`
    str+="0"
    count=$(($count+1))
done

echo "Required padding of $count Zeros." 

