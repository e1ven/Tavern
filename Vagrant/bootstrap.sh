apt-get update
apt-get -y install g++ libpcre3-dev zlib1g-dev libssl-dev python-dev swig libfreetype6 libfreetype6-dev libjpeg8-dev libjpeg8 libzzip-dev libxml2-dev libxslt-dev python3 python3-dev libmagic-dev python-imaging java-common yui-compressor  gnupg make git-core scons libpq-dev curl lib32z1

apt-key adv --keyserver keyserver.ubuntu.com --recv 7F0CEB10
echo 'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen' | sudo tee /etc/apt/sources.list.d/10gen.list

apt-get install mongodb-10gen


# Install RVM
curl -L https://get.rvm.io | bash -s stable --ruby
source /usr/local/rvm/scripts/rvm

rvm install 1.9.3
rvm use 1.9.3 --default

# Install the Gems that convert the sass files into CSS
gem install sass compass

# Compile Nginx
cd /usr/local/src
wget http://nginx.org/download/nginx-1.4.1.tar.gz   
tar xvfz nginx-1.4.1.tar.gz
cd nginx-1.4.1

wget http://www.grid.net.ru/nginx/download/nginx_upload_module-2.2.0.tar.gz
tar -zxvf nginx_upload_module-2.2.0.tar.gz
git clone https://github.com/mdirolf/nginx-gridfs.git
CFLAGS="$CFLAGS -Wno-missing-field-initializers"
cd nginx-gridfs
git submodule init
git submodule update
cd mongo-c-driver
git checkout v0.7.1
cd ../..
./configure --add-module=/usr/local/src/nginx-1.4.1/nginx_upload_module-2.2.0 --with-http_ssl_module  --prefix=/opt/nginx  --with-http_stub_status_module --add-module=/usr/local/src/nginx-1.4.1/nginx-gridfs --add-module=/usr/local/src/nginx-1.4.1/ngx_pagespeed-release-1.5.27.1-beta --with-cc-opt='-Wno-missing-field-initializers -Wno-unused-function -D_POSIX_SOURCE'
make
make install

mkdir /opt/uploads
chmod 777 /opt/uploads/
mkdir -p /var/www/cache/tmp
    
    
# Install the current Tavern source
cd /opt
sudo git clone https://tavern-readonly:MzVFhh6YtE7Kkx@github.com/e1ven/Tavern.git

cd /opt/Tavern/nginx
cp nginx.conf /opt/nginx/conf/

cd /opt/Tavern/nginx
cp nginx /opt/nginx/sbin/initscript
ln -s /opt/nginx/sbin/initscript /etc/init.d/nginx
ln -s /opt/Tavern/tavern.sh /etc/init.d/tavern


# Install the python deps.    
cd /opt/Tavern
pip3 install -r requirements.txt

# Copy in the geo-lookup IP database. 
# We want to download it from http://dev.maxmind.com/geoip/legacy/install/city to pull the most recent free version.
mkdir -p /usr/local/share/GeoIP
curl http://geolite.maxmind.com/download/geoip/database/GeoLiteCity.dat.gz >  /usr/local/share/GeoIP/GeoIPCity.dat.gz
gunzip /usr/local/share/GeoIP/GeoIPCity.dat.gz


# Install the Python3 port of PIL.
# Eventually, this will be unnecessary, but for now it still is ;(
cd /opt/Tavern/libs
git clone https://github.com/grahame/pil-py3k
cd pil-py3k

### If you are on 64_bit linux, you'll want to add the 64 bit lib dir as shown-
 #   vi setup.py
 #   on line 196, add
 #   add_directory(library_dirs, "/usr/lib/x86_64-linux-gnu")

python3 setup.py install


# Install PyLZMA, after fixing it to be py3 compatible.
cd /opt/Tavern/libs
git clone https://github.com/fancycode/pylzma.git
cd pylzma
2to3 -f all -w *.py
python3 setup.py install

# If you're in prod, you may want to generate these things automatically. 
# If not, they happen at startup anyway, so you can ignore ;)
echo "/usr/bin/python /opt/Tavern/TopicList.py" > /etc/cron.hourly/generatetopics
echo "/usr/bin/python /opt/Tavern/ModList.py" > /etc/cron.daily/findmods


cd /opt/Tavern

./start-dev-servers.sh
./tavern.sh daemon 