from .config import *

def test_validate_db(cryodb_server_app):
    """ Check that we can succesfully initialise and validate
    a MariaDB connection
    """
    
    with cryodb_server_app.app_context():

        db = cryodb.server.get_cryodb()
        assert db.validate()
