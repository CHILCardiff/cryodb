import cryodb

# Libraries for import required for testing
import datetime 
import mariadb
import os
import pathlib
import pytest

# import common test parameters
from .config import *

@pytest.mark.parametrize("db", ("db_mariadb", "db_sqlite"))
def test_add_ingest_event(db, request):

    db = request.getfixturevalue(db)

    # Log all ingest events created, to remvoe them afterwards
    ingest_event_ids = []

    # Create a new ingest event
    ingest_event_ids.append(db.add_ingest_event(
        description = "An ingest event for testing purposes",
        type = cryodb.IngestType.TEST,
        timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
    ))

    # check inserted id
    assert len(ingest_event_ids) == 1
    assert isinstance(ingest_event_ids[0], int)
    assert ingest_event_ids[0] > 0

    # check we can read it from the database
    cursor = db.cursor()
    cursor.execute("SELECT * FROM `ingest_event_table` WHERE `ingest_event_id` = (?)", (ingest_event_ids[0],));

    # check we have returned one row
    assert len(cursor.fetchall()) == 1

    # test ingest event without datetime
    ingest_event_ids.append(db.add_ingest_event(
        description = "An ingest event for testing purposes",
        type = cryodb.IngestType.TEST,
    ))

    # check inserted id
    assert len(ingest_event_ids) == 2
    assert isinstance(ingest_event_ids[-1], int)
    assert ingest_event_ids[-1] > 0

    cursor.execute("SELECT `ingest_event_id`, `timestamp` FROM `ingest_event_table` WHERE `ingest_event_id` = (?);", (ingest_event_ids[0],));

    # check timestamp
    row = cursor.fetchone()

    # try calling ingest event without type
    with pytest.raises(Exception):

        ingest_event_ids.append(db.add_ingest_event(
            description = "An invalid ingest event call",
        ))

    # Try setting ingest event
    db.set_ingest_event(ingest_event_ids[0]);

    with pytest.raises(cryodb.InvalidIngestEventError):
        db.set_ingest_event(-1)

    # Cleanup
    cursor.execute(f"DELETE FROM `ingest_event_table` WHERE `ingest_event_id` IN ({("?,"*len(ingest_event_ids))[0:-1]});", ingest_event_ids)
    db.commit()

@pytest.mark.parametrize("db", ("db_mariadb", "db_sqlite"))
def test_get_ingest_event(db, request):

    db = request.getfixturevalue(db)

    event_id = db.add_ingest_event(
        type = cryodb.IngestType.TEST,
        description = "Ingest event to test getting Python representative row",
    )

    db.set_ingest_event(event_id)

    # Get Python object
    obj = db.get_ingest_event()

    assert isinstance(obj, cryodb.IngestEvent)
    assert isinstance(obj.type, cryodb.IngestType)
    assert obj.id == event_id

    # Cleanup
    db.cursor().execute(f"DELETE FROM `ingest_event_table` WHERE `ingest_event_id` = ?;", (event_id,))
    db.commit()
