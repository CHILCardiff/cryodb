-- update this to have more nuanced privileges for chiltest
CREATE USER IF NOT EXISTS chiltest IDENTIFIED BY 'cryoparty';
GRANT ALL PRIVILEGES ON *.* TO 'chiltest';

CREATE DATABASE cryodb_test;
USE cryodb_test;

SOURCE init_schema.sql;