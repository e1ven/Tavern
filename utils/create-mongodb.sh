#!/bin/bash
if [ "$#" -lt 1 ]
then
    echo "Usage $0 installdir"
    exit 1
fi
installdir=$1

mkdir -p $installdir/datafiles/mongodb
mkdir -p $installdir/logs/
mkdir -p $installdir/conf/

echo "port=26001" > $installdir/conf/mongodb.conf
echo "bind_ip=127.0.0.1" >> $installdir/conf/mongodb.conf
echo "logpath=$installdir/logs/mongod.log" >> $installdir/conf/mongodb.conf
echo "pidfilepath=$installdir/conf/mongod.pid"  >> $installdir/conf/mongodb.conf
echo "nounixsocket=true" >> $installdir/conf/mongodb.conf
echo "fork=true" >> $installdir/conf/mongodb.conf
echo "dbpath=$installdir/datafiles/mongodb" >> $installdir/conf/mongodb.conf


