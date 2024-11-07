import abc
import importlib.resources
import mariadb
import os 
import pathlib
import sqlite3

from typing import Union

# Implement Connector as an abstract base class, its likely that the methods
# invovled will be different for both the MariaDB and SQL connectors

CRYODB_VALID_TABLES = [
    "hydrobean_raw_table",
    "hydrobean_data_table",
    "ingest_localpacket_table",
    "process_table",
    "ingest_event_table",
    "ingest_lingomo_table",
    "units_metadata_table",
    "cryoegg_data_table",
    "receiver_table",
    "conductivity_calibration_table",
    "receiver_deployment_table",
    "cryowurst_raw_table",
    "instrument_table",
    "campaign_table",
    "cryowurst_data_table",
    "receiver_data_table",
    "ingest_table",
    "ingest_manual_table",
    "instrument_deployment_table",
    "calibration_table",
    "cryoegg_raw_table"
]

def connect(
    # SQLite flags
    path=None,
    create_if_not_found=False,
    # MariaDB flags
    host=None,
    user=None,
    password=None,
    port=None
):
    """swap between a SQLite and MariaDB connector depending on where we are connecting"""

    # default to SQLite if possible
    if path is not None:

        # Convert path to a pathlib representation
        path = pathlib.Path(path)

        # If the file doesn't exist...
        if not path.exists():
            # we should either crash out because we don't want to over
            # write by default
            if create_if_not_found == False: 
                raise FileNotFoundError(f"Could not find {path}.")    
            # or we should initliase the database
            return CryoDatabase.initialise_sqlite3(path) 
        
        # ...othewise, return the CryoDatabase object with sqlite connector
        else:
            return CryoDatabase(
                sqlite3.connect(path)
            )
    
    else:
        # Create a list of parameters that are not none
        maria_kwargs = dict()
        if host is not None:
            maria_kwargs["host"] = host
        if user is not None:
            maria_kwargs["user"] = user
        if password is not None:
            maria_kwargs["password"] = password
        if port is not None:
            maria_kwargs["port"] = port
        # Attempt to create MariaDB connector and pass to CryoDatabase
        return CryoDatabase(
            mariadb.connect(**maria_kwargs)
        )

class CryoDatabase:

    class InvalidDatabaseError(Exception):
        pass

    def __init__(
        self, 
        connection : Union[sqlite3.Connection, mariadb.Connection]
    ):
        """Accepts a SQLite3 or MariaDB connection object to initialise
        """

        # Store reference to connection locally
        self.connection = connection

    def __is_sqlite(self):
        return isinstance(self.connection, sqlite3.Connection)

    def __is_mariadb(self):
        return isinstance(self.connection, mariadb.Connection)

    def cursor(self):
        return self.connection.cursor()
    
    def disconnect(self):
        if isinstance(self.connection,  Union[sqlite3.Connection, mariadb.Connection]):
            self.connection.close()

    def validate(self):
        """Validates the database connected to the MariaDBConnector"""

        # Step 1 - validate the connected database
        cursor = self.cursor()

        if self.__is_mariadb():
            cursor.execute("SELECT DATABASE();")
        
            # fetchone returns a tuple, so check that the first element isn't None
            # to proceed
            db_name = cursor.fetchone()[0]

            if db_name == None:
                raise CryoDatabase.InvalidDatabaseError("No database selected.")
            
            # Step 2 - valid a list of tables 
            cursor.execute("SELECT `table_name` FROM `information_schema`.`tables` WHERE `table_schema` = (SELECT DATABASE());")

        elif self.__is_sqlite():
            
            cursor.execute("SELECT `name` FROM `sqlite_master` WHERE `type` = 'table';")

        # we need to strip the first element from the tuple returned as row 
        # to get a list of tables
        tables = [row[0] for row in cursor.fetchall()];

        # then check against valid tables
        for valid_table in CRYODB_VALID_TABLES:
            if not valid_table in tables:
                raise CryoDatabase.InvalidDatabaseError(f"Could not find table {valid_table} in database '{db_name}")
        
        # if all is okay to here
        return True

    def create_ingest_event(type, name=None, description="", timestamp=None):
        """creates a new ingest event, specifying type"""
        
        # creates new ingest event id
        # records type, description, timestamp
        pass

    def set_ingest_event(id=None, name=None):
        """sets the current ingest event"""
        pass

    def ingest_lingomo(json):
        """
        1. takes json, parses into LingoMO packet

        2. In ingest_table: create new ingest_id, assign to current ingest_event_id, assign raw json

        3. Using ingest_id, create new row in `ingest_lingomo_table` with metadata from LingoMO packet

        4. Get SDPackets from bytes in LingoMO payload/message:

            4a. for each packet, get receiver packet and instrument/data packet
            4b. insert receiver data into `receiver_data_table`
            4c. select correct table from instrument packet (either cryoegg/cryowurst_data_table) and insert data
        """
        pass

    def ingest_sdcard(path, description=None):
        """
        1. create ingest event with path and description in `ingest_event_table` and store event id

        2. open file at path and for each SDPacket:

            2a. create new `ingest_id` in `ingest_table`, assign hex-coded raw data to raw
            2b. get receiver packet and instrument/data packet
            2c. insert receiver data into `receiver_data_table`
            2d. select correct table from instrument packet (either cryoegg/cryowurst_data_table) and insert data
        """
        pass

    def ingest_localpacket(packet_obj, ingest_event_id):
        """
        assmues we already have a LocalUSBPacket from cryodecoder 
        assumes (or checks!) we have started a local ingest event

        1. create new entry in `ingest_table`, assign raw data from packet_obj to raw

        2. using ingest_id, assign local timestamp (from packet_obj) to `ingest_localpacket_table` (and any other parameters, maybe)

        3. insert data into relevant tables:
            3a. get receiver packet and instrument/data packet from packet_obj 
            3b. insert receiver data into `receiver_data_table`
            3c. select correct table from instrument packet (either cryoegg/cryowurst_data_table) and insert data
        """
        pass

    @staticmethod
    def initialise_sqlite3(path : Union[str, pathlib.Path]):

        if isinstance(path, str):
            path = pathlib.Path(path)

        # Check whether the DB already exists
        if path.exists():
            raise FileExistsError(f"Path {path} already exists!")
        
        # Open connection to database
        db_object = sqlite3.connect(path)

        resource_root = importlib.resources.files("cryodb.resources.sql.init")
        for resource in resource_root.iterdir():
            
            # TODO check file extension is .sql/.SQL
            # Read and execute each file
            with open(resource, "r") as sql_file:

                script = sql_file.read()
                try: 
                    db_object.executescript(script)
                except Exception as e:
                    # Cleanup by closing DB and removing file
                    db_object.close()
                    os.remove(path)
                    raise e
                
        cryo_db = CryoDatabase(db_object)
        cryo_db.validate()

        return cryo_db