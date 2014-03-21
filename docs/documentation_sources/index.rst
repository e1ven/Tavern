Welcome To Tavern
=================
How to Install:
---------------
The easiest way to run Tavern is to start the Vagrant instance included inside.
See docs/Using-Vagrant for instructions.

Alternatively, You can install Tavern locally onto your machine.
If you are on Ubuntu 13.10 or OSX, the script ``install.sh`` should walk you through the install.

Once the installation is complete, you can start tavern by running
``tavern.sh start`` to start in the background
or
``tavern.sh debug`` to run without forking

Tavern is written in Python3 and Tornado.

How does Tavern Work?
=====================

Tavern is a Decentralized, Anonymous, Peer to Peer forum, written in Tornado and Python3.
It is designed to be censorship resistant, and is based on the idea of passing signed messages.
Each message is a JSON document, signed by a Public Key that is unique to each user.
We then pass these along to various servers, and organize them by Topics.

.. toctree::
   :maxdepth: 3

   for-users
   for-developers
   copying



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

