# Tavern system-install instructions
# Tavern is written to run on Python 3.3+, under Ubuntu or OSX.
# It'll almost certainly work on other systems, but the docs are yet to be written.
# 
#                               IMPORTANT!
#           This is not the recomended way for testing out Tavern.
#           There is a Vagrant Virtual Machine, which will be -MUCH- Easier.
#
#           If you want to check out Tavern, you should almost certainly use the Vagrant box, at least at first.
#           These instructions will install it directly on the machine -
#           This makes it run faster, but also is more invasive, and a lot more work. 
#           I strongly suggest you checkout the DOCS/Using-Vagrant file for instructions on installing via Vagrant instead.
#           
#           If you complain "Tavern is hard to install", and you used these instructions instead of the Vagrant box, I will cry.
#           Really. I'll cry like a baby. I'll help you, but I'll be helping through tears.
#
#
#

uname -a  | grep -i Darwin
if [ $? -eq 0 ]
then
    os='OSX'
    installroot="$HOME/opt"
fi
uname -a  | grep -i Linux
if [ $? -eq 0 ]
then
    os='LINUX'
    installroot="/opt"
fi
taverndir="$installroot/Tavern"



# Install the Needed packages.
# Note - This will also install MongoDB, which will run in the background.
# Anytime you are not using Tavern, you may want to disable this.
# Before you argue "That's not convienient", see the note labeled IMPORTANT at the top ;) 

# Package install for Ubuntu

if [ $os == 'LINUX' ]
then
    apt-get -y install curl g++ git-core gnupg java-common lib32z1 libfreetype6 libfreetype6-dev libjpeg8 libjpeg8-dev liblcms1-dev \
    libmagic-dev libmpc2 libpcre3-dev libpq-dev libssl-dev libtiff4-dev libwebp-dev libxml2-dev libxslt-dev libzzip-dev luajit make \
    mongodb python-imaging python3 python3-dev scons swig tcl8.5-dev tk8.5-dev yui-compressor zlib1g-dev libpq-dev libgmp-dev

# Package install for OSX
# Requires Homebrew - ( http://brew.sh/ )
elif [ $os == 'OSX' ]
then
    brew
    if [ $? -ne 0 ]
    then
        # Install Homebrew
        ruby -e "$(curl -fsSL https://raw.github.com/mxcl/homebrew/go/install)"
    fi
    brew install gnupg yuicompressor exiv2 libmagic mongodb python3 Boost gnu-sed scons autoconf automake libtool libxml2 libxslt libksba \
    libmpc gmp libtiff libjpeg webp littlecms postgres pcre
fi


# Install RVM, so we can load in a more recent ruby without messing up the system ruby
source $HOME/.rvm/scripts/rvm || source /etc/profile.d/rvm.sh > /dev/null
rvm -v > /dev/null
if [ $? -ne 0 ]
    then
    # RVM is not yet installed
    curl -L https://get.rvm.io | bash -s stable
    source $HOME/.rvm/scripts/rvm || source /etc/profile.d/rvm.sh
fi

# Install the Gems that convert the sass files into CSS
# Use a separate gemset as to not screw up system ruby.
rvm use 1.9.3@Tavern --create  --install
gem install sass compass bourbon

# Install the current Tavern source
if [ ! -d "$taverndir" ]
then
    mkdir -p $taverndir
    cd $taverndir
    git init
    git remote add git@github.com:e1ven/Tavern.git 
    git pull origin master
    chown -R "$USER" .
fi

### If you want to run through nginx, we should use a custom compiled version for upload/etc.
### You can skip this step, and just connect directly for development.
### If you want to run through nginx, we should use a custom compiled version for upload/etc.
### You can skip this step, and just connect directly for development.

mkdir -p $taverndir/tmp/nginx
cd $taverndir/tmp/nginx
NGINX_VER=1.4.4
wget http://nginx.org/download/nginx-$NGINX_VER.tar.gz   
tar xvfz nginx-$NGINX_VER.tar.gz
cd nginx-$NGINX_VER

wget https://github.com/vkholodkov/nginx-upload-module/archive/2.2.zip
unzip 2.2.zip
./configure --prefix=$installroot/nginx  --add-module=`pwd`/nginx-upload-module-2.2 --with-http_gzip_static_module --with-http_mp4_module --with-http_ssl_module 

make
make install

mkdir $installroot/uploads
chmod 777 $installroot/uploads/
mkdir -p $installroot/cache/tmp

rm /etc/init.d/nginx
rm $installroot/nginx/conf/nginx.conf
cp $installroot/Tavern/nginx/nginx /etc/init.d/nginx
chmod a+x /etc/init.d/nginx
ln -s $installroot/Tavern/nginx/nginx.conf $installroot/nginx/conf/nginx.conf
ln -s $installroot/Tavern/nginx/default.site $installroot/nginx/conf/default.site
mkdir -p $installroot/nginx/cache/tmp

# Create Tavern init file.
ln -s $installroot/Tavern/tavern.sh /etc/init.d/tavern

        
# Install the python deps.    
cd $taverndir/libs

# Ensure we have VirtualEnv, so we can create our own packages.
curl -O https://pypi.python.org/packages/source/v/virtualenv/virtualenv-1.10.tar.gz
tar -zxvf virtualenv-1.10.tar.gz

cd $taverndir
# Create a Virtual Environment, so we don't spew across the whole system
libs/virtualenv-1.10/virtualenv.py  --no-site-packages --distribute tmp/env -p `which python3.3`
source tmp/env/bin/activate

pip install -r requirements.txt

# Pull down a local copy of Robohash.org, so we don't need any outward links
cd libs
git clone https://github.com/e1ven/Robohash.git

# Copy in the geo-lookup IP database. 
# We want to download it from http://dev.maxmind.com/geoip/legacy/install/city to pull the most recent free version.
# This is not included in git because it is 17M, and frequently updated.
cd ../data
curl -O http://geolite.maxmind.com/download/geoip/database/GeoLiteCity.dat.gz
gunzip GeoLiteCity.dat.gz


# There is a list of user agents included in the Tavern 'data' directory.
# This list is -not- kept up to date, however. You can update it easily if you want to, but it is not necessary.
curl "http://user-agent-string.info/rpc/get_data.php?key=free&format=ini&download=y" > useragent.ini




# If you're in prod, you may want to generate various things on a schedule.
# If not, they happen at startup anyway, so you can ignore ;)
    echo "/usr/bin/python $taverndir/TopicList.py" > /etc/cron.hourly/generatetopics
    echo "/usr/bin/python $taverndir/ModList.py" > /etc/cron.daily/findmods

# Make sure your DB is running.
if [ $os == 'LINUX' ]
then
    /etc/init.d/mongodb start
elif [ $os == 'OSX' ]
then
    cd /tmp
    wget https://github.com/remysaissy/mongodb-macosx-prefspane/raw/master/download/MongoDB.prefPane.zip
    unzip MongoDB.prefPane.zip
    open MongoDB.prefPane &

    cd $taverndir
    ./start-dev-servers.sh
fi




# Start Tavern in Config mode, to generate all needed config files
./tavern start initonly

# Start Tavern for real, and run in the background.
./tavern.sh start


# SETTINGS
# Most settings should work automatically out of the box, but you may want to modify Domains to run things on your own.
# For instance, the serversetting 'embedserver' sends users to embed.is for embedded iframes.
# Feel free to run your own embed server, and change this setting to use it.

# Also, for production, you should change probably run a separate binaries server from / to a new domain.
# This will prevent some cookie reading attacks.
