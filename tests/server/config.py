import cryodb
import cryodb.server
import importlib.resources
import mariadb
import pathlib
import pytest


@pytest.fixture
def cryodb_server_app():

    # Connect to localhost

    # Create app
    app = cryodb.server.create_app({
        "CRYODB_HOST"       : "localhost",
        "CRYODB_USER"       : "root",
        "CRYODB_PASSWORD"   : "cryoparty",
        "CRYODB_PORT"       : 3306,
        "CRYODB_DATABASE"   : "flask_test"
    })

    # Setup fake database
    with app.app_context():

        db = mariadb.connect(
            host = app.config["CRYODB_HOST"],
            port = app.config["CRYODB_PORT"],
            user = app.config["CRYODB_USER"],
            password = app.config["CRYODB_PASSWORD"],
        )

        cursor = db.cursor()

        try:
            cursor.execute("DROP DATABASE flask_test;")
        except:
            pass
        cursor.execute("CREATE DATABASE flask_test;")
        cursor.execute("USE flask_test;")

        setup_scripts = (
            "init_schema.sql", 
            "init_metadata.sql",
            "init_api.sql"
        )
        
        # Get path to scripts from module
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

    yield app

    with app.app_context():

        cursor = cryodb.server.get_cryodb().cursor()
        cursor.execute("DROP DATABASE flask_test;")

    

@pytest.fixture
def cryodb_server_client(cryodb_server_app):
    return cryodb_server_app.test_client()

@pytest.fixture
def cryodb_server_runner(cryodb_server_app):
    return cryodb_server_app.test_cli_runner()

