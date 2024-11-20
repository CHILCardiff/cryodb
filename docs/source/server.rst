``cryodb`` server
=================

The ``cryodb`` server exposes a REST API to retrieve data from a ``cryodb`` database.

The default port for the server is ``3291`` or ``cdb`` in hexadecimal.

We can implement these routes as Python functions, so the REST API is building on the internal Python API.

Authentication
--------------
To handle the case that we only want expose certain data and instruments to users of the database, we need some form of authentication mechanism.

Propose to achieve this using API keys, which are generated and then have a campaigns associated with them so that only instruments and receivers related to that campaign can be vieed.

API keys are then distributed and configured by the maintainer of the database being connected to.  Need to make an exception for local users in a sqlite3 databse.

.. note::
    Does this work for the case of testing/super-users? Can we create hidden campaigns that span multiple deployments? 

API hierarchy
-------------
An outline of the API hierarchy is given below::

    instrument/
        <type>/ [cryoegg, cryowurst, receiver, ...]
            list/

    receiver/
        list/
            
    data/
        <type>/ [cryoegg, cryowurst, receiver, ...]
            raw/
            processed/
                
    campaign/
        list/
        <name>/
            deployments/
            instruments/
            receivers/

Flask Configuration
-------------------
Flask has a default configuration file, defined within the ``cryodb.server.default_settings`` submodule. 

This can be overridden by providing a path to a new config file in the environment variable ``CRYODB_FLASK_CONFIG``.
