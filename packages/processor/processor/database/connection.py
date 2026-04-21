"""データベース接続のファクトリ関数 (後方互換インターフェース)。

このモジュールは既存の全呼び出し箇所 (get_db_connection(db_path)) を
変更不要にするための後方互換ファクトリを提供する。

DAL切り替え方法:
    1. 起動時に configure_backend(MariaDBBackend(...)) を呼び出す
    2. 以降は全ての get_db_connection() 呼び出しが自動的に新バックエンドを使用する
    3. db_path を渡している既存コードは変更不要

バックエンド未設定時の動作:
    - db_path が渡された場合: SQLiteBackend(db_path) を生成して使用
    - db_path も未指定の場合: RuntimeError
"""
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .backends.base import DatabaseBackend

# グローバルバックエンド設定 (configure_backend() で設定する)
_configured_backend: DatabaseBackend | None = None


def configure_backend(backend: DatabaseBackend) -> None:
    """アプリ起動時にデフォルトのDBバックエンドを設定する。

    設定後は全ての get_db_connection() 呼び出しがこのバックエンドを使用する。
    db_path 引数は無視される (後方互換インターフェースのため引数自体は残す)。

    Args:
        backend: DatabaseBackend のインスタンス
    """
    global _configured_backend
    _configured_backend = backend


def get_configured_backend() -> DatabaseBackend | None:
    """現在設定されているバックエンドを返す。未設定の場合は None。"""
    return _configured_backend


@contextmanager
def get_db_connection(db_path: str | Path | None = None):
    """DB接続を取得するコンテキストマネージャ (後方互換インターフェース)。

    Args:
        db_path: SQLite ファイルパス。configure_backend() が設定済みの場合は
                 このパラメータは無視され、設定済みバックエンドが使用される。
                 None かつバックエンド未設定の場合は RuntimeError。

    Yields:
        sqlite3.Connection 互換の接続オブジェクト。

    Notes:
        既存の全呼び出し箇所 (get_db_connection(config.db_path) 等) は変更不要。
        将来的に configure_backend(MariaDBBackend(...)) を呼び出すだけで
        全コンポーネントが透過的に新バックエンドを利用できる。
    """
    if _configured_backend is not None:
        # バックエンドが設定済みの場合は常にそれを使用 (db_path は無視)
        backend = _configured_backend
    elif db_path is not None:
        # 後方互換: db_path が渡された場合は SQLiteBackend を生成
        from .backends.sqlite_backend import SQLiteBackend
        backend = SQLiteBackend(db_path)
    else:
        raise RuntimeError(
            "DB backend is not configured. "
            "Either pass db_path or call configure_backend() first."
        )

    with backend.connect() as conn:
        yield conn
