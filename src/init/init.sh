#!/bin/bash
mariadb -u root --password=$MARIADB_ROOT_PASSWORD < init_user.sql
mariadb -u root --password=$MARIADB_ROOT_PASSWORD --database=cryodb_test < init_database.sql
mariadb -u root --password=$MARIADB_ROOT_PASSWORD --database=cryodb_test < init_metadata.sql
