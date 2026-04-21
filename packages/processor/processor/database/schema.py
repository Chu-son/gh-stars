BASE_SCHEMA = """
CREATE TABLE IF NOT EXISTS repositories (
  github_id        TEXT PRIMARY KEY,
  name             TEXT NOT NULL,
  full_name        TEXT NOT NULL,
  url              TEXT NOT NULL,
  description      TEXT,
  primary_language TEXT,
  topics           TEXT,          -- JSON array string
  stars            INTEGER DEFAULT 0,
  forks            INTEGER DEFAULT 0,
  license          TEXT,
  readme           TEXT,
  starred_at       TEXT NOT NULL, -- ISO8601
  synced_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tags (
  id   INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS repository_tags (
  repo_id TEXT    NOT NULL REFERENCES repositories(github_id) ON DELETE CASCADE,
  tag_id  INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  source  TEXT    NOT NULL CHECK(source IN ('auto', 'manual')),
  PRIMARY KEY (repo_id, tag_id)
);

CREATE TABLE IF NOT EXISTS tag_edit_history (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  repo_id   TEXT NOT NULL,
  action    TEXT NOT NULL CHECK(action IN ('add', 'remove')),
  tag_name  TEXT NOT NULL,
  edited_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_meta (
  key   TEXT PRIMARY KEY,
  value TEXT
);
"""

VEC_SCHEMA = """
-- ベクトル検索用テーブル。embedding は float32 バイト列 (BLOB) として格納し、
-- 類似度計算は Python (numpy) 側で実行する (sqlite-vec 拡張不使用)。
CREATE TABLE IF NOT EXISTS vec_repositories (
  repo_id   TEXT PRIMARY KEY,
  embedding BLOB
);
"""

def initialize_schema(conn) -> None:
    """データベースのスキーマを初期化します。

    Args:
        conn: sqlite3.Connection 互換の接続オブジェクト。
              MariaDBBackend 経由の接続の場合は自動的に SQL 方言が変換される。
    """
    conn.executescript(BASE_SCHEMA)
    conn.executescript(VEC_SCHEMA)
    conn.commit()
