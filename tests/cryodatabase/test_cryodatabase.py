import cryodb

# Libraries for import required for testing
import mariadb
import os
import pytest
import pathlib

def test_connect():
    """Requires that localhost server running valid MariaDB 
    server is open"""

    print(pathlib.Path(".").resolve())

    # Test that we can't open a non-existent database
    with pytest.raises(FileNotFoundError):
        db = cryodb.connect(
            path="invalid_file_path.db"
        )

    # Check that the output of db is a CryoDatabase object
    assert isinstance(db, cryodb.CryoDatabase)

def test_initialise_sqlite_db():
    
    test_path = pathlib.Path("tmpdb.db")
    
    try:
        # Specify create if not exists flagabse
        db = cryodb.connect(path=test_path, create_if_not_found=True)
        # Check that we've created an instance of CryoDatabase
        assert isinstance(db, cryodb.CryoDatabase)
        db.disconnect()
    finally:
        if test_path.exists():
            os.remove(test_path)


    
def test_validate():

    assert False