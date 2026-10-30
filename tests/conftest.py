import pytest

from core.db import get_connection, init_db

@pytest.fixture
def conn():
    connection = get_connection(":memory:")
    init_db(connection)
    yield connection
    connection.close()
    
