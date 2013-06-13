apt-key adv --keyserver keyserver.ubuntu.com --recv 7F0CEB10
echo 'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen' | sudo tee /etc/apt/sources.list.d/10gen.list


apt-get update
apt-get -y install mongodb-10gen luajit libluajit-5.1-dev g++ libpcre3-dev zlib1g-dev libssl-dev python-dev swig libfreetype6 libfreetype6-dev libjpeg8-dev libjpeg8 libzzip-dev libxml2-dev libxslt-dev python3.3 python3.3-dev libmagic-dev python-imaging java-common yui-compressor  gnupg make git-core scons libpq-dev curl lib32z1

# Install Distribute + Pip
curl http://python-distribute.org/distribute_setup.py | python3.3
curl https://raw.github.com/pypa/pip/master/contrib/get-pip.py | python3.3


# Temporarily add /usr/local/bin to the path so root can run pip-3.3,etc
PATH=$PATH:/usr/local/bin

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



./configure --with-http_ssl_module  --prefix=/opt/nginx  --with-http_stub_status_module \
--add-module=/usr/local/src/nginx-1.4.1/nginx-gridfs  --add-module=/usr/local/src/nginx-1.4.1/ngx_devel_kit-0.2.18 --add-module=/usr/local/src/nginx-1.4.1/lua-nginx-module \
--with-cc-opt='-Wno-missing-field-initializers -Wno-unused-function -Wno-unused-but-set-variable -D_POSIX_SOURCE'


make
make install

mkdir /opt/uploads
chmod 777 /opt/uploads/
mkdir -p /var/www/cache/tmp

cd /opt/nginx
git clone https://github.com/pgaertig/nginx-big-upload.git
    
    
# Install the current Tavern source
cd /opt
sudo git clone https://tavern-readonly:MzVFhh6YtE7Kkx@github.com/e1ven/Tavern.git
cd Tavern
mkdir -p libs

cd /opt/Tavern/nginx
cp nginx.conf /opt/nginx/conf/

cd /opt/Tavern/nginx
cp nginx /opt/nginx/sbin/initscript
ln -s /opt/nginx/sbin/initscript /etc/init.d/nginx
ln -s /opt/Tavern/tavern.sh /etc/init.d/tavern


# Install the python deps.    
cd /opt/Tavern
pip-3.3 install -r requirements.txt

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

chown vagrant:vagrant /opt/Tavern -R
chown vagrant:vagrant /opt/nginx -R

/etc/init.d/nginx start
/etc/init.d/tavern start

update-rc.d nginx defaults 
update-rc.d tavern defaults