import pytest
from processor.database.backends.sqlite_backend import SQLiteBackend
from processor.database.schema import initialize_schema
import respx


@pytest.fixture
def db_conn():
    """インメモリSQLiteデータベース接続を提供します (SQLiteBackend経由)。"""
    backend = SQLiteBackend(":memory:")
    with backend.connect() as conn:
        initialize_schema(conn)
        yield conn


@pytest.fixture
def mock_api():
    """RESPXによるGitHub APIのモックを提供します。"""
    with respx.mock as mock:
        yield mock
