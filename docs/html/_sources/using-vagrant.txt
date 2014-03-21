Using Vagrant
=============

Tavern includes a Vagrant virtual machine, which should make it easy to run Tavern with minimal setup.

Before you run the virtual machine, make sure you have Virtualbox installed. (https://virtualbox.org/wiki/Downloads)
You will also need Vagrant installed (http://downloads.vagrantup.com)

Then, just cd to the Vagrant directory ( Tavern/datafiles/Vagrant) and run "vagrant up"
The VM should install everything it needs, and then fire up Tavern.

If everything went smoothly, you should be able to connect to Vagrant at:
    http://127.0.0.1:8080/

To administrate the machine, cd to the Vagrant directory, and run "vagrant ssh"

Creating your own Vagrant base image.
=====================================

The standard Tavern Vagrant box will download a basic Ubuntu install,
and then install Tavern onto it using the normal install.sh script.

If you don't trust this base image (And frankly, you probably shouldn't..),
you can make your own using veewee.

To create your own image, first install veewee-

    1) git clone https://github.com/jedi4ever/veewee.git
	2) cd veewee
	3) rvm install ruby-1.9.2-p320
	4) rvm use ruby-1.9.2-p320
	5) gem install bundler
	6) bundle install

Then, use veewee to create a base image.

	1) veewee vbox define 'tavern-minimal' 'ubuntu-13.10-server-amd64'
	2) bundle exec veewee vbox build 'tavern-minimal'
	3) bundle exec veewee vbox export 'tavern-minimal'
	4) cp tavern-minimal.box ..
	5) cd ..
	6)
		change the line in the Vagrantfile from
		  config.vm.box_url = "https://www.dropbox.com/s/xnayxfshxobvrsu/tavern-minimal.box"
		to
		  config.vm.box_url = "tavern-minimal.box"