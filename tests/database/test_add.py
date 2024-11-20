import cryodb

# Libraries for import required for testing
import datetime 
import mariadb
import os
import pathlib
import pytest

# import common test parameters
from .config import *

def __test_add_instrument(db : cryodb.CryoDatabase):
    
    instrument_id_hex = "aa123456"
    instrument_id_dec = int(instrument_id_hex, 16)

    cursor = db.cursor()
    # Purge database in advance of add
    cursor.execute("DELETE FROM `instrument_table` WHERE `instrument_id` = ?", (instrument_id_dec,))

    db.commit()
    
    instrument_id = db.add_instrument(
        instrument_id="aa123456",
        type=cryodb.InstrumentType.Cryoegg,
        pressure_keller_max=30.0
    )

    # Validate it exists in the database
    cursor.execute("SELECT * FROM `instrument_table` WHERE `instrument_id` = ?;", (instrument_id,))

    assert len(cursor.fetchall()) == 1

    with pytest.raises(cryodb.RecordExistsError):
        instrument_id = db.add_instrument(
            instrument_id="aa123456",
            type=cryodb.InstrumentType.Cryoegg,
            pressure_keller_max=30.0
        )

    cursor.execute("DELETE FROM `instrument_table` WHERE `instrument_id` = ?", (instrument_id,))

    db.commit()

    cursor.execute("SELECT * FROM `instrument_table` WHERE `instrument_id` = ?;", (instrument_id,))

    assert len(cursor.fetchall()) == 0

def test_add_instrument(db_mariadb, db_sqlite):

    __test_add_instrument(db_mariadb)
    __test_add_instrument(db_sqlite)

def test_add_receiver(db_mariadb, db_sqlite):
    
    __test_add_receiver(db_mariadb)
    __test_add_receiver(db_sqlite)

def test_add_campaign():
    pass