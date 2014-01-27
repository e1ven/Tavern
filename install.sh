#!/bin/bash -e

# This script will install Tavern to your local machine. 
# It should be safe to run even if Tavern is already installed.
# 
# Tavern is written to run on Python 3.4+, under Ubuntu and OSX.
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



function install_gem_if_nec 
{
    # Installs gem if it isn't already installed. 
    # Doesn't re-install existing gems, or trigger the `set -e`
    # 
    # Usage: install_gem_if_nec gemname

    if [ `gem list | grep "$1" >/dev/null; echo "$?"` -ne 0 ]
    then
        gem install "$1"
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

# Make sure only root can run our script
if [ "$(id -u)" != "0" ]; then
   echo "This script must be run as root, or with sudo."
   echo "Try sudo ./install.sh"
   exit 1
fi

prompt "installroot" "Where would you like to install to?" "/opt/tavern"
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

prompt "user" "What user should Tavern run under?" "$SUDO_USER"

echo "Installing System Packages..."
if [ "$os" == "LINUX" ]
then
    # Package install for Ubuntu
    apt-get -y install curl g++ git-core gnupg java-common lib32z1 libfreetype6 libfreetype6-dev libjpeg8 libjpeg8-dev liblcms1-dev \
    libmagic-dev libmpc2 libpcre3-dev libpq-dev libssl-dev libtiff4-dev libwebp-dev libxml2-dev libxslt-dev libzzip-dev luajit make \
    mongodb python-imaging python3 python3-dev scons swig tcl8.5-dev tk8.5-dev yui-compressor zlib1g-dev libpq-dev libgmp-dev

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
       
    sudo -u "$user" brew install gnupg yuicompressor exiv2 libmagic mongodb python3 Boost gnu-sed scons autoconf automake libtool libxml2 libxslt libksba \
    libmpc gmp libtiff libjpeg webp littlecms postgres pcre wget
fi

echo "Installing CSS Manipulation tools via Rubygems"
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


NGINX_VER=1.4.4
if [ ! -f $installroot/nginx/sbin/nginx ]
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
    ./configure --prefix=$installroot/nginx  --add-module="$nginxinstall/nginx-$NGINX_VER"/nginx-upload-module-2.2 --with-http_gzip_static_module --with-http_mp4_module --with-http_ssl_module 

    make
    make install
fi
echo "Linking nginx configs"
mkdir -p $installroot/nginx/uploads
chmod 777 $installroot/nginx/uploads/
mkdir -p $installroot/nginx/cache/tmp

mv $installroot/nginx/conf $installroot/nginx/original-unused-conf
ln -s $installroot/datafiles/nginx-config $installroot/nginx/conf


# echo "Creating initscript for Tavern"
# ln -s $installroot/Tavern/tavern.sh /etc/init.d/tavern

echo "Installing Python dependencies"        
cd $installroot
# Create a Virtual Environment, so we don't spew across the whole system
python3 -m venv $installroot/tmp/env
source $installroot/tmp/env/bin/activate
pip install -r $installroot/datafiles/python-requirements.txt

# Copy in the geo-lookup IP database. 
# We want to download it from http://dev.maxmind.com/geoip/legacy/install/city to pull the most recent free version.
# This is not included in git because it is 17M, and frequently updated.
if [ ! -f "$installroot/datafiles/GeoLiteCity.dat" ]
then
    echo "Retrieving GeoLite datafiles."
    cd $installroot/datafiles
    curl "http://geolite.maxmind.com/download/geoip/database/GeoLiteCity.dat.gz" -O "$installroot/datafiles/GeoLiteCity.dat.gz"
    gunzip "$installroot/datafiles/GeoLiteCity.dat.gz"
fi


# There is a list of user agents included in the Tavern 'data' directory.
# This list is -not- kept up to date, however. You can update it easily if you want to, but it is not necessary.
if [ ! -f "$installroot/datafiles/useragent.ini" ]
then
    echo "Retrieving UserAgent data."
    curl "http://user-agent-string.info/rpc/get_data.php?key=free&format=ini&download=y" > $installroot/datafiles/useragent.ini
fi



# # If you're in prod, you may want to generate various things on a schedule.
# # If not, they happen at startup anyway, so you can ignore ;)
#     echo "/usr/bin/python $taverndir/TopicList.py" > /etc/cron.hourly/generatetopics
#     echo "/usr/bin/python $taverndir/ModList.py" > /etc/cron.daily/findmods

# # Make sure your DB is running.
# if [ $os == 'LINUX' ]
# then
#     /etc/init.d/mongodb start
# elif [ $os == 'OSX' ]
# then
#     cd $taverndir/tmp
#     wget https://github.com/remysaissy/mongodb-macosx-prefspane/raw/master/download/MongoDB.prefPane.zip
#     unzip -f MongoDB.prefPane.zip
#     open MongoDB.prefPane &

#     cd $taverndir
#     ./start-dev-servers.sh
# fi




# # Start Tavern in Config mode, to generate all needed config files
# ./tavern start initonly

# # Start Tavern for real, and run in the background.
# ./tavern.sh start


# SETTINGS
# Most settings should work automatically out of the box, but you may want to modify Domains to run things on your own.
# For instance, the serversetting 'embedserver' sends users to embed.is for embedded iframes.
# Feel free to run your own embed server, and change this setting to use it.

# Also, for production, you should change probably run a separate binaries server from / to a new domain.
# This will prevent some cookie reading attacks.
