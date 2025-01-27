from .config import *
import pytest
import json
 
@pytest.mark.parametrize("db", ("db_mariadb", "db_sqlite"))
def test_sql_transaction(db, request):
    
    db = request.getfixturevalue(db)

    # Use ingest_lingomo

    # Get packet
    with open("tests/lingomo_packet.json", "r") as fh:
        packet = json.load(fh)

    def get_ingest_ids():

        # Get all ingest rows
        cursor = db.cursor()
        cursor.execute("SELECT `ingest_id` FROM `ingest_table` ORDER BY `ingest_id`")

        return set([x[0] for x in cursor.fetchall()])

    ingest_begin = get_ingest_ids()

    # Try inerting with invalid ingest event
    invalid_ingest_id = 999
    with pytest.raises(ValueError):
        db.ingest_lingomo(json.dumps(packet), invalid_ingest_id)

    # Create ingest event
    ingest_event_id = db.add_ingest_event(cryodb.IngestType.LINGOMO, description="test")

    # Remove to invalidate packet
    old_id = packet["identity"]
    del packet["identity"]

    with pytest.raises(cryodb.InvalidLingoMOPacketError):
        db.ingest_lingomo(json.dumps(packet), ingest_event_id)

    ingest_end = get_ingest_ids()

    assert len(ingest_end - ingest_begin) == 0

    packet["identity"] = old_id

    db.ingest_lingomo(json.dumps(packet), ingest_event_id)

    ingest_end = get_ingest_ids()

    assert len(ingest_end - ingest_begin) == 1
