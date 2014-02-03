#!/bin/bash

# This file will run through the basics to get Tavern up and running on your Vagrant box.
# It is meant JUST for Dev- It makes several tradeoffs that you should never do in prod.
# (Such as reduced randomness, running remote bash scripts as root, etc)

# That said, it should help get your devbox up and running quickly and easily.

# If you are in testing, particularly in Vagrant, you may need to generate additional pseudo-random numbers.
# These should not be trusted for prod, but they are good enough for developing software that talks to Tavern nets.
# For prod, I'd suggest the use of a USB device that generates random numbers.


# Generate additional entropy if nec.
if [ `grep 4096 /etc/default/haveged > /dev/null 2>&1; echo $?` -ne 0 ]
then
    apt-get install haveged
    echo 'DAEMON_ARGS="-w 4096"' > /etc/default/haveged
    update-rc.d haveged defaults
    /etc/init.d/haveged restart
fi

# Verify Tavern install is up to date
bash -l /opt/Tavern/install.sh

# Start Tavern
bash -l /opt/Tavern/tavern.sh start