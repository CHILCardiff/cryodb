``cryodb`` server
=================

The ``cryodb`` server exposes a REST API to retrieve data from a ``cryodb`` database.

The default port for the server is ``3291`` or ``cdb`` in hexadecimal.

.. note::
    We can implement these routes as Python functions, so the REST API is building on the internal Python API.

Authentication
--------------
To handle the case that we only want expose certain data and instruments to users of the database, we need some form of authentication mechanism.

Propose to achieve this using API keys, which are generated and then have a campaigns associated with them so that only instruments and receivers related to that campaign can be viewed.

API keys are then distributed and configured by the maintainer of the database being connected to.  Need to make an exception for local users in a sqlite3 databse.  This requires that the priviledges of the MariaDB user configured with the database are appropriately restricted.

There are three types of API keys

* **ADMIN** keys permit access to the entire database.
* **USER** keys are for individual access to the ``cryodb`` database and can be associated with campaigns, so that only instruments and receivers deployed on those campaigns are visible.
* **SERVICE** keys are for automated access to the ``cryodb`` database, i.e. when an external service is pulling data.  Otherwise they behave the same as **USER** keys.
* **IP** keys are for automated access to the ``cryodb`` database, where elevated permissions are granted on the basis of the IP address used.  This is necessary to integrate with Cloudloop.+

The API requires that an environment variable ``CRYODB_SALT`` is configured on the server.  This should be set to a pseudo-random ASCII string or pass-phrase which prevents raw keys from being stored in the database. 

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
            <id>/
                raw/
                processed/
                
    campaign/
        list/
        <name>/
            deployments/
            instruments/
            receivers/

    ingest/
        lingomo/

Flask and WSGI configuration
----------------------------
The ``cryodb`` server is implemented using the Flask WSGI web framework. Following the documentation available `here <https://flask.palletsprojects.com/en/stable/deploying/mod_wsgi/>`_, it can be run using the ``mod_wsgi-express`` command from the Python `mod-wsgi <https://pypi.org/project/mod-wsgi/>`_ module.



Flask has a default configuration file, defined within the ``cryodb.server.default_settings`` submodule. 

This can be overridden by providing a path to a new config file in the environment variable ``CRYODB_FLASK_CONFIG``.

.. code-block:: bash

    $ export CRYODB_FLASK_CONFIG="/path/to/config.cfg"

The configuration variables are described in the table below.  The database username and password should be updated from the default values, and it is not recommended to expose the MariaDB port (3306) outside of the server.

+-----------------+-------------------+-------------------------------------------------------------------------------------------------+
| Variable        | Default           | Description                                                                                     |
+=================+===================+=================================================================================================+
| DATABASE        | "mariadb"         | Selects the type of database to use. Only MariaDB is implemented for the ``cryodb.server`` API. |
+-----------------+-------------------+-------------------------------------------------------------------------------------------------+
| CRYODB_USER     | "cryodb_user"     | MariaDB username.                                                                               |
+-----------------+-------------------+-------------------------------------------------------------------------------------------------+
| CRYODB_PASSWORD | "cryodb_password" | MariaDB password.                                                                               |
+-----------------+-------------------+-------------------------------------------------------------------------------------------------+
| CRYODB_DATABASE | "cryodb"          | MariaDB database name. Allows hosting multiple versions of cryodb for testing.                  |
+-----------------+-------------------+-------------------------------------------------------------------------------------------------+
| CRYODB_PORT     | 3306              | MariaDB port                                                                                    |
+-----------------+-------------------+-------------------------------------------------------------------------------------------------+
| CRYODB_HOST     | "localhost"       | MariaDB hostname                                                                                |
+-----------------+-------------------+-------------------------------------------------------------------------------------------------+

The WSGI application is launched from ``cryodb.wsgi`` which looks like

.. code-block:: python

    from cryodb.server import create_app
    application = create_app()

To start the WSGI server manually, use the following commands to activate the virtual environment and then run the wsgi server.

.. code-block:: bash

    source /path/to/.env/bin/activate
    (.env) $ mod_wsgi-express start-server /path/to/cryodb.wsgi --processes 4 --port 3291

Replace ``--processes 4`` with twice the number of CPUs available on the server, or the maximum number of processes to create while serving the API.

.. note:: 

    Work out how to start the server automatically in a daemon process