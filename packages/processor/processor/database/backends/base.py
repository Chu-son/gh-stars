"""データベースバックエンドの抽象基底クラス。"""
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Generator


class DatabaseBackend(ABC):
    """データベースバックエンドの抽象基底クラス。

    特定のDBに依存しないDALインターフェースを定義する。
    新しいDBバックエンドはこのクラスを継承して実装する。
    現在の実装: SQLiteBackend, MariaDBBackend
    """

    @abstractmethod
    @contextmanager
    def connect(self) -> Generator[Any, None, None]:
        """コンテキストマネージャとしてDB接続を取得する。

        Yields:
            sqlite3.Connection 互換の接続オブジェクト。
            execute(), executescript(), commit(), close() をサポートする。
        """

    @abstractmethod
    def get_placeholder(self) -> str:
        """SQLクエリのパラメータプレースホルダ文字を返す。

        Returns:
            SQLite: '?', MariaDB/MySQL: '%s'
        """

    @abstractmethod
    def adapt_sql(self, sql: str) -> str:
        """SQLite 方言で書かれた SQL をバックエンド固有の方言に変換する。

        repository.py 等の SQL は SQLite 方言で記述し、実行前にこのメソッドで
        変換することで、各バックエンド間の方言差異を吸収する。

        Args:
            sql: SQLite 方言の SQL 文

        Returns:
            バックエンド固有の方言に変換された SQL 文
        """

    @abstractmethod
    def is_available(self) -> bool:
        """バックエンドへの接続が利用可能かを確認する。

        Returns:
            接続可能な場合 True。ローカルSQLiteは常に True。
            MariaDB等のネットワークDBは接続テストを行う。
        """

    @property
    def backend_type(self) -> str:
        """バックエンドの種別を文字列で返す ('sqlite', 'mariadb', etc.)"""
        return self.__class__.__name__.replace("Backend", "").lower()
