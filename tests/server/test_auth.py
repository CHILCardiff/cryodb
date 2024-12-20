import pytest
from .config import *

def test_ip_authentication(cryodb_server_app):

    for ip, key in pytest.TEST_API_KEYS_IP.items():
        with cryodb_server_app.test_request_context(
            environ_base = {'REMOTE_ADDR' : ip}
        ):

            type, permissions = cryodb.server.validate_api_key()
            assert type == cryodb.APIKeyType.IP

    # Try without key
    with cryodb_server_app.test_request_context(
        environ_base = {'REMOTE_ADDR' : "123.123.123.123"}
    ):

        with pytest.raises(cryodb.InvalidAPIKeyError):
            type, permissions = cryodb.server.validate_api_key()