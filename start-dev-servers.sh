#!/bin/bash
ps aux | grep [m]ysql
if [ $? -eq 1 ]
then 
	nohup mysql.server start 
fi
nohup mongod run --config /usr/local/Cellar/mongodb/2.0.2-x86_64/mongod.conf &