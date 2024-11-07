import abc
import mariadb

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

class CryoDatabase:

    class InvalidDatabaseError(Exception):
        pass

    def connect(**kwargs):
        """swap between a SQLite and MariaDB connector depending on where we are connecting"""
        pass

    def cursor(self):
        return self.connection.cursor()

    def validate(self):
        """Validates the database connected to the MariaDBConnector"""

        # Step 1 - validate the connected database
        cursor = self.cursor()
        cursor.execute("SELECT DATABASE();")
        
        # fetchone returns a tuple, so check that the first element isn't None
        # to proceed
        db_name = cursor.fetchone()[0]

        if db_name == None:
            raise CryoDatabase.InvalidDatabaseError("No database selected.")
        
        # Step 2 - valid a list of tables 
        cursor.execute("SELECT `table_name` FROM `information_schema`.`tables` WHERE `table_schema` = (SELECT DATABASE());")

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
