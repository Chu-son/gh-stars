import sqlite3
from contextlib import contextmanager
from pathlib import Path

@contextmanager
def get_db_connection(db_path: str | Path):
    """
    SQLiteデータベースへの接続を取得し、WALモードを有効にします。
    コンテキストを抜ける際に自動的にクローズします。
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    # 辞書形式で結果を取得できるように設定
    conn.row_factory = sqlite3.Row
    
    try:
        # WALモードを有効化（書き込み時の同時実行性能向上）
        conn.execute("PRAGMA journal_mode=WAL")
        # 外部キー制約を有効化
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
    finally:
        conn.close()
