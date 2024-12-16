from .config import *

import pytest

def test_api_keys_in_config(cryodb_server_client):

    assert "admin" in pytest.TEST_API_KEYS
    assert "user" in pytest.TEST_API_KEYS
    assert "service" in pytest.TEST_API_KEYS

@pytest.mark.parametrize("type,role", (
    ("cryoegg","user"), ("cryowurst", "user"),
    ("cryoegg","admin"), ("cryowurst", "admin"),
    ("cryoegg","service"), ("cryowurst", "service"),
))
def test_get_instruments(cryodb_server_client, type, role):
    """test getting instruments from the cryodb server with
    cryoegg and cryowurst parameters
    """

    response = cryodb_server_client.get(
        f"instrument/{type}/list",         
        query_string={
            "key" : pytest.TEST_API_KEYS[role]
        }
    )

    # TODO: be more rigorous in testing that we have retrieved
    #       the correct instruments
    assert response.status_code == 200

@pytest.mark.parametrize("type", ("cryoegg", "cryowurst"))
def test_get_instrument_invalid_key(cryodb_server_client, type): 

    # Try and get instruments without providing key
    response = cryodb_server_client.get(
        f"instrument/{type}/list"
    )

    # Expect 401 Unauthorized status code because 
    # we haven't provided the API key
    assert response.status_code == 401

    # Try and get instruments providing an invalid key
    response = cryodb_server_client.get(
        f"instrument/{type}/list",
        query_string = {
            "key" : "invalid_key!"
        }
    )

@pytest.mark.parametrize("role", ("admin", "user", "service"))
def test_get_instrument_invalid_type(cryodb_server_client, role):

    response = cryodb_server_client.get(
        f"instrument/invalid/list",
        query_string = {
            "key" : pytest.TEST_API_KEYS[role]
        }
    )

    # Expect 400 Bad request
    assert response.status_code == 400