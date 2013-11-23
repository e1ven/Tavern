# This file will run through the basics to get Tavern up and running on your Vagrant box.
# It is meant JUST for Dev- It makes several tradeoffs that you should never do in prod.
# (Such as reduced randomness, running remote bash scripts as root, etc)

# That said, it should help get your devbox up and running quickly and easily.

# Don't run this script if we've already installed Tavern.
if [ -e /opt/tavern/data/COMPLETED-INSTALL ]
	then
	echo "Tavern already installed, not reinstalling."
	exit 0
fi
apt-key adv --keyserver keyserver.ubuntu.com --recv 7F0CEB10
echo 'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen' | sudo tee /etc/apt/sources.list.d/10gen.list
apt-get update

apt-get install haveged

# If you are in testing, particularly in Vagrant, you may need to generate additional pseudo-random numbers.
# These should not be trusted for prod, but they are good enough for developing software that talks to Tavern nets.
# For prod, I'd suggest the use of a USB device that generates random numbers.
if [ $os == 'LINUX' ]
then
    echo 'DAEMON_ARGS="-w 4096"' > /etc/default/haveged
    update-rc.d haveged defaults
    /etc/init.d/haveged restart
fi

bash -l /opt/Tavern/install.sh


update-rc.d nginx defaults 
update-rc.d tavern defaults

# Update again, so the logs/etc that were just created by root are now Vagrant owned.
chown vagrant:vagrant /opt/Tavern -R
chown vagrant:vagrant /opt/nginx -R

# Create a touchfile, so we don't run all these steps on every boot.
echo `date` >  /opt/Tavern/data/COMPLETED-INSTALL



