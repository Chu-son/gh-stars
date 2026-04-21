"""SQLite データベースバックエンド実装。"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from .base import DatabaseBackend


class SQLiteBackend(DatabaseBackend):
    """SQLite データベースバックエンド。

    ローカルファイルまたはインメモリ (":memory:") SQLite への接続を提供する。
    sqlite-vec 拡張は不使用 (ベクトル計算は Python 側で実施)。
    """

    def __init__(self, db_path: str | Path):
        """
        Args:
            db_path: SQLite データベースファイルのパス。
                     ":memory:" を指定するとインメモリDBとなる (テスト用途)。
        """
        self._db_path_str = str(db_path)
        # インメモリDBの場合は Path 変換しない
        if self._db_path_str == ":memory:":
            self.db_path = db_path
        else:
            self.db_path = Path(db_path)

    @contextmanager
    def connect(self) -> Generator[Any, None, None]:
        """SQLite 接続を取得するコンテキストマネージャ。"""
        if self._db_path_str != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self._db_path_str)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
        finally:
            conn.close()

    def get_placeholder(self) -> str:
        return "?"

    def adapt_sql(self, sql: str) -> str:
        """SQLite はそのまま返す (適応不要)。"""
        return sql

    def is_available(self) -> bool:
        """ローカルファイル DB は常に利用可能。"""
        return True

    @property
    def backend_type(self) -> str:
        return "sqlite"
