#!/bin/bash -e

# This script will install Tavern to your local machine. 
# It should be safe to run even if Tavern is already installed.
# 
# Tavern is written to run on Python 3.4+, under Ubuntu and OSX.
# It'll almost certainly work on other systems, but the docs are yet to be written.
# 
#                               IMPORTANT!
#           This is not the recommended way for testing out Tavern.
#           There is a Vagrant Virtual Machine, which will be -MUCH- Easier.
#
#           If you want to check out Tavern, you should almost certainly use the Vagrant box, at least at first.
#           These instructions will install it directly on the machine -
#           This makes it run faster, but also is more invasive, and a lot more work. 
#           I strongly suggest you checkout the DOCS/Using-Vagrant file for instructions on installing via Vagrant instead.
#           
#           If you complain "Tavern is hard to install", and you used these instructions instead of the Vagrant box, I will cry.
#           Really. I'll cry like a baby. I'll help you, but I'll be helping through tears.

function install_gem_if_nec 
{
    # Installs gem if it isn't already installed. 
    # Doesn't re-install existing gems, or trigger the `set -e`
    # 
    # Usage: install_gem_if_nec gemname

    if [ `gem list | grep "$1" >/dev/null; echo "$?"` -ne 0 ]
    then
        sudo gem install "$1"
    fi
}

function prompt 
{
    # Prompts for a answer, and saves into a variable
    # Used because OSX ships with a BASH that doesn't support read -i 
    # 
    # Usage: prompt 'variable' 'Whatever you want to say' ['default']
    
    DEST="$1"
    QUESTION="$2"
    DEFAULT="$3"

    # Clear any current value in dest
    eval "$DEST"=""

    # Check for a default value
    if [ ! -z "$DEFAULT" ]
    then
        myprompt="$QUESTION [ $DEFAULT ] "
    else
        myprompt="$QUESTION "
    fi
    echo -n "$myprompt"
    read "$DEST"

    # If they didn't enter anything, use the default, using indirect references.
    if [ -z "${!DEST}" ]
    then
        eval "$DEST"="$DEFAULT"
    fi
}

# Determine the User to run under
if [ "$(id -u)" != "0" ]
then
    prompt "user" "What user should Tavern run under?" `whoami`
else
    prompt "user" "What user should Tavern run under?" "$SUDO_USER"
fi

# Determine if that user exists
if [ `sudo -u $user -n uptime >/dev/null 2>&1; echo $?` -ne 0 ]
then
    echo "That user does not currently exist, and the install script is not yet smart enough to create users. :("
    echo "Aborting."
    exit 1
fi

# Determine if we are able to sudo to that user
if [ `sudo -n $user uptime 2>/dev/null | wc -l` -gt 0 ]
then
    echo "Sure thing - We'll install as user $user."
else
    echo "Please note, you may be prompted for your computer password in order to switch to $user"
fi

prompt "installroot" "Where would you like to install to?" `pwd`
echo "Installing to - $installroot"

# OSX or Linux?

echo -n "Determining OS type: "
if [ `uname -a | grep -i Darwin >/dev/null; echo "$?"` -eq 0 ]
then
    os='OSX'
elif [`uname -a | grep -i Linux > /dev/null; echo "$?"` -eq 0 ]
then
    os='LINUX'
fi
echo "OS is $os."

echo "Installing System Packages..."
if [ "$os" == "LINUX" ]
then
    # Package install for Ubuntu
    apt-get -y install g++ git-core gnupg java-common lib32z1 libfreetype6 libfreetype6-dev libjpeg8 libjpeg8-dev liblcms1-dev \
    libmagic-dev libmpc2 libpcre3-dev libpq-dev libssl-dev libtiff4-dev libwebp-dev libxml2-dev libxslt-dev libzzip-dev luajit make \
    python-imaging python3 python3-dev scons swig tcl8.5-dev tk8.5-dev zlib1g-dev libpq-dev libgmp-dev default-jre

elif [ "$os" == "OSX" ]
then
    # The Package install for OSX uses homebrew.
    # We need to make sure this is installed before we can continue.
    
    if [ ! -f /usr/local/bin/brew ]
    then
        echo "You do not yet have the Homebrew package manager installed. (http://brew.sh/) "
        echo "This is necessary to install Tavern :( "
        prompt "install_homebrew" "Would you like to attempt to install homebrew automatically?" "yes"
        if [ "$install_homebrew" != "yes" ]
        then
            echo "Homebrew cannot be found, and install cannot continue without it."
            exit 1
        else
            echo "Attempting to install homebrew."
            sudo -u "$user" ruby -e "$(curl -fsSL https://raw.github.com/Homebrew/homebrew/go/install)"
        fi 
    fi
       
    sudo -u "$user" brew install git exiv2 libmagic python3 Boost gnu-sed scons autoconf automake libtool libxml2 libxslt libksba \
    libmpc gmp libtiff libjpeg webp littlecms postgres pcre wget gpg
fi

echo "Installing Sass via Rubygems"
install_gem_if_nec sass
install_gem_if_nec compass
install_gem_if_nec bourbon

echo "Downloading current Tavern source"

# Install the current Tavern source
if [ ! -d "$installroot" ]
then
    mkdir -p "$installroot"
    git clone git@github.com:e1ven/Tavern.git "$installroot"
else
    echo "$installroot exists"
    if [ -f "$installroot/tavern.sh" ]
    then
        prompt "overwrite_existing" "The given directory appears to already have a Tavern installation. Should it be updated?" "Yes"
        if [ "$overwrite_existing" == "Yes" ]
        then
            cd "$installroot"
            git stash
            git checkout origin/master
        fi
    else
        echo "The specified directory exists and does not appear to be a Tavern installation. Please remove, or re-run and specify a different directory."
    fi
fi
chown -R "$user" "$installroot"

# INSTALL NGINX

NGINX_VER=1.5.7
if [ -f $installroot/utils/nginx/sbin/nginx ]
then
    # If it's installed, remove if it's an old version.
    CURRENT_VER=`$installroot/utils/nginx/sbin/nginx -v 2>&1| awk -F/ {'print $2'}`
    if [ "$CURRENT_VER" != "$NGINX_VER" ]
    then
      rm $installroot/utils/nginx/sbin/nginx
    fi
fi

if [ ! -f $installroot/utils/nginx/sbin/nginx ]
then
    echo "Installing nginx $NGINX_VER"
    nginxinstall=$installroot/tmp/nginx_install
    mkdir -p $nginxinstall
    cd $nginxinstall

    wget http://nginx.org/download/nginx-$NGINX_VER.tar.gz
    tar xfz nginx-$NGINX_VER.tar.gz
    cd $nginxinstall/nginx-$NGINX_VER


    wget https://github.com/vkholodkov/nginx-upload-module/archive/2.2.zip
    unzip 2.2.zip

    ./configure --prefix=$installroot/utils/nginx  --add-module="$nginxinstall/nginx-$NGINX_VER"/nginx-upload-module-2.2 --with-http_gzip_static_module --with-http_mp4_module --with-http_ssl_module

    make
    make install
fi
echo "Linking nginx configs"

mkdir -p $installroot/tmp/uploads
mkdir -p $installroot/tmp/nginxcache

rm -rf $installroot/utils/nginx/conf || true
rm -rf $installroot/utils/nginx/logs || true
rm -rf $installroot/utils/nginx/html || true

ln -s $installroot/datafiles/nginx-config $installroot/utils/nginx/conf


# INSTALL MONGODB

MONGO_VER=2.4.9
if [ ! -f $installroot/utils/mongodb/bin/mongod ]
then
    echo "Installing MongoDB $MONGO_VER"
    mongoinstall=$installroot/tmp/mongo_install
    mkdir -p $mongoinstall
    cd $mongoinstall
    if [ "$os" == "LINUX" ]
    then
        wget http://downloads.mongodb.org/linux/mongodb-linux-x86_64-$MONGO_VER.tgz
        tar -zxf mongodb-linux-x86_64-$MONGO_VER.tgz
        mkdir -p $installroot/utils/mongodb
        mv mongodb-linux-x86_64-$MONGO_VER/* $installroot/utils/mongodb
    elif [ "$os" == "OSX" ]
    then
        wget http://downloads.mongodb.org/osx/mongodb-osx-x86_64-$MONGO_VER.tgz
        tar -zxf mongodb-osx-x86_64-$MONGO_VER.tgz
        mkdir -p $installroot/utils/mongodb
        mv mongodb-osx-x86_64-$MONGO_VER/* $installroot/utils/mongodb
    fi
fi


# echo "Creating initscript for Tavern"
# ln -s $installroot/Tavern/tavern.sh /etc/init.d/tavern

echo "Installing Python dependencies"        
cd $installroot
python3 -m venv $installroot/tmp/env || true
source $installroot/tmp/env/bin/activate
if [ ! -f $installroot/tmp/env/bin/pip ]
then
    # Python3.3 doesn't include pip by default, although Python3.4 does :/
    wget https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py -O - | python
    wget https://raw.github.com/pypa/pip/master/contrib/get-pip.py -O - | python
fi
pip install -r $installroot/datafiles/python-requirements.txt

# Copy in the geo-lookup IP database. 
# We want to download it from http://dev.maxmind.com/geoip/legacy/install/city to pull the most recent free version.
# This is not included in git because it is 17M, and frequently updated.
if [ ! -f "$installroot/datafiles/GeoLiteCity.dat" ]
then
    echo "Retrieving GeoLite datafiles."
    cd $installroot/datafiles
    wget "http://geolite.maxmind.com/download/geoip/database/GeoLiteCity.dat.gz" -O "$installroot/datafiles/GeoLiteCity.dat.gz"
    gunzip "$installroot/datafiles/GeoLiteCity.dat.gz"
fi


# There is a list of user agents included in the Tavern 'data' directory.
# This list is -not- kept up to date, however. You can update it easily if you want to, but it is not necessary.
if [ ! -f "$installroot/datafiles/useragent.ini" ]
then
    echo "Retrieving UserAgent data."
    wget "http://user-aglent-string.info/rpc/get_data.php?key=free&format=ini&download=y" -O "$installroot/datafiles/useragent.ini"
fi

# Create
mkdir -p "$installroot/logs"


chown -R "$user" "$installroot"

echo "Tavern is now installed."
echo "This setup should be sufficent for testing and dev."
echo "Reminder - Tavern is NOT ready to be used outside of development. It's -not- safe!"