import json
import sqlite3
from datetime import datetime

# リポジトリ操作

def upsert_repository(conn: sqlite3.Connection, repo: dict) -> None:
    """リポジトリ情報を保存または更新します。"""
    query = """
    INSERT OR REPLACE INTO repositories (
        github_id, name, full_name, url, description, primary_language,
        topics, stars, forks, license, readme, starred_at, synced_at
    ) VALUES (
        :github_id, :name, :full_name, :url, :description, :primary_language,
        :topics, :stars, :forks, :license, :readme, :starred_at, :synced_at
    )
    """
    # topicsはJSON文字列として保存
    data = repo.copy()
    if isinstance(data.get("topics"), (list, tuple)):
        data["topics"] = json.dumps(data["topics"])
    
    if "synced_at" not in data:
        data["synced_at"] = datetime.now().isoformat()
        
    conn.execute(query, data)

SORT_COLUMNS = {
    "stars":      "r.stars",
    "name":       "r.full_name",
    "language":   "r.primary_language",
    "starred_at": "r.starred_at",
}

def get_all_repositories(conn: sqlite3.Connection, tag_filter: str | None = None,
                         language_filter: str | None = None,
                         keyword: str | None = None, sort_by: str = "starred_at",
                         sort_descending: bool = True) -> list[dict]:
    """リポジトリ一覧を取得します。"""
    query = "SELECT r.* FROM repositories r"
    params = {}
    where_clauses = []

    if tag_filter:
        query += " JOIN repository_tags rt ON r.github_id = rt.repo_id"
        query += " JOIN tags t ON rt.tag_id = t.id"
        where_clauses.append("t.name = :tag_filter")
        params["tag_filter"] = tag_filter

    if language_filter:
        where_clauses.append("r.primary_language = :language_filter")
        params["language_filter"] = language_filter

    if keyword:
        where_clauses.append("(r.full_name LIKE :keyword OR r.description LIKE :keyword OR r.topics LIKE :keyword)")
        params["keyword"] = f"%{keyword}%"

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    
    col = SORT_COLUMNS.get(sort_by, SORT_COLUMNS["starred_at"])
    direction = "DESC" if sort_descending else "ASC"
    
    if sort_by == "language":
        order_clause = f"{col} {direction} NULLS LAST"
    else:
        order_clause = f"{col} {direction}"
        
    query += f" ORDER BY {order_clause}"
    
    cursor = conn.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]

def get_repository_by_id(conn: sqlite3.Connection, github_id: str) -> dict | None:
    """ID\u6307\u5b9a\u3067\u30ea\u30dd\u30b8\u30c8\u30ea\u3092\u53d6\u5fb7\u3059\u308b\u3002"""
    query = "SELECT * FROM repositories WHERE github_id = ?"
    row = conn.execute(query, (github_id,)).fetchone()
    return dict(row) if row else None

def get_all_repositories_for_retagging(conn: sqlite3.Connection) -> list[dict]:
    """\u518d\u30bf\u30b0\u4ed8\u3051\u5c02\u7528: topics \u3092 list[str] \u306b\u30c7\u30b7\u30ea\u30a2\u30e9\u30a4\u30ba\u3057\u3066\u5168\u30ea\u30dd\u30b8\u30c8\u30ea\u3092\u8fd4\u3059\u3002
    
    \u901a\u5e38\u306e get_all_repositories() \u306f topics \u3092 str \u306e\u307e\u307e\u8fd4\u3059\u305f\u3081\u3001
    \u30bf\u30ac\u30fc\u306b\u6e21\u3059\u524d\u306e\u578b\u5909\u63db\u304c\u5fc5\u8981\u306a\u5b34\u5408\u306b\u3053\u306e\u95a2\u6570\u3092\u4f7f\u3046\u3002
    """
    cursor = conn.execute("SELECT * FROM repositories")
    repos = []
    for row in cursor.fetchall():
        repo = dict(row)
        # topics \u306f JSON \u6587\u5b57\u5217 \u2192 list[str] \u306b\u5909\u63db
        if isinstance(repo.get("topics"), str):
            try:
                repo["topics"] = json.loads(repo["topics"])
            except (json.JSONDecodeError, TypeError):
                repo["topics"] = []
        else:
            repo["topics"] = []
        repos.append(repo)
    return repos

def get_random_repository(conn: sqlite3.Connection, tag_filter: str | None = None) -> dict | None:
    """ランダムにリポジトリを1つ取得します。"""
    query = "SELECT r.* FROM repositories r"
    params = {}
    
    if tag_filter:
        query += " JOIN repository_tags rt ON r.github_id = rt.repo_id"
        query += " JOIN tags t ON rt.tag_id = t.id"
        query += " WHERE t.name = :tag_filter"
        params["tag_filter"] = tag_filter
        
    query += " ORDER BY RANDOM() LIMIT 1"
    
    row = conn.execute(query, params).fetchone()
    return dict(row) if row else None

# タグ操作

def get_or_create_tag(conn: sqlite3.Connection, name: str) -> int:
    """タグを取得または作成し、そのIDを返します。"""
    cursor = conn.execute("SELECT id FROM tags WHERE name = ?", (name,))
    row = cursor.fetchone()
    if row:
        return row[0]
    
    cursor = conn.execute("INSERT INTO tags (name) VALUES (?)", (name,))
    return cursor.lastrowid

def get_tags_for_repo(conn: sqlite3.Connection, repo_id: str) -> list[str]:
    """指定したリポジトリに紐づくタグ名一覧を取得します。"""
    query = """
    SELECT t.name FROM tags t
    JOIN repository_tags rt ON t.id = rt.tag_id
    WHERE rt.repo_id = ?
    """
    cursor = conn.execute(query, (repo_id,))
    return [row[0] for row in cursor.fetchall()]

def set_tags_for_repo(conn: sqlite3.Connection, repo_id: str, tag_names: list[str],
                      source: str = 'auto') -> None:
    """リポジトリのタグをリセットして設定します。"""
    # 既存の当該ソースのタグを削除（手動タグは残す等の制御が必要ならソースを指定）
    # 今回は単純化のため、指定したソースのタグを全削除して入れ替え
    conn.execute("DELETE FROM repository_tags WHERE repo_id = ? AND source = ?", (repo_id, source))
    
    for name in tag_names:
        tag_id = get_or_create_tag(conn, name)
        conn.execute("INSERT OR IGNORE INTO repository_tags (repo_id, tag_id, source) VALUES (?, ?, ?)",
                     (repo_id, tag_id, source))
        
        if source == 'manual':
            record_tag_edit(conn, repo_id, 'add', name)

def add_tag_to_repo(conn: sqlite3.Connection, repo_id: str, tag_name: str, source: str) -> None:
    """タグを追加します。"""
    tag_id = get_or_create_tag(conn, tag_name)
    conn.execute("INSERT OR IGNORE INTO repository_tags (repo_id, tag_id, source) VALUES (?, ?, ?)",
                 (repo_id, tag_id, source))
    if source == 'manual':
        record_tag_edit(conn, repo_id, 'add', tag_name)

def remove_tag_from_repo(conn: sqlite3.Connection, repo_id: str, tag_name: str) -> None:
    """タグを削除します。"""
    cursor = conn.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
    row = cursor.fetchone()
    if row:
        tag_id = row[0]
        conn.execute("DELETE FROM repository_tags WHERE repo_id = ? AND tag_id = ?", (repo_id, tag_id))
        record_tag_edit(conn, repo_id, 'remove', tag_name)

def get_all_tags(conn: sqlite3.Connection) -> list[str]:
    """登録されている全タグ名を取得します。"""
    cursor = conn.execute("SELECT name FROM tags ORDER BY name ASC")
    return [row[0] for row in cursor.fetchall()]

def get_all_languages(conn: sqlite3.Connection) -> list[str]:
    """登録されている全リポジトリの主要言語(primary_language)一覧を取得します。"""
    query = "SELECT DISTINCT primary_language FROM repositories WHERE primary_language IS NOT NULL ORDER BY primary_language ASC"
    cursor = conn.execute(query)
    return [row[0] for row in cursor.fetchall()]

def record_tag_edit(conn: sqlite3.Connection, repo_id: str, action: str, tag_name: str) -> None:
    """タグの変更履歴を記録します。"""
    query = "INSERT INTO tag_edit_history (repo_id, action, tag_name, edited_at) VALUES (?, ?, ?, ?)"
    conn.execute(query, (repo_id, action, tag_name, datetime.now().isoformat()))

# 同期メタ操作

def get_sync_meta(conn: sqlite3.Connection, key: str) -> str | None:
    """同期メタデータを取得します。"""
    cursor = conn.execute("SELECT value FROM sync_meta WHERE key = ?", (key,))
    row = cursor.fetchone()
    return row[0] if row else None

def set_sync_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    """同期メタデータを保存します。"""
    conn.execute("INSERT OR REPLACE INTO sync_meta (key, value) VALUES (?, ?)", (key, value))
