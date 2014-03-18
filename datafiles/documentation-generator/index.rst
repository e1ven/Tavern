.. Tavern documentation master file, created by
   sphinx-quickstart on Mon Mar  3 15:24:31 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


How to Install:
===============
The easiest way to run Tavern is to start the Vagrant instance included inside.
See docs/Using-Vagrant for instructions.

Alternatively, You can install Tavern locally onto your machine.
If you are on Ubuntu 13.10 or OSX, the script ``install.sh`` should walk you through the install.

Once the installation is complete, you can start tavern by running
``tavern.sh start`` to start in the background
or
``tavern.sh debug`` to run without forking

Tavern is written in Python3 and Tornado.

Messages
========

Tavern is a Decentralized, Anonymous, Peer to Peer forum, written in Tornado and Python3.
It is designed to be censorship resistant, and is based on the idea of passing signed messages.

There is a Specification for messages in the "Spec" directory, but the basic format is very simple.
Each message is a JSON document, signed by a Public Key that is unique to each user.

We then pass these along to various servers, and organize them by Topics.


Code Documentation
==================
.. toctree::
   :maxdepth: 4

   libtavern
   webtav


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

