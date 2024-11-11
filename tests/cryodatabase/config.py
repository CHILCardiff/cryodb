import cryodb
import os
import pathlib
import pytest

TEST_SQLITE_NAME = "db_test_sqlite.db"

@pytest.fixture
def db_sqlite():
    db = cryodb.connect(
        path=TEST_SQLITE_NAME,
        create_if_not_found=True
    ) 
    # Run tests
    yield db

    db.disconnect()
    # Cleanup sqlite database if it exists
    os.remove(TEST_SQLITE_NAME)

@pytest.fixture
def db_mariadb():
    return cryodb.connect(
    user="root", 
    password="cryoparty", 
    database="cryodb_test"
) 