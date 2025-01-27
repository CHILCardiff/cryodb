import cryodb
import importlib.resources
import os
import pathlib
import mariadb
import pytest

TEST_SQLITE_NAME = "db_test_sqlite.db"

CRYODB_HOST = "localhost"
CRYODB_PORT = 3306
CRYODB_USER = "root"
CRYODB_PASSWORD = "cryoparty"

@pytest.fixture
def db_sqlite():
    db = cryodb.connect(
        path=TEST_SQLITE_NAME,
        sqlite_create_if_not_found=True
    ) 

    path_to_test = pathlib.Path(__file__).resolve()

    # Split into statements
    statements = cryodb.database.sql_to_statements(path_to_test.parent.parent / "test_database.sql")

    for statement in statements:
        db.cursor().execute(statement)

    # Run tests
    yield db

    db.disconnect()
    
    # Cleanup sqlite database if it exists
    os.remove(TEST_SQLITE_NAME)

@pytest.fixture
def db_mariadb():

    # Create database connection
    db = mariadb.connect(
        host = CRYODB_HOST,
        port = CRYODB_PORT,
        user = CRYODB_USER,
        password = CRYODB_PASSWORD,
    )

    cursor = db.cursor()
    try:
        cursor.execute("DROP DATABASE mariadb_test")
    except:
        pass

    cursor.execute("CREATE DATABASE mariadb_test")
    cursor.execute("USE mariadb_test")

    setup_scripts = (
        "init_schema.sql",
        "init_metadata.sql",
        "init_api.sql",
    )

    init_scripts = importlib.resources.files("cryodb.resources.sql.init")
    for script in setup_scripts:

        # Split into statements
        statements = cryodb.database.sql_to_statements(init_scripts/script)

        for statement in statements:
            cursor.execute(statement)

    path_to_test = pathlib.Path(__file__).resolve()

    # Split into statements
    statements = cryodb.database.sql_to_statements(path_to_test.parent.parent / "test_database.sql")

    for statement in statements:
        cursor.execute(statement)

    db.close()

    cryodb_obj = cryodb.connect(
        user="root", 
        password="cryoparty", 
        database="mariadb_test"
    ) 

    yield cryodb_obj

    cryodb_obj.disconnect()

