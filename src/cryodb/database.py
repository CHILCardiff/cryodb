# Import logger
from .__init__ import cryodb_logger

import abc
import base64 
import cryodecoder
import datetime
import hashlib
import importlib.resources
import ipaddress
import json
import logging
import mariadb
import os 
import pathlib
import re
import secrets
import sqlite3

from dataclasses import dataclass
from enum import Enum
from types import NoneType
from typing import Union, Iterable

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

def log_exceptions(func): 
    """
    log exceptions to the configured log file
    """
    try:
        func()
    except Exception as e:
        # Do logging
        pass
        # Re-raise exception
        raise e

def sql_transaction(func):
    """
    wrap a function in a sql transaction to ensure rollback on exceptions
    """
    def self_wrapper(*args, **kwargs):
        # Get self from arguments
        self = args[0]
        # Check if we are in transaction
        local_in_transaction = self._CryoDatabase__in_transaction
        if local_in_transaction:
            # get db connection and begin transaction
            if self._CryoDatabase__is_sqlite():
                self.cursor().execute("BEGIN TRANSACTION")
            else:
                self.connection.begin()
            # Set to being in transaction
            self._CryoDatabase__in_transaction = True
        try:
            # run the function
            return_value = func(*args, **kwargs)
            # if there's no exception, commit
            if "commit_on_complete" in kwargs:
                if kwargs["commit_on_complete"]:
                    self.commit()
            else:
                self.commit()
            # and return from the function
            self._CryoDatabase__in_transaction = local_in_transaction
            return return_value
        # if there's an exception
        except Exception as e:
            # roll back the transaction
            self.connection.rollback()
            self._CryoDatabase__in_transaction = local_in_transaction
            # then re-raise the exception
            raise e
    return self_wrapper

def sql_to_statements(path):

    with open(path, "r") as fh:

        script = fh.read()

        # Compile regex
        pat_statements = re.compile(r'([^;]+?);')
        pat_comments = re.compile(r'--.+\n?')

        # Match statements
        raw_statements = pat_statements.findall(script)
        new_statements = []

        for statement in raw_statements:
            
            new_statements.append(pat_comments.sub("", statement).replace("\n", ""))

        return new_statements
            

def connect(
    # SQLite flags
    path : os.PathLike = None,
    sqlite_create_if_not_found=False,
    # MariaDB flags
    host : str = "localhost",
    user : str =None,
    password : str = None,
    database : str = "cryodb",
    port : int =3306
):
    """connect to a cryodb instance using sqlite3 or MariaDB

    :param path: Path to a sqlite3 database file.
    :type path: os.PathLike or None
    :param sqlite_create_if_not_found: If True, connecting initialises the database at path. If False, a FileNotFoundError is raised.
    :type sqlite_create_if_not_found: bool

    :param host: Hostname for a MariaDB server
    :type host: str
    :param user: Username to use when connecting to the MariaDB server
    :type user: str or None
    :param password: Password to use when connecting to the MariaDB server
    :type password: str or None
    :param database: Name of the database to connect to at the MariaDB server
    :type database: str
    :param port: Port on which to connect to the MariaDB server (defaults to 3306).
    :type port: int

    :raise FileNotFoundError: if the sqlite3 path does not exist and the sqlite_create_if_not_found flag is set to False.

    :return: a CryoDatabase wrapper object
    :rtype: :py:class:CryoDatabase

    """

    # default to SQLite if possible
    if path is not None:

        # Convert path to a pathlib representation
        path = pathlib.Path(path)

        # If the file doesn't exist...
        if not path.exists():
            # we should either crash out because we don't want to over
            # write by default
            if sqlite_create_if_not_found == False: 
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
            raise InvalidDatabaseError(f"Could not find database {database} on host {host}:{port}")

class CryoDatabaseError(Exception):
    """generic exception for CryoDatabase errors
    """
    pass

class InvalidIngestEventError(CryoDatabaseError):
    """raised if the ingest event id is invalid or the ingest event type does not match the ingest method
    """
    pass

class InvalidDatabaseError(CryoDatabaseError):
    """raised if no database is selected, it cannot be found on the host or it does not conform to the cryodb schema
    """
    pass

class InvalidConnectionError(CryoDatabaseError):
    """raised if the connection object in CryoDatabae is invalid
    """
    pass

class NoRecordInsertedError(CryoDatabaseError):
    """raised if not record was inserted during the method call
    """
    pass

class RecordExistsError(CryoDatabaseError):
    """raised if a record with the id already exists
    """
    pass

class InvalidAPIKeyError(CryoDatabaseError):
    """raised if the API key provided is invalid
    """
    pass

class InvalidLingoMOPacketError(CryoDatabaseError):
    """raised if a LingoMO object is invalid
    """
    pass

class NoReceiverFoundError(CryoDatabaseError):
    """raised if there is no receiver found by IMEI number
    """


class IngestType(Enum):
    """represents the different types of events associated with ingesting data to a cryodb database.

    * **LINGOMO** events are for automatic ingest of data in response to an external server input.
    * **SDCARD** events correspond to offline input from SD card files.
    * **LOCAL** events are used for packets received on the local machine, i.e. over a serial link.
    * **MANUAL** events are used to cover scenarios where data is manually added to the database.
    """
    TEST    = 0
    LINGOMO = 1
    SDCARD  = 2
    LOCAL   = 3
    MANUAL  = 4

class APIKeyType(Enum) : 
    ADMIN   = "admin"
    USER    = "user"
    SERVICE = "service"
    IP      = "ip"

class ReceiverType(Enum):
    TRIPOD = "tripod"
    PORTABLE = "portable"

class InstrumentType(Enum):
    """Utility class to describe different instrument types
    """
    Cryoegg     = "cryoegg"
    Cryowurst   = "cryowurst"

@dataclass
class IngestEvent:
    """Dataclass representing row in ingest_event_table
    """
    id              : int
    type            : IngestType
    description     : str
    timestamp       : datetime.datetime


@dataclass
class Receiver:

    id : int
    type : ReceiverType
    name : str
    imei : str
    manufacture_date : datetime.datetime = None
    manufacture_batch : str = None
    commission_date : datetime.datetime = None
    notes : str = None

    def to_dict(self):
        return {
            "id" : f"{self.id:x}",
            "type" : self.type.value,
            "name" : self.name if self.name is not None else "",
            "imei" : self.imei, 
            "manufacture_date" : self.manufacture_date.strftime(CryoDatabase.STRFTIME_FORMAT) if self.manufacture_date is not None else "",
            "commission_date" : self.commission_date.strftime(CryoDatabase.STRFTIME_FORMAT) if self.commission_date is not None else "",
            "manufacture_batch" : self.manufacture_batch,
            "notes" : self.notes
        }

@dataclass
class Instrument:

    id : int
    type : str
    manufacture_date : datetime.datetime = None
    manufacture_batch : str = None
    commission_date : datetime.datetime = None
    notes : str = None
    pressure_keller_min : float = 0.0
    pressure_keller_max : float = 0.0

    def to_dict(self):
        return {
            "id" : f"{self.id:x}",
            "type" : self.type,
            "manufacture_date" : self.manufacture_date.strftime(CryoDatabase.STRFTIME_FORMAT) if self.manufacture_date is not None else "",
            "commission_date" : self.commission_date.strftime(CryoDatabase.STRFTIME_FORMAT) if self.commission_date is not None else "",
            "manufacture_batch" : self.manufacture_batch,
            "pressure_keller_min" : self.pressure_keller_min,
            "pressure_keller_max" : self.pressure_keller_max,
            "notes" : self.notes
        }

class CryoeggInstrument(Instrument):
    def __init__(self, **kwargs):
        super().__init__(type="CRYOEGG", **kwargs)

class CryowurstInstrument(Instrument):
    def __init__(self, **kwargs):
        super().__init__(type="CYROWURST", **kwargs)

class CryoDatabase:
    """interface class to interface with MariaDB or Sqlite databases
    
    :param connection:
    :type connection: ``sqlite3.Connection`` or ``mariadb.Connection``
    """

    STRFTIME_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(
        self, 
        connection : Union[sqlite3.Connection, mariadb.Connection]
    ):

        # Store reference to connection locally
        self.connection = connection

        # Initialise ingest event id
        self.__ingest_event_id = None
        self.__ingest_event_obj = None
        
        # Initialise transaction status
        self.__in_transaction = False

    def __is_sqlite(self):
        return isinstance(self.connection, sqlite3.Connection)

    def __is_mariadb(self):
        return isinstance(self.connection, mariadb.Connection)

    def cursor(self):
        """returns the SQL cursor for the database

        :return: cursor object
        :rtype: ``sqlite3.Cursor`` or ``mariadb.Cursor`` object
        """
        return self.connection.cursor()
    
    def commit(self):
        """commits the current set of transactions to the database
        """
        self.connection.commit()
    
    def disconnect(self):
        """disconnect from the database

        :raise InvalidConnectionError: if the connection instance is invalid
        """
        if isinstance(self.connection,  Union[sqlite3.Connection, mariadb.Connection]):
            self.connection.close()
        else:
            raise InvalidConnectionError;

    def validate(self):
        """checks the database conforms to the ``cryodb`` schema
        
        :return: True, if the database is valid
        :rtype: bool
        :raise InvalidDatabaseError: if there is no database selected, or there is an error in the database schema"""

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

    def add_ingest_event(self, type : Union[str, int, IngestType],  description : str = "", timestamp : Union[NoneType, datetime.datetime] = None) -> int:
        """registers a new ingest event in the database

        :param type: the type of ingest event being registered
        :type type: ``IngestType``
        :param description: a description of the ingest event being registered
        :type description: str
        :param timestamp: the timestamp corresponding to the start of the ingest event
        :type timestamp: ``datetime.datetime``

        :raise ValueError: if type is not a valid IngestType
        :raise NoRecordInsertedError: if no ingest event is created 

        :return: the ingest event ID in `ingest_event_table`
        :rtype: int
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

        try:
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
        except:
            raise NoRecordInsertedError

        # Return last row id
        if cursor.lastrowid > 0:
            self.connection.commit()
        else:
            raise NoRecordInsertedError

        return cursor.lastrowid

    def set_ingest_event(self, id : Union[int, NoneType] = None):
        """sets the default ingest event associated with any ingest actions

        :param id: id of the ingest event to be used as default
        :type id: int
        
        :raise InvalidIngestEventError: if the id is not a valid row in ``ingest_event_table``.
        """
        
        cursor = self.cursor();
        cursor.execute("SELECT COUNT(`ingest_event_id`) FROM `ingest_event_table` WHERE `ingest_event_id` = ?;", (id,))

        if cursor.fetchone()[0] != 1:
            raise InvalidIngestEventError("No ingest event with ingest_event_id:{id}")
        
        self.__ingest_event_id = id

    def get_ingest_event(self, id : int = None):
        """gets a Python object representation of an ingest event

        If the ``id`` parameter is not provided, then the default ingest event for the instance of ``CryoDatabase`` is returned.

        :param id: id of the ingest event
        :type id: int

        :return: ingest event associated with ``id``.
        :rtype: IngestEvent

        :raise ValueError: if the ingest_event_id is not valid 
        """

        # If id is none, select for the current object
        if id == None:
            if self.__ingest_event_id == None:
                raise ValueError("No ingest_event_id provided and no default ingest_event_id set.")
            id = self.__ingest_event_id

        if self.__ingest_event_obj is not None and self.__ingest_event_id == id:
            return self.__ingest_event_obj
        else:
            # Request ingest_event information 
            cursor = self.cursor()
            cursor.execute("SELECT `ingest_event_id`, `ingest_type`, `description`, `timestamp` FROM `ingest_event_table` WHERE `ingest_event_id` = ?;", (id,))

            results = cursor.fetchall()

            if len(results) != 1:
                raise ValueError("Cannot get IngestEvent object for ingest_event_id:{id}")
            
            ingest_event_obj = IngestEvent(
                id=results[0][0],
                type=IngestType.__members__[results[0][1]],
                description=results[0][2],
                timestamp=datetime.datetime.strptime(results[0][3], CryoDatabase.STRFTIME_FORMAT)
            )

            if self.__ingest_event_id == id:
                self.__ingest_event_obj = ingest_event_obj

            return ingest_event_obj

    @sql_transaction
    def ingest_lingomo(self, json_obj : str, ingest_event : Union[IngestEvent, int]):
        """
        accepts a JSON LingoMO object and ingests
        1. takes json, parses into LingoMO packet

        2. In ingest_table: create new ingest_id, assign to current ingest_event_id, assign raw json

        3. Using ingest_id, create new row in `ingest_lingomo_table` with metadata from LingoMO packet

        4. Get SDPackets from bytes in LingoMO payload/message:

            4a. for each packet, get receiver packet and instrument/data packet
            4b. insert receiver data into `receiver_data_table`
            4c. select correct table from instrument packet (either cryoegg/cryowurst_data_table) and insert data

        :raise json.decoder.JSONDecodeError: raised if there is an error decoding the LingoMO packet.
        """
    
        # Try decoding
        lingomo_packet = json.loads(json_obj)

        #TODO: Perform some validation on the LingoMO object
        if not "id" in lingomo_packet or not "receivedAt" in lingomo_packet:
            raise InvalidLingoMOPacketError("Invalid LingoMO packet.")

        # Now we can interrogate the ingest event
        if isinstance(ingest_event, int):
            ingest_event = self.get_ingest_event(ingest_event)

        # And check that the event is valid 
        if ingest_event.type != IngestType.LINGOMO: 
            raise ValueError("Invalid ingest event - check LingoMO ingest event type")
    
        # Begin transaction
        cursor = self.cursor()

        ### STEP 2 - Create new ingest row in ingest_table
        cursor.execute(
            "INSERT INTO `ingest_table` (`ingest_event_id`, `raw`) VALUES (?,?);",
            (ingest_event.id, json_obj)
        )

        # Get ingest_id
        ingest_id = cursor.lastrowid
        # and if its less than 1, we haven't inserted a record correctly
        if ingest_id < 1:
            raise NoRecordInsertedError
        
        ### STEP 3 - Create new row in LingoMO metadata table
        imei = None

        try:

            # Create receivedAt timestamp
            received_at = datetime.datetime(
                lingomo_packet["receivedAt"]["year"],
                lingomo_packet["receivedAt"]["month"],
                lingomo_packet["receivedAt"]["day"],
                lingomo_packet["receivedAt"]["hour"],
                lingomo_packet["receivedAt"]["minute"],
                lingomo_packet["receivedAt"]["second"]
            )

            # Get IMEI from LingoMO packet
            imei = lingomo_packet["identity"]["hardware"]["imei"]

            cursor.execute(
                "INSERT INTO `ingest_lingomo_table` (`ingest_id`, `lingomo_id`, `received_timestamp`, `imei`, `serial`, `momsn`, `latitude`, `longitude`, `accuracy`) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    ingest_id, 
                    lingomo_packet["id"],
                    received_at,
                    imei,
                    lingomo_packet["identity"]["hardware"]["serial"],
                    lingomo_packet["sbd"]["momsn"],
                    lingomo_packet["sbd"]["location"]["latitude"],
                    lingomo_packet["sbd"]["location"]["longitude"],
                    lingomo_packet["sbd"]["location"]["cep"]
                )
            )

        except KeyError as e: 
            raise InvalidLingoMOPacketError("Invalid LingoMO packet.")
        
        if cursor.lastrowid != ingest_id:
            raise NoRecordInsertedError("Failed to insert ingest_lingomo row.")
        
        ### STEP 4

        # Ideally we would encode the receiver_id in the transmitted packet to
        # avoid any ambiguity but instead we'll have to make do with having 
        # a record of the IMEI/Serial number for each receiver
        if imei == None:
            receiver_id = None
        else:
            cursor.execute("SELECT `receiver_id` FROM `receiver_table` WHERE `imei_number` = ? LIMIT 1;", (imei,))

            if cursor.rowcount == 0:
                receiver_id = None
            else:
                receiver_id = cursor.fetchone()[0]

        if receiver_id == None:
            #TODO: we should log that there is no receiver found here
            raise NoReceiverFoundError()
    
        # 4a. for each packet, get receiver packet and instrument/data packet
        #     4b. insert receiver data into `receiver_data_table`
        #     4c. select correct table from instrument packet (either cryoegg/cryowurst_data_table) and insert data
        payload = base64.b64decode(lingomo_packet["message"])

        # Convert payload to SDPackets
        packets = [cryodecoder.SDPacket(p) for p in cryodecoder.bytes_to_packets(payload)]

        # Iterate over packets found in the payload
        for packet in packets:
            self.ingest_sdpacket(packet, receiver_id, ingest_event.id, ingest_id, commit_on_complete=False)

        return ingest_id

    @sql_transaction
    def ingest_sdcard(
        self, 
        path, 
        receiver_id : int,
        ingest_event : Union[IngestEvent, int, NoneType] = None 
    ):
        """

        1. create ingest event with path and description in `ingest_event_table` and store event id

        2. open file at path and for each SDPacket:

            2a. create new `ingest_id` in `ingest_table`, assign hex-coded raw data to raw
            2b. get receiver packet and instrument/data packet
            2c. insert receiver data into `receiver_data_table`
            2d. select correct table from instrument packet (either cryoegg/cryowurst_data_table) and insert data
        """

        if ingest_event == None:
            # If no ingest event is provided, then we will create a new one
            event_id = self.add_ingest_event(
                type        = IngestType.SDCARD,
                description = str(path),
                # Don't pass timestamp so we use the current time
            )
            # get the ingest_event
            ingest_event = self.get_ingest_event(event_id)
        elif isinstance(ingest_event, IngestEvent):
            # Validate the IngestEvent object
            ingest_event = self.get_ingest_event(ingest_event.id)
        elif isinstance(ingest_event, int):
            # Validate the ingest event id
            ingest_event = self.get_ingest_event(ingest_event)
        else:
            # otherwise, get the current ingest event
            ingest_event = self.get_ingest_event()

        # Check that we are using an SD card ingest event
        if ingest_event.type != IngestType.SDCARD:
            raise InvalidIngestEventError("The ingest event #{event_id} type is not SDCARD")

        # Open SD file in binary mode
        with open(path, "rb") as fh_sdcard:

            # Convert bytes to packets
            packets = cryodecoder.bytes_to_packets(fh_sdcard.read())

            # Iterate over packets
            for packet in packets:
                self.__ingest_sdpacket_novalidation(
                    packet, 
                    event_id, 
                    receiver_id = receiver_id, 
                    commit_on_complete=False
                )

            # Commit all changes
            self.commit()

    @sql_transaction
    def __ingest_sdpacket_novalidation(
        self, 
        packet, 
        receiver_id : int, 
        ingest_event : IngestEvent,
        ingest_id : int = None, 
        commit_on_complete=True
    ):
        
        # Get database cursor
        cursor = self.cursor()

        # Create an ingest id
        if ingest_id == None:
            cursor.execute(
                "INSERT INTO `ingest_table` (`ingest_event_id`, `raw`) VALUES (?,?);", (ingest_event.id, packet.get_raw())
            )
            # TODO: replace raw value so that we store hex not raw bytes?

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
                receiver_id = receiver_id, 
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

    @sql_transaction
    def ingest_sdpacket(
        self, 
        packet : cryodecoder.SDPacket, 
        receiver_id : int, 
        ingest_event : Union[IngestEvent, int, NoneType] = None, 
        ingest_id : int = None,
        commit_on_complete=True
    ):
        """ingest a single SDPcaket (i.e. W1/W2/C0/C1 etc) style packet

        1. create new `ingest_id` in `ingest_table`, assign hex-coded raw data to raw
        2. get receiver packet and instrument/data packet
        3. insert receiver data into `receiver_data_table`
        4. select correct table from instrument packet (either cryoegg/cryowurst_data_table) and insert data
        """

        if isinstance(ingest_event, IngestEvent):
            # Validate the IngestEvent object
            ingest_event = self.get_ingest_event(ingest_event.id)
        elif isinstance(ingest_event, int):
            # Validate the ingest event id
            ingest_event = self.get_ingest_event(ingest_event)
        else:
            # otherwise, get the current ingest event
            ingest_event = self.get_ingest_event()

        # Check that we are using an SD card or LignoMO ingest event
        if ingest_event.type not in (IngestType.SDCARD, IngestType.LINGOMO):
            raise InvalidIngestEventError("The ingest event #{event_id} type is not SDCARD or LINGOMO")

        self.__ingest_sdpacket_novalidation(
            packet,
            receiver_id,
            ingest_event,
            ingest_id,
            commit_on_complete
        )


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
            "INSERT INTO `receiver_data_table` (`receiver_id`, `ingest_id`, `timestamp`, `channel`, `temperature_logger`, `pressure_logger`, `voltage_logger`) VALUES (?,?,?,?,?,?,?);",
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
                packet.instrument_id,
                packet.conductivity_raw,
                packet.temperature_pt1000_raw,
                packet.pressure_raw,
                packet.temperature_raw,
                packet.battery_voltage,
                packet.sequence_number,
                packet.rssi,
                packet.packet_type
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

    @sql_transaction
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
        receiver_id : Union[str, int, NoneType] = None,
        receiver_type : Union[str, ReceiverType, NoneType] = None,
        receiver_name : Union[str, NoneType] = None,
        imei_number : Union[str, int, NoneType] = None,
        manufacture_date : Union[datetime.datetime, NoneType] = None,
        manufacture_batch : Union[str, NoneType] = None,
        commission_date : Union[datetime.datetime, NoneType] = None,
        notes : Union[str, NoneType] = None
    ):
        """Adds a new receiver to the database
        """

        # Validate and convert the instrument ID
        if isinstance(receiver_id, str):
            try:
                receiver_id = int(receiver_id, 16)
            except ValueError:
                raise ValueError("String-like receiver_id should be in hexadecimal format.")
        elif isinstance(receiver_id, int) and receiver_id > 0:
            raise ValueError("receiver_id should be > 0")
        
        if isinstance(receiver_type, ReceiverType):
            receiver_type = receiver_type.value
        
        if not isinstance(receiver_type, str):
            raise ValueError("Invalid receiver_type")

        cursor = self.cursor()
        # Insert values
        try: 
            cursor.execute("INSERT INTO `receiver_table` (`receiver_id`, `name`, `type`, `imei_number`, `manufacture_date`, `manufacture_batch`, `commission_date`, `notes`) VALUES (?,?,?,?,?,?,?,?)", 
            (
                receiver_id,
                receiver_type,
                receiver_name,
                imei_number,
                manufacture_date.strftime(CryoDatabase.STRFTIME_FORMAT) if manufacture_date is not None else None,
                manufacture_batch,
                commission_date.strftime(CryoDatabase.STRFTIME_FORMAT) if commission_date is not None else None,
                notes
            ))
        except (mariadb.IntegrityError, sqlite3.IntegrityError) as e:
            self.connection.rollback()
            raise NoRecordInsertedError()

        # Commit new instrument to database
        self.commit()

        if cursor.lastrowid == -1:
            raise NoRecordInsertedError;

        # Return instrument_id
        return cursor.lastrowid
    
    def get_receiver(self, receiver_id):
        pass

    def get_receivers(self, id : Union[int, str, Iterable[int], Iterable[str]] = None):
        
        cursor = self.cursor()

        # tidy up id argument
        if id is None:
            # Request from database
            cursor.execute("SELECT * FROM `receiver_table`;")
        else:
            # Convert to list if a single argument
            if isinstance(id, (int, str)):
                id = list(id)
            
            parameter_string = ("?," * len(id))[0:-1] 
            parameters = id
            cursor.execute(f"SELECT * FROM `receiver_table` WHERE `receiver_id` IN ({parameter_string});", parameters)

        # Iterate through results
        receivers = []

        for row in cursor.fetchall():
            receivers.append(Receiver(
                id = row[0],
                type = ReceiverType(row[2]),
                name = row[1] if isinstance(row[1], str) else "",
                imei = row[3] if isinstance(row[3], str) else "",
                manufacture_date = datetime.datetime.strptime(row[4], CryoDatabase.STRFTIME_FORMAT) if row[4] is not None else None,
                manufacture_batch = row[5],
                commission_date = datetime.datetime.strptime(row[6], CryoDatabase.STRFTIME_FORMAT) if row[6] is not None else None,
                notes = row[7]
            ))

        return receivers
    
    def get_instruments(self, id : Union[int, str, Iterable[int], Iterable[str]] = None, type : InstrumentType = None):
        
        # Get DB cursor
        cursor = self.cursor()
        
        # If no ID is provided, then select all
        if id == None:
            if type == None:
                cursor.execute("SELECT * FROM `instrument_table`;")
            else:
                cursor.execute("SELECT * FROM `instrument_table` WHERE `type`=?;", (type.value,))

        else:
            # Tidy up ID list
            if isinstance(id, (str, int)):
                id = list(id)
                
            # Query string
            # create a string of ?s separated by commas for each id 
            parameter_string = ("?," * len(id))[0:-1] 
            parameters = id

            if type == None:
                cursor.execute(f"SELECT * FROM `instrument_table` WHERE `instrument_id` IN ({parameter_string});", parameters)
            else:
                parameters.append(type)
                cursor.execute(f"SELECT * FROM `instrument_table` WHERE `instrument_id` IN ({parameter_string}) AND `type` = ?;", parameters)

        # Process response
        instruments = []
        for row in cursor.fetchall():
            instruments.append(CryoDatabase.instrument_from_row(row))
        
        return instruments

    
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
            start_timestamp.strftime(CryoDatabase.STRFTIME_FORMAT) if start_timestamp is not None else None,
            end_timestamp.strftime(CryoDatabase.STRFTIME_FORMAT) if end_timestamp is not None else None
        ))

        # Commit new instrument to database
        self.commit()

        if cursor.lastrowid == -1:
            raise NoRecordInsertedError;

        # Return instrument_id
        return cursor.lastrowid
        
    def add_instrument_deployment(
        self,
        start_timestamp : datetime.datetime,
        end_timestamp : datetime.datetime = None,
        campaign_id : int = None,
        instrument_id : int = None,
        description : str = None
    ):
        
        cursor = self.cursor()
        try:
            cursor.execute("INSERT INTO `instrument_deployment_table` (`description`, `campaign_id`, `instrument_id`, `start_timestamp`, `end_timestamp`) VALUES (?,?,?,?,?);",
                (description,
                campaign_id,
                instrument_id,
                start_timestamp.strftime(CryoDatabase.STRFTIME_FORMAT) if start_timestamp is not None else None,
                end_timestamp.strftime(CryoDatabase.STRFTIME_FORMAT) if end_timestamp is not None else None
                )
            )
        except (mariadb.IntegrityError, sqlite3.IntegrityError) as e:
            raise NoRecordInsertedError
        
        self.commit()

        if cursor.lastrowid == -1:
            raise NoRecordInsertedError;

        # Return instrument_id
        return cursor.lastrowid
    
    def update_instrument_deployment(
        self,
        deployment_id : int,
        start_timestamp : datetime.datetime = None,
        end_timestamp : datetime.datetime = None,
        campaign_id : int = None,
        instrument_id : int = None,
        description : str = None
    ):
        
        cursor = self.cursor()

        # Set parameter list
        parameters = list()
        query_string = list()

        for key, value in {
            "start_timestamp"   : start_timestamp,
            "end_timestamp"     : end_timestamp,
            "campaign_id"       : campaign_id,
            "instrument_id"     : instrument_id,
            "description"       : description
        }.items():
            if value is not None:
                query_string.append(f"`{key}` = ?")
                if "_timestamp" in key:
                    parameters.append(value.strftime(CryoDatabase.STRFTIME_FORMAT))

        if len(query_string) > 0:

            # Add deployment id to parameters
            parameters.append(deployment_id)

            try:
                query = f"UPDATE `instrument_deployment_table` SET {",".join(query_string)} WHERE `deployment_id` = ?;"
                cursor.execute(query, parameters)
            except (mariadb.IntegrityError, sqlite3.IntegrityError) as e:
                raise NoRecordInsertedError
            
            self.commit()

            if cursor.lastrowid == -1:
                raise NoRecordInsertedError;

            # Return instrument_id
            return cursor.lastrowid
        
        else:
            return deployment_id
        
    def add_receiver_deployment(
        self,
        start_timestamp : datetime.datetime,
        end_timestamp : datetime.datetime = None,
        campaign_id : int = None,
        receiver_id : int = None,
        description : str = None,
        firmware_version : Union[str, NoneType] = None,
        antenna_type : str = None,
        service_timestamp : datetime.datetime = None,
        original_latitude : Union[int, float] = None,
        original_longitude : Union[int, float] = None,
        original_elevation : Union[int, float] = None,
        latest_latitude : Union[int, float] = None,
        latest_longitude : Union[int, float] = None,
        latest_elevation : Union[int, float] = None,
    ):
        
        # Validate latitude and longitude
        if (original_latitude is None) ^ (original_longitude is None):
            raise ValueError("Both original_latitude and original_longitude must be provided.")
        
        if (latest_latitude is None) ^ (latest_longitude is None):
            raise ValueError("Both latest_latitude and latest_longitude must be provided.")
        
        if latest_longitude is None and original_longitude is not None:
            latest_longitude = original_longitude
        
        if latest_latitude is None and original_latitude is not None:
            latest_latitude = original_latitude

        # Validate elevation
        if latest_elevation is None and original_elevation is not None:
            latest_elevation = original_elevation
        
        cursor = self.cursor()
        try:
            cursor.execute("INSERT INTO `receiver_deployment_table` (`description`, `campaign_id`, `receiver_id`, `firmware_version`, `antenna_type`, `start_timestamp`, `end_timestamp`, `service_timestamp`, `original_latitude`, `original_longitude`, `original_elevation`, `latest_latitude`, `latest_longitude`, `latest_elevation`) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?);",
            (
                description,
                campaign_id,
                receiver_id,
                firmware_version,
                antenna_type,
                start_timestamp.strftime(CryoDatabase.STRFTIME_FORMAT) if start_timestamp is not None else None,
                end_timestamp.strftime(CryoDatabase.STRFTIME_FORMAT) if end_timestamp is not None else None,
                service_timestamp.strftime(CryoDatabase.STRFTIME_FORMAT) if service_timestamp is not None else None,
                original_latitude,
                original_longitude,
                original_elevation,
                latest_latitude,
                latest_longitude,
                latest_elevation
            ))
        except (mariadb.IntegrityError, sqlite3.IntegrityError) as e:
            raise NoRecordInsertedError
        
        self.commit()

        if cursor.lastrowid == -1:
            raise NoRecordInsertedError;

        # Return instrument_id
        return cursor.lastrowid
    
    def update_receiver_deployment(
        self,
        deployment_id : int,
        firmware_version : Union[str, NoneType] = None,
        start_timestamp : datetime.datetime = None,
        end_timestamp : datetime.datetime = None,
        campaign_id : int = None,
        receiver_id : int = None,
        description : str = None,
        antenna_type : str = None,
        service_timestamp : datetime.datetime = None,
        latest_latitude : Union[int, float] = None,
        latest_longitude : Union[int, float] = None,
        latest_elevation : Union[int, float] = None,
    ):
        
        cursor = self.cursor()

        # Set parameter list
        parameters = list()
        query_string = list()

        for key, value in {
            "firmware_version" : firmware_version,
            "start_timestamp" : start_timestamp,
            "end_timestamp" : end_timestamp,
            "campaign_id" : campaign_id,
            "receiver_id" : receiver_id,
            "description" : description,
            "antenna_type" : antenna_type,
            "service_timestamp" : service_timestamp,
            "latest_latitude" : latest_latitude,
            "latest_longitude" : latest_longitude,
            "latest_elevation" : latest_elevation,
        }.items():
            if value is not None:
                query_string.append(f"`{key}` = ?")
                if "_timestamp" in key:
                    parameters.append(value.strftime(CryoDatabase.STRFTIME_FORMAT))

        if len(query_string) > 0:

            # Add deployment id to parameters
            parameters.append(deployment_id)

            try:
                cursor.execute(f"UPDATE `receiver_deployment_table` SET {",".join(query_string)} WHERE `deployment_id` = ?;", parameters
                )
            except (mariadb.IntegrityError, sqlite3.IntegrityError) as e:
                raise NoRecordInsertedError
            
            self.commit()

            if cursor.lastrowid == -1:
                raise NoRecordInsertedError;

            # Return instrument_id
            return cursor.lastrowid
        
        else:
            return deployment_id
        
    def add_api_key(
        self, 
        name : str, 
        type : APIKeyType, 
        email : str,
        campaigns : Union[int, Iterable[int]] = None, 
        can_select : bool = False, 
        can_update : bool = False, 
        can_insert : bool = False,
        ip : Union[str, ipaddress.IPv4Address] = None
    ):
        
        if self.__is_sqlite():
            raise TypeError("Cannot create API keys for Sqlite database.")
        
        # Check that we have a valid API key name
        if len(name) < 1:
            raise ValueError("Cannot create API key with empty string.")

        cursor = self.cursor()
            
        global_can_select = False
        global_can_update = False
        global_can_insert = False
            
        if type == APIKeyType.IP:

            # Convert IP address to IPv4 class
            if isinstance(ip, str):
                ip = ipaddress.ip_address(ip)
            
            if ip == None or not isinstance(ip, (ipaddress.IPv4Address)):
                raise ValueError("IP address cannot be empty and should be an IPv4 address")
            
            # Assign global properties for IP keys
            global_can_insert = can_insert
            global_can_update = can_update
            global_can_select = can_select

            key = str(ip)
        
            cursor.execute(
                "INSERT INTO `api_keys` (`name`,`type`,`email`,`ip`,`created`,`last_accessed`, `can_select`, `can_insert`, `can_update`) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    name,
                    type.name,
                    email if email is not None else "",
                    str(ip),
                    datetime.datetime.now(tz=datetime.timezone.utc).strftime(CryoDatabase.STRFTIME_FORMAT),
                    datetime.datetime.now(tz=datetime.timezone.utc).strftime(CryoDatabase.STRFTIME_FORMAT),
                    global_can_select,
                    global_can_insert,
                    global_can_update
                )
            )

        else:

            # Check we have a local salt available in the environment variables
            if not "CRYODB_SALT" in os.environ:
                raise KeyError("Cannot find CRYODB_SALT key in environment variables - check server configuration")

            # Generate random SHA256 digest
            hashgen = hashlib.new("sha256")
            hashgen.update(secrets.SystemRandom().randbytes(256))
            # This is the user private key
            key = hashgen.hexdigest()

            if type == APIKeyType.ADMIN:
                # Assign global properties for admin keys
                global_can_insert = True
                global_can_update = True
                global_can_select = True
            
            cursor.execute(
                "INSERT INTO `api_keys` (`name`, `type`, `hash`, `email`, `created`, `last_accessed`, `can_select`, `can_insert`, `can_update`) VALUES (?,?,SHA2(CONCAT(?,?),256),?,?,?,?,?,?)",
                (
                    name,
                    type.name,
                    key, 
                    os.environ["CRYODB_SALT"], # SQL concats these
                    email if email is not None else "",
                    datetime.datetime.now(tz=datetime.timezone.utc).strftime(CryoDatabase.STRFTIME_FORMAT),
                    datetime.datetime.now(tz=datetime.timezone.utc).strftime(CryoDatabase.STRFTIME_FORMAT),
                    global_can_select,
                    global_can_insert,
                    global_can_update
                )
            )

        if cursor.lastrowid == -1:
            raise NoRecordInsertedError
        
        # Key api_key id
        key_id = cursor.lastrowid

        if type == APIKeyType.SERVICE or type == APIKeyType.USER:

            try:
                # Convert single integer to list
                if isinstance(campaigns, int):
                    campaigns = [campaigns,]

                for campaign in campaigns:

                    cursor.execute(
                        "INSERT INTO `api_key_permissions` (`key_id`, `can_select`, `can_insert`, `can_update`, `campaign_id`) VALUES (?,?,?,?,?)",
                        (
                            key_id,
                            1 if can_select else 0,
                            1 if can_insert else 0,
                            1 if can_update else 0,
                            campaign 
                        )
                    )
            except mariadb.IntegrityError as e:
                
                cursor.execute("DELETE FROM `api_keys` WHERE `key_id` = ?", (key_id,))
                cursor.execute("DELETE FROM `api_key_permissions` WHERE `key_id` = ?", (key_id,))
                raise NoRecordInsertedError

        self.commit()
                
        return key
    
    def update_api_key(
        self,
        key,
        campaign_id : int = None, 
        can_select : bool = None, 
        can_update : bool = None, 
        can_insert : bool = None
    ):

        cursor = self.cursor()

        # Define set string
        if can_select is None and can_update is None and can_insert is None:
            cryodb_logger.warning("No permissions changed.")
            return
        
        set_fields = {
            "can_select" : can_select,
            "can_update" : can_update,
            "can_insert" : can_insert 
        }
        set_string = []
        for field, value in set_fields.items():

            if value is None or not isinstance(value, bool):
                continue

            set_string.append(f"`{field}` = {1 if value else 0}")

        if len(set_string) == 0:
            raise ValueError("Invalid update arguments (can_select, can_update, can_insert must be bool)")

        set_string = ",".join(set_string)

        query_string = f"UPDATE `api_key_permissions` SET {set_string} WHERE `key_id` = (SELECT `key_id` FROM `api_keys` WHERE `hash` = SHA2(CONCAT(?,?),256) LIMIT 1) AND `campaign_id` = ?;"

        print(query_string)
            
        cursor.execute(
            query_string,
            (
                key, os.environ["CRYODB_SALT"], campaign_id
            )
        )

        self.commit()

    def get_api_permissions(self, key=None, ip=None):

        cursor = self.cursor()
        
        # If we have a provided, check this
        if key != None:
            cursor.execute(
                "SELECT `key_id`, `type`, `can_select`, `can_insert`, `can_update` FROM `api_keys` WHERE `hash` = SHA2(CONCAT(?,?),256) LIMIT 1", 
                (
                    key, os.environ["CRYODB_SALT"]
                )
            )

        # otherwise lookup the IP address
        elif ip != None:
            cursor.execute(
                "SELECT `key_id`, `type`, `can_select`, `can_insert`, `can_update` FROM `api_keys` WHERE `ip` = ? AND `type` = 'IP' LIMIT 1",
                (ip,)
            )

        # if neither a key or IP address were pas
        else:
            raise ValueError("Require API key or IP address to get api permissions.")
        
        # Get API key type
        key_result = cursor.fetchone()
        
        if key_result is None:
            return None, None
        
        key_id, type, global_select, global_insert, global_update = key_result
        # Convert type to API key type 
        type = APIKeyType(type.lower())

        # Get all instrument, receiver and campaign id's
        cursor.execute("SELECT `instrument_id` FROM `instrument_table`;")
        instrument_ids = [x[0] for x in cursor.fetchall()]
        cursor.execute("SELECT `receiver_id` FROM `receiver_table`;")
        receiver_ids = [x[0] for x in cursor.fetchall()]
        cursor.execute("SELECT `campaign_id` FROM `campaign_table`;")
        campaign_ids = [x[0] for x in cursor.fetchall()]

        permissions = {
            "campaigns" : { 
                "select" : [],
                "update" : [],
                "insert" : []
            },
            "receivers" : { 
                "select" : [],
                "update" : [],
                "insert" : []
            },
            "instruments" : { 
                "select" : [],
                "update" : [],
                "insert" : []
            }
        }

        # Apply global permissions
        for category, ids in {"campaigns" : campaign_ids, "receivers" : receiver_ids, "instruments" : instrument_ids}.items():
            
            if global_select:
                permissions[category]["select"] = ids
            if global_update:
                permissions[category]["update"] = ids
            if global_insert:
                permissions[category]["insert"] = ids

        
        # Get instrument permissions
        cursor.execute("SELECT DISTINCT `instrument_id`, `can_select`, `can_update`, `can_insert` FROM `instrument_deployment_table` INNER JOIN `api_key_permissions` USING(`campaign_id`) WHERE `key_id` = ? GROUP BY `instrument_id`;", (key_id,))

        for id, select, update, insert in cursor.fetchall():
            if select and not id in permissions["instruments"]["select"]:
                permissions["instruments"]["select"].append(id)
            if update and not id in permissions["instruments"]["update"]:
                permissions["instruments"]["update"].append(id)
            if insert and not id in permissions["instruments"]["insert"]:
                permissions["instruments"]["insert"].append(id)

        cursor.execute("SELECT DISTINCT `receiver_id`, `can_select`, `can_update`, `can_insert` FROM `receiver_deployment_table` INNER JOIN `api_key_permissions` USING(`campaign_id`) WHERE `key_id` = ? GROUP BY `receiver_id`;", (key_id,))

        for id, select, update, insert in cursor.fetchall():
            if select and not id in permissions["receivers"]["select"]:
                permissions["receivers"]["select"].append(id)
            if update and not id in permissions["receivers"]["update"]:
                permissions["receivers"]["update"].append(id)
            if insert and not id in permissions["receivers"]["insert"]:
                permissions["receivers"]["insert"].append(id)

        cursor.execute("SELECT `campaign_id`, `can_select`, `can_insert`, `can_insert` FROM `api_key_permissions` WHERE `key_id` = ? GROUP BY `campaign_id`;", (key_id,))

        for id, select, update, insert in cursor.fetchall():
            if select and not id in permissions["campaigns"]["select"]:
                permissions["campaigns"]["select"].append(id)
            if update and not id in permissions["campaigns"]["update"]:
                permissions["campaigns"]["update"].append(id)
            if insert and not id in permissions["campaigns"]["insert"]:
                permissions["campaigns"]["insert"].append(id)

        return type, permissions
        
    @staticmethod
    def initialise_sqlite3(path : Union[str, pathlib.Path]):

        # Log
        cryodb_logger.debug("Initialising sqlite3 database")

        if isinstance(path, str):
            path = pathlib.Path(path)

        # Check whether the DB already exists
        if path.exists():
            raise FileExistsError(f"Path {path} already exists!")
        
        # Open connection to database
        db_object = sqlite3.connect(path)

        # Iterate through resources in order and execute
        setup_scripts = (
            "init_schema.sql", 
            "init_metadata.sql"
        )
        
        # Get path to scripts from module
        init_scripts = importlib.resources.files("cryodb.resources.sql.init")
        for script in setup_scripts:

            with open(init_scripts/script, "r") as sql_file:

                cryodb_logger.info(f"Running {script} on {path}")

                script = sql_file.read()
                # We need to modify and remove any instance of AUTO_INCREMENT
                script = script.replace("AUTO_INCREMENT","")
                script = script.replace("INTEGER UNSIGNED NOT NULL PRIMARY KEY", "INTEGER NOT NULL PRIMARY KEY")
                script = script.replace("TINYINT","INTEGER")
                
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
    
    @staticmethod
    def instrument_from_row(row):

        # Assume we have a full row
        if row[1] == InstrumentType.Cryoegg.value:
            class_type = CryoeggInstrument
        elif row[1] == InstrumentType.Cryowurst.value:
            class_type = CryowurstInstrument
        
        # Perform constructor
        return class_type(
            id = row[0],
            manufacture_date = datetime.datetime.strptime(row[2], CryoDatabase.STRFTIME_FORMAT),
            manufacture_batch = row[3],
            commission_date = datetime.datetime.strptime(row[4], CryoDatabase.STRFTIME_FORMAT),
            notes = row[5],
            pressure_keller_min = row[6],
            pressure_keller_max = row[7]
        )