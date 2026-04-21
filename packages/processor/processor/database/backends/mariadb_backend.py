"""MariaDB/MySQL データベースバックエンド実装。"""
import logging
import re
from contextlib import contextmanager
from typing import Any, Generator

from .base import DatabaseBackend

logger = logging.getLogger(__name__)

# SQLite → MariaDB SQL 変換ルール (正規表現による順次変換)
_SQL_ADAPTATIONS: list[tuple[re.Pattern, str]] = [
    # Named params: :name → %(name)s
    (re.compile(r":(\w+)\b"), r"%(\1)s"),
    # INSERT OR REPLACE INTO → REPLACE INTO
    (re.compile(r"\bINSERT\s+OR\s+REPLACE\s+INTO\b", re.IGNORECASE), "REPLACE INTO"),
    # INSERT OR IGNORE INTO → INSERT IGNORE INTO
    (re.compile(r"\bINSERT\s+OR\s+IGNORE\s+INTO\b", re.IGNORECASE), "INSERT IGNORE INTO"),
    # ORDER BY RANDOM() → ORDER BY RAND()
    (re.compile(r"\bRANDOM\(\)", re.IGNORECASE), "RAND()"),
    # INTEGER PRIMARY KEY AUTOINCREMENT → INT NOT NULL AUTO_INCREMENT PRIMARY KEY
    (
        re.compile(r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b", re.IGNORECASE),
        "INT NOT NULL AUTO_INCREMENT PRIMARY KEY",
    ),
    # 残余の AUTOINCREMENT → AUTO_INCREMENT
    (re.compile(r"\bAUTOINCREMENT\b", re.IGNORECASE), "AUTO_INCREMENT"),
    # col ASC/DESC NULLS LAST → col IS NULL, col ASC/DESC
    # MariaDB は NULLS LAST 非サポートのため IS NULL トリックで代替
    (
        re.compile(r"(\w+(?:\.\w+)?)\s+(ASC|DESC)\s+NULLS\s+LAST", re.IGNORECASE),
        r"\1 IS NULL, \1 \2",
    ),
    # TEXT PRIMARY KEY → VARCHAR(255) PRIMARY KEY (インデックス付き列は TEXT 不可)
    (re.compile(r"\bTEXT\s+PRIMARY\s+KEY\b", re.IGNORECASE), "VARCHAR(255) PRIMARY KEY"),
    # TEXT UNIQUE NOT NULL → VARCHAR(255) UNIQUE NOT NULL (長さ制限のため)
    (
        re.compile(r"\bTEXT\s+UNIQUE\s+NOT\s+NULL\b", re.IGNORECASE),
        "VARCHAR(255) UNIQUE NOT NULL",
    ),
]


class _MariaDBCursor:
    """pymysql DictCursor を sqlite3 Cursor 互換のインターフェースでラップ。"""

    def __init__(self, cursor: Any):
        self._cursor = cursor

    @property
    def lastrowid(self) -> int | None:
        return self._cursor.lastrowid

    def fetchone(self) -> dict | None:
        return self._cursor.fetchone()  # DictCursor なので dict を返す

    def fetchall(self) -> list[dict]:
        return self._cursor.fetchall()  # list[dict]

    def __iter__(self):
        return iter(self.fetchall())


class _MariaDBConnection:
    """pymysql 接続を sqlite3.Connection 互換のインターフェースでラップ。

    SQL 実行前に adapt_sql() を呼び出してMariaDB方言へ変換する。
    これにより repository.py 等は SQLite 方言のまま記述でき、
    バックエンド切り替え時に呼び出し側の変更が不要になる。
    """

    def __init__(self, conn: Any, backend: "MariaDBBackend"):
        self._conn = conn
        self._backend = backend

    def execute(self, sql: str, params: Any = None) -> _MariaDBCursor:
        sql = self._backend.adapt_sql(sql)
        cursor = self._conn.cursor()
        cursor.execute(sql, params or ())
        return _MariaDBCursor(cursor)

    def executescript(self, script: str) -> None:
        """複数ステートメントを順次実行 (sqlite3.executescript 互換)。

        sqlite3.executescript はコミット前に実行するため、先にコミットする。
        """
        self._conn.commit()
        cursor = self._conn.cursor()
        for stmt in script.split(";"):
            stmt = stmt.strip()
            if not stmt or stmt.startswith("--"):
                continue
            adapted = self._backend.adapt_sql(stmt)
            try:
                cursor.execute(adapted)
            except Exception as e:
                # CREATE TABLE IF NOT EXISTS 等で既存テーブルを無視
                logger.debug("Schema statement skipped: %s... | %s", adapted[:60], e)

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


class MariaDBBackend(DatabaseBackend):
    """MariaDB/MySQL データベースバックエンド。

    将来の移行先として実装。現在の運用は SQLiteBackend を使用する。
    pymysql が必要: `uv add pymysql`
    """

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database

    @contextmanager
    def connect(self) -> Generator[Any, None, None]:
        """MariaDB 接続を取得するコンテキストマネージャ。"""
        try:
            import pymysql
            import pymysql.cursors
        except ImportError as exc:
            raise RuntimeError(
                "pymysql is required for MariaDB backend. "
                "Install with: uv add pymysql"
            ) from exc

        conn = pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )
        wrapped = _MariaDBConnection(conn, self)
        try:
            yield wrapped
        finally:
            conn.close()

    def get_placeholder(self) -> str:
        return "%s"

    def adapt_sql(self, sql: str) -> str:
        """SQLite 方言の SQL を MariaDB 方言に変換する。"""
        for pattern, replacement in _SQL_ADAPTATIONS:
            sql = pattern.sub(replacement, sql)
        return sql

    def is_available(self) -> bool:
        """MariaDB への接続可否を確認する (タイムアウト 3 秒)。"""
        try:
            import pymysql

            conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                connect_timeout=3,
            )
            conn.close()
            return True
        except Exception as e:
            logger.debug("MariaDB is not available: %s", e)
            return False

    @property
    def backend_type(self) -> str:
        return "mariadb"
