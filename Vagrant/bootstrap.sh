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
apt-get -y install ruby rubygems mongodb-10gen haveged luajit libluajit-5.1-dev g++ libpcre3-dev zlib1g-dev libssl-dev python-dev swig libfreetype6 libfreetype6-dev libjpeg8-dev libjpeg8 libzzip-dev libxml2-dev libxslt-dev python3.3 python3.3-dev libmagic-dev python-imaging java-common yui-compressor  gnupg make git-core scons libpq-dev curl lib32z1

# Install Distribute + Pip
curl http://python-distribute.org/distribute_setup.py | python3.3
curl https://raw.github.com/pypa/pip/master/contrib/get-pip.py | python3.3


# We're going to need more randomness to create encryption keys
# For dev, we'll use the tool haveged to "generate" more entropy
# This isn't particularly secure - It uses various HW timings, but it should be OK for dev boxes..

# The primary use of this Vagrantfile is to generate software that talks to Tavern, not to be a production Tavern relay.
# For prod, I'd suggest the use of a USB device that generates random numbers.
echo 'DAEMON_ARGS="-w 4096"' > /etc/default/haveged
update-rc.d haveged defaults
/etc/init.d/haveged restart


# Temporarily add /usr/local/bin to the path so root can run pip-3.3,etc
PATH=$PATH:/usr/local/bin

# Install the Gems that convert the sass files into CSS
gem install sass compass


# Compile Nginx
NGINX_VER=1.4.2


cd /usr/local/src
wget http://nginx.org/download/nginx-$NGINX_VER.tar.gz   
tar xvfz nginx-$NGINX_VER.tar.gz

cd nginx-$NGINX_VER

wget https://github.com/simpl/ngx_devel_kit/archive/v0.2.18.tar.gz
tar -zxvf v0.2.18.tar.gz

# Configure LuaJIT - Used right now for nginx-big-upload

git clone https://github.com/chaoslawful/lua-nginx-module.git

export LUAJIT_LIB=/usr/lib/x86_64-linux-gnu/
export LUAJIT_INC=/usr/include/luajit-2.0/ 

# Configure GridFS
git clone https://github.com/mdirolf/nginx-gridfs.git
CFLAGS="$CFLAGS -Wno-missing-field-initializers"
cd nginx-gridfs
git submodule init
git submodule update
cd mongo-c-driver
git checkout v0.7.1
cd ../..



./configure --with-http_ssl_module  --prefix=/opt/nginx  --with-http_stub_status_module --with-http_gzip_static_module \
--add-module=/usr/local/src/nginx-$NGINX_VER/nginx-gridfs  --add-module=/usr/local/src/nginx-$NGINX_VER/ngx_devel_kit-0.2.18 --add-module=/usr/local/src/nginx-$NGINX_VER/lua-nginx-module \
--with-cc-opt='-Wno-missing-field-initializers -Wno-unused-function -Wno-unused-but-set-variable -D_POSIX_SOURCE'


make
make install

mkdir /opt/uploads
chmod 777 /opt/uploads/
mkdir -p /var/www/cache/tmp

cd /opt/nginx
git clone https://github.com/pgaertig/nginx-big-upload.git
    
    
cd /opt
cd Tavern
mkdir -p libs

# Setup nginx
cd /opt/Tavern/data/nginx
rm /opt/nginx/conf/nginx.conf
ln -s /opt/Tavern/data/nginx/nginx.conf /opt/nginx/conf/
cp /opt/Tavern/data/nginx/nginx /opt/nginx/sbin/initscript
ln -s /opt/nginx/sbin/initscript /etc/init.d/nginx

# Setup Tavern init script
ln -s /opt/Tavern/tavern.sh /etc/init.d/tavern


# Install the python deps.    
cd /opt/Tavern
pip-3.3 install -r requirements.txt

# Copy in the geo-lookup IP database. 
# We want to download it from http://dev.maxmind.com/geoip/legacy/install/city to pull the most recent free version.
mkdir -p /opt/Tavern/data
curl http://geolite.maxmind.com/download/geoip/database/GeoLiteCity.dat.gz >  /opt/Tavern/data/GeoIPCity.dat.gz
gunzip /opt/Tavern/data/GeoIPCity.dat.gz


# Install the Python3 port of PIL.
# Eventually, this will be unnecessary, but for now it still is ;(
cd /opt/Tavern/libs
git clone https://github.com/grahame/pil-py3k
cd pil-py3k

### If you are on 64_bit linux, you'll want to add the 64 bit lib dir as shown-
sed -i '196i\ \ \ \ \ \ \ \ add_directory(library_dirs, "/usr/lib/x86_64-linux-gnu")' setup.py

python3.3 setup.py install


# Install PyLZMA, after fixing it to be py3 compatible.
cd /opt/Tavern/libs
git clone https://github.com/fancycode/pylzma.git
cd pylzma
2to3 -f all -w *.py
python3.3 setup.py install

# If you're in prod, you may want to generate these things automatically. 
# If not, they happen at startup anyway, so you can ignore ;)
echo "/usr/bin/python /opt/Tavern/TopicList.py" > /etc/cron.hourly/generatetopics
echo "/usr/bin/python /opt/Tavern/ModList.py" > /etc/cron.daily/findmods


# Ensure all config files are created
/etc/init.d/tavern start initonly

chown vagrant:vagrant /opt/Tavern -R
chown vagrant:vagrant /opt/nginx -R

/etc/init.d/nginx start
/etc/init.d/tavern start

update-rc.d nginx defaults 
update-rc.d tavern defaults

# Update again, so the logs/etc that were just created by root are now Vagrant owned.
chown vagrant:vagrant /opt/Tavern -R
chown vagrant:vagrant /opt/nginx -R
/etc/init.d/tavern start

# Create a touchfile, so we don't run all these steps on every boot.
echo `date` >  /opt/Tavern/data/COMPLETED-INSTALL



