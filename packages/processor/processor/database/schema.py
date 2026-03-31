SCHEMA = """
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

def initialize_schema(conn):
    """データベースのスキーマを初期化します。"""
    conn.executescript(SCHEMA)
    conn.commit()
