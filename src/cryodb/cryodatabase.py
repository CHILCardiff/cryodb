import abc
import cryodecoder
import datetime
import importlib.resources
import mariadb
import os 
import pathlib
import sqlite3

from dataclasses import dataclass
from enum import Enum
from types import NoneType
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
    host="localhost",
    user=None,
    password=None,
    database="cryodb",
    port=3306
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
        if database is not None:
            maria_kwargs["database"] = database
        # Attempt to create MariaDB connector and pass to CryoDatabase
        try:
            return CryoDatabase(
                mariadb.connect(**maria_kwargs)
            )
        except mariadb.ProgrammingError:
            raise DatabaseNotFoundError(f"Could not find database {database} on host {host}:{port}")

class CryoDatabaseError(Exception):
    pass

class InvalidIngestEventError(CryoDatabaseError):
    pass

class InvalidDatabaseError(CryoDatabaseError):
    pass

class DatabaseNotFoundError(CryoDatabaseError):
    pass

class NoRecordInsertedError(CryoDatabaseError):
    pass

class RecordExistsError(CryoDatabaseError):
    pass

class IngestType(Enum):
    """Utility class to describe different ingest events
    """
    TEST    = 0
    WEBHOOK = 1
    SDCARD  = 2
    LOCAL   = 3
    MANUAL  = 4

class InstrumentType(Enum):
    """Utility class to describe different instrument types
    """
    Cryoegg     = "Cryoegg"
    Cryowurst   = "Cryowurst"

@dataclass
class IngestEvent:
    """Dataclass representing row in ingest_event_table
    """
    id              : int
    type            : IngestType
    description     : str
    timestamp       : datetime.datetime


class CryoDatabase:

    STRFTIME_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(
        self, 
        connection : Union[sqlite3.Connection, mariadb.Connection]
    ):
        """Accepts a SQLite3 or MariaDB connection object to initialise
        """

        # Store reference to connection locally
        self.connection = connection

        # Initialise ingest event id
        self.__ingest_event_id = None
        self.__ingest_event_obj = None

    def __is_sqlite(self):
        return isinstance(self.connection, sqlite3.Connection)

    def __is_mariadb(self):
        return isinstance(self.connection, mariadb.Connection)

    def cursor(self):
        return self.connection.cursor()
    
    def commit(self):
        self.connection.commit()
    
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
                raise InvalidDatabaseError("No database selected.")
            
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
                raise InvalidDatabaseError(f"Could not find table {valid_table} in database '{db_name}")
        
        # if all is okay to here
        return True

    def add_ingest_event(self, type : Union[str, int, IngestType],  description : str = "", timestamp : Union[NoneType, datetime.datetime] = None):
        """creates a new ingest event, specifying type
        """
        
        # creates new ingest event id
        # records type, description, timestamp
        
        # Set timestamp to current UTC
        if timestamp is None:
            timestamp = datetime.datetime.now(tz=datetime.timezone.utc)

        # Validate IngesstType
        if isinstance(type, str):
            if not type in IngestType.__members__:
                raise ValueError(f"Invalid IngestType {type}")
            else:
                type = IngestType.__members__[type]
        elif isinstance(type, int):
            type = IngestType(type)

        # Get cursor and construct query 

        parameters = {
            "type"      : type.name,
            "desc"      : description,
            "timestamp" : timestamp.strftime(CryoDatabase.STRFTIME_FORMAT)
        }

        cursor = self.cursor()
        if self.__is_mariadb():
            cursor.execute(
                "INSERT INTO `ingest_event_table` (`ingest_type`,`description`,`timestamp`) VALUES (?,?,?)", 
                (parameters['type'], parameters['desc'], parameters['timestamp'])
            )
        elif self.__is_sqlite():
            cursor.execute(
                "INSERT INTO `ingest_event_table` (`ingest_type`,`description`,`timestamp`) VALUES (:type,:desc,:timestamp)", 
                parameters
            )

        # Return last row id
        if cursor.lastrowid > 0:
            self.connection.commit()

        return cursor.lastrowid

    def set_ingest_event(self, id=None):
        """sets the current ingest event"""
        
        cursor = self.cursor();
        cursor.execute("SELECT COUNT(`ingest_event_id`) FROM `ingest_event_table` WHERE `ingest_event_id` = ?;", (id,))

        if cursor.fetchone()[0] != 1:
            raise InvalidIngestEventError("No ingest event with ingest_event_id:{id}")
        
        self.__ingest_event_id = id

    def get_ingest_event(self, id=None):

        # If id is none, select for the current object
        id = self.__ingest_event_id

        if id == None:
            raise ValueError("Cannot get IngestEvent object for ingest_event_id:None")

        # Check whether ingest event object is out of date
        if self.__ingest_event_obj is None or self.__ingest_event_id != self.__ingest_event_obj.id:

            # Request ingest_event information 
            cursor = self.cursor()
            cursor.execute("SELECT `ingest_event_id`, `ingest_type`, `description`, `timestamp` FROM `ingest_event_table` WHERE `ingest_event_id` = ?;", (self.__ingest_event_id,))

            results = cursor.fetchall()

            if len(results) != 1:
                raise ValueError("Cannot get IngestEvent object for ingest_event_id:{id}")
            
            return IngestEvent(
                id=results[0][0],
                type=IngestType.__members__[results[0][1]],
                description=results[0][2],
                timestamp=datetime.datetime.strptime(results[0][3], CryoDatabase.STRFTIME_FORMAT)
            )

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

    def ingest_sdcard(self, path, description=None, ingest_event : Union[IngestEvent, int, NoneType] = None, receiver_id : Union[int, NoneType] = None):
        """
        1. create ingest event with path and description in `ingest_event_table` and store event id

        2. open file at path and for each SDPacket:

            2a. create new `ingest_id` in `ingest_table`, assign hex-coded raw data to raw
            2b. get receiver packet and instrument/data packet
            2c. insert receiver data into `receiver_data_table`
            2d. select correct table from instrument packet (either cryoegg/cryowurst_data_table) and insert data
        """

        # If no ingest event is provided, then we will create a new one
        if ingest_event == None:
            
            event_id = self.add_ingest_event(
                type        = IngestType.SDCARD,
                description = str(path),
                # Don't pass timestamp so we use the current time
            )
        
        else:

            # other
            event_id = self.get_ingest_event().id

        # Open file in binary mode
        with open(path, "rb") as fh_sdcard:

            # Convert bytes to packets
            packets = cryodecoder.bytes_to_packets(fh_sdcard.read())

            # Iterate over packets
            for packet in packets:
                self.ingest_sdpacket(
                    packet, 
                    event_id, 
                    receiver_id = receiver_id, 
                    commit_on_complete=False
                )

            # Commit all changes
            self.commit()

    def ingest_sdpacket(self, packet, ingest_event_id : int, receiver_id : Union[int, NoneType] = None, commit_on_complete=True):
        """ingest a single SDPcaket (i.e. W1/W2/C0/C1 etc) style packet

        1. create new `ingest_id` in `ingest_table`, assign hex-coded raw data to raw
        2. get receiver packet and instrument/data packet
        3. insert receiver data into `receiver_data_table`
        4. select correct table from instrument packet (either cryoegg/cryowurst_data_table) and insert data
        """

        # Get database cursor
        cursor = self.cursor()

        # Create an ingest id
        cursor.execute(
            "INSERT INTO `ingest_table` (`ingest_event_id`, `raw`) VALUES (?,?);", (ingest_event_id, packet.raw)
        )

        # and get the value
        ingest_id = cursor.lastrowid
        assert ingest_id != -1 # for sqlite3 database

        # Strip SDPacket into constitutent parts
        receiver_data = packet.get_receiver_packet()
        instrument_data = packet.get_instrument_packet()

        # Assign receiver data ID
        receiver_data_id = None
        # Insert receiver data
        if receiver_data is not None:
            receiver_data_id = self.__insert_receiver_data(
                receiver_data, 
                ingest_id, 
                receiver_id = None, 
                commit_on_complete = False
            )

        # Insert receiver data
        instrument_data_id, instrument_type = self.__insert_instrument_data(
            instrument_data, 
            ingest_id, 
            commit_on_complete=False,
            receiver_data_id=receiver_data_id
        )

        # IF we should commit each insert operation then do so
        if commit_on_complete:
            self.commit()

        return receiver_data_id, instrument_data_id, instrument_type

    def __insert_receiver_data(self, packet : cryodecoder.ReceiverPacket, ingest_id, receiver_id : Union[NoneType, int] = None, commit_on_complete=True):
        
        # Validate receiver_id
        if packet.receiver_id == None:
            if receiver_id == None:
                raise ValueError("Cannot insert receiver data without receiver id.")
            else:
                # Assign the local receiver id
                packet.receiver_id = receiver_id
    
        # Insert values
        cursor = self.cursor()
        cursor.execute(
            "INSERT INTO `receiver_data` (`receiver_id`, `ingest_id`, `timestamp`, `channel`, `temperature_logger`, `pressure_logger`, `voltage_logger`) VALUES (?,?,?,?,?,?,?);",
            (
                receiver_id, ingest_id, packet.timestamp, packet.channel, packet.temperature, packet.pressure, packet.voltage
            )    
        )

        # Get last row ID
        receiver_data_id = cursor.lastrowid

        # Check that we inserted the record
        if receiver_data_id == -1:
            raise NoRecordInsertedError;

        # IF we should commit each insert operation then do so
        if commit_on_complete:
            self.commit()

        # Return row id
        return receiver_data_id

    def __insert_instrument_data(self, packet : cryodecoder.InstrumentPacket, ingest_id, receiver_data_id = None, commit_on_complete=True):
        """
        """

        instrument_type = None
        if isinstance(packet, cryodecoder.CryoeggPacket):

            cursor = self.cursor()
            cursor.execute("INSERT INTO `cryoegg_raw_table` (`receiver_data_id`, `ingest_id`, `instrument_id`, `conductivity_raw`, `temperature_pt1000_raw`, `pressure_raw`, `temperature_raw`, `battery_voltage`, `sequence_number`, `rssi`, `packet_version`) VALUES (?,?,?,?,?,?,?,?,?,?,?)", 
            (
                receiver_data_id,
                ingest_id,
                int(packet.id, 16), # convert from hex string to integer
                packet.conductivity,
                packet.temperature_pt1000,
                packet.pressure,
                packet.temperature,
                packet.battery_voltage,
                packet.sequence_number,
                packet.rssi,
                packet.uid
            ))

            instrument_type = InstrumentType.Cryoegg

            # Check that we inserted the record
            if cursor.lastrowid == -1:
                raise NoRecordInsertedError;

        elif isinstance(packet, cryodecoder.CryowurstPacket):

            instrument_type = InstrumentType.Cryowurst

        else:
            raise ValueError(f"Incompatible InstrumentPacket type {type(packet)}")
        
        instrument_id = cursor.lastrowid
        
        if commit_on_complete:
            self.commit()

        return instrument_id, instrument_type

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
    
    def add_instrument(self, 
        instrument_id : Union[str, int],
        type : InstrumentType,
        pressure_keller_max : Union[int, float],
        pressure_keller_min : Union[int, float, NoneType] = 0.0,
        manufacture_date : Union[datetime.datetime, NoneType] = None,
        manufacture_batch : Union[str, NoneType] = None,
        commission_date : Union[datetime.datetime, NoneType] = None,
        notes : Union[str, NoneType] = None
    ):
        """Adds a new instrument to the database
        """

        # Validate and convert the instrument ID
        if isinstance(instrument_id, str):
            try:
                instrument_id = int(instrument_id, 16)
            except ValueError:
                raise ValueError("String-like instrument_id should be in hexadecimal format.")
        elif instrument_id < 1:
            raise ValueError("instrument_id should be > 0")

        # Validate pressure_keller values
        if pressure_keller_max <= pressure_keller_min:
            raise ValueError(f"pressure_keller_max ({pressure_keller_max}) should be greater than pressure_keller_min ({pressure_keller_min}).")
        
        cursor = self.cursor()
        # Insert values
        try:
            cursor.execute("INSERT INTO `instrument_table` (`instrument_id`, `type`, `manufacture_date`, `manufacture_batch`, `commission_date`, `notes`, `pressure_keller_min`, `pressure_keller_max`) VALUES (?,?,?,?,?,?,?,?)", 
            (
                instrument_id,
                type.name,
                manufacture_date,
                manufacture_batch,
                commission_date,
                notes,
                pressure_keller_min,
                pressure_keller_max
            ))
        except (sqlite3.IntegrityError, mariadb.IntegrityError):
            raise RecordExistsError;

        # Commit new instrument to database
        self.commit()

        if cursor.lastrowid == -1:
            raise NoRecordInsertedError;

        # Return instrument_id
        return cursor.lastrowid
        
    def add_receiver(self, 
        receiver_id : Union[str, int, None] = None,
        receiver_type : Union[str, NoneType] = None,
        receiver_name : Union[str, NoneType] = None,
        firmware_version : Union[str, NoneType] = None,
        manufacture_date : Union[datetime.datetime, NoneType] = None,
        manufacture_batch : Union[str, NoneType] = None,
        commission_date : Union[datetime.datetime, NoneType] = None,
        notes : Union[str, NoneType] = None
    ):
        """Adds a new instrument to the database
        """

        # Validate and convert the instrument ID
        if isinstance(receiver_id, str):
            try:
                receiver_id = int(receiver_id, 16)
            except ValueError:
                raise ValueError("String-like receiver_id should be in hexadecimal format.")
        elif receiver_id > 0:
            raise ValueError("receiver_id should be > 0")
        
        cursor = self.cursor()
        # Insert values
        cursor.execute("INSERT INTO `receiver_table` (`receiver_id`, `name`, `type`, `firmware_version`, `manufacture_date`, `manufacture_batch`, `commission_date`, `notes`) VALUES (?,?,?,?,?,?,?,?)", 
        (
            receiver_id,
            receiver_type,
            receiver_name,
            firmware_version,
            manufacture_date.strftime(CryoDatabase.STRFTIME_FORMAT),
            manufacture_batch,
            commission_date.strftime(CryoDatabase.STRFTIME_FORMAT),
            notes
        ))

        # Commit new instrument to database
        self.commit()

        if cursor.lastrowid == -1:
            raise NoRecordInsertedError;

        # Return instrument_id
        return cursor.lastrowid
    
    def add_campaign(self, 
        name : Union[str],
        description : Union[str, NoneType] = None,
        latitude : Union[int, float, NoneType] = None,
        longitude : Union[int, float, NoneType] = None,
        elevation : Union[int, float, NoneType] = None,
        start_timestamp : Union[datetime.datetime, NoneType] = None,
        end_timestamp :  Union[datetime.datetime, NoneType] = None,
    ):
        
        # Validate position
        if latitude is None or longitude is None:
            raise ValueError("Both latitude and longitude must not be None if providing position.")
        
        if abs(latitude) > 90:
            raise ValueError("Latitude must be between -90.0 and 90.0 degrees.")
        
        if abs(longitude) > 180:
            raise ValueError("Longitude must be between -180.0 and 180.0 degrees.")
        
        cursor = self.cursor()
        # Insert values
        cursor.execute("INSERT INTO `campaign_table` (`name`, `description`, `latitude`, `longitude`, `elevation`, `start_timestamp`, `end_timestamp`) VALUES (?,?,?,?,?,?,?)", 
        (
            name,
            description,
            latitude,
            longitude,
            elevation,
            start_timestamp.strftime(CryoDatabase.STRFTIME_FORMAT),
            end_timestamp.strftime(CryoDatabase.STRFTIME_FORMAT)
        ))

        # Commit new instrument to database
        self.commit()

        if cursor.lastrowid == -1:
            raise NoRecordInsertedError;

        # Return instrument_id
        return cursor.lastrowid
        
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
                # We need to modify and remove any instance of AUTO_INCREMENT
                script = script.replace("AUTO_INCREMENT","")
                script = script.replace("INTEGER UNSIGNED NOT NULL PRIMARY KEY", "INTEGER NOT NULL PRIMARY KEY")
                
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