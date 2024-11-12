.. _development_index:

Development
===========

Initialisation
--------------
To initialise the database on a MariaDB server, start a bash window for the MariaDB docker container::

   docker exec -it --user root chiltest /bin/bash

Navigate to the mounted volume with the `cryodb`, `cryodecoder` and `cryoweb` repositories. You can then log in to the database and initialise the tables using::

   mariadb -u root --password=$MARIADB_ROOT_PASSWORD
   source cryodb/src/init/init_cryodb_test.sql;

**Note**
Need to address differences between SQLite and MariaDB. For example:

* Sqlite will automatically impose autoincremenet on INTEGER PRIMARY KEY, while MariaDB needs this explicitly