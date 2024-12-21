import pytest
import json
from .config import *

@pytest.mark.parametrize("role", ("admin","service"))
def test_lingomo_ingest(cryodb_server_app, role):

    packet = None
    with open("tests/lingomo_packet.json", "r") as fh:
        packet = json.load(fh)

    # Get raw data
    client = cryodb_server_app.test_client()

    # Enter app context
    with cryodb_server_app.app_context():
        
        # Get copy of db handle
        db = cryodb.server.get_cryodb()
        cursor = db.cursor()

        # Get current count of ingest_table
        cursor.execute("SELECT COUNT(*) FROM `ingest_table`")
        start_count = cursor.fetchone()[0]
        
        # Get count of cryoegg table
        cursor.execute("SELECT COUNT(*) FROM `cryoegg_raw_table`")
        cryoegg_raw_count = cursor.fetchone()[0]

        response = client.post("/ingest/lingomo", method=["POST",], json=packet, query_string={"key" : pytest.TEST_API_KEYS[role]})

        cursor.execute("SELECT COUNT(*) FROM `ingest_table`")
        end_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM `cryoegg_raw_table`")
        cryoegg_raw_new = cursor.fetchone()[0]

        assert end_count - start_count
        assert cryoegg_raw_new - cryoegg_raw_count
        assert response.status_code == 200

def test_bad_key(cryodb_server_client):
    
    response = cryodb_server_client.post("/ingest/lingomo", method=["POST",], json={}, query_string={"key" : "invalid_key"})

    assert response.status_code == 401 # unauthorised#
    assert response.mimetype == "application/json"

@pytest.mark.parametrize("role", ("admin","service"))
def test_bad_packet(cryodb_server_client, role):

    packet = {
        "not_a_real_packet" : 123,
        "nice_try" : "failed"
    }

    response = cryodb_server_client.post("/ingest/lingomo", method=["POST",], json=packet, query_string={"key" : pytest.TEST_API_KEYS[role]})

    assert response.status_code == 400 # bad request

    # Load actual packet
    with open("tests/lingomo_packet.json", "r") as fh:
        packet = json.load(fh)

    # Modify packet to remove key
    del packet["id"]

    response = cryodb_server_client.post("/ingest/lingomo", method=["POST",], json=packet, query_string={"key" : pytest.TEST_API_KEYS[role]})

    assert response.status_code == 400 # bad request

def test_invalid_ingest_event(cryodb_server_app):

    with open("tests/lingomo_packet.json", "r") as fh:
        packet = json.load(fh)
    
    cryodb_server_app.config["LINGOMO_EVENT_ID"] = 9999

    response = cryodb_server_app.test_client().post("/ingest/lingomo", method=["POST",], json=packet, query_string={"key" : pytest.TEST_API_KEYS["admin"]})

    assert response.status_code == 500 # internal server error