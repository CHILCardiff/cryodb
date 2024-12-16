from .config import *

import pytest



@pytest.mark.parametrize("role", ("user", "admin", "service"))
def test_get_receivers(cryodb_server_client, role):
    """test getting receivers from the cryodb server
    """

    response = cryodb_server_client.get(
        f"receiver/list",
        query_string = {
            "key" : pytest.TEST_API_KEYS[role]
        }
    )

    assert response.status_code == 200