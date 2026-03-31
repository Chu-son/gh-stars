import pytest
import sqlite3
import respx
from processor.database.schema import initialize_schema

@pytest.fixture
def db_conn():
    """インメモリSQLiteデータベース接続を提供します。"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    initialize_schema(conn)
    yield conn
    conn.close()

@pytest.fixture
def mock_api():
    """RESPXによるGitHub APIのモックを提供します。"""
    with respx.mock as mock:
        yield mock
