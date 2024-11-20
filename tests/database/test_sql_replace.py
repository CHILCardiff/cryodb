import pytest
from cryodb.database import sql_to_statements

def test_sql_to_statements():

    statements = sql_to_statements("src/cryodb/resources/sql/init/init_api.sql")

    pass