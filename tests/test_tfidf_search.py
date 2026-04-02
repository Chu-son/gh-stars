import pytest
import sqlite3
from processor.search.tfidf_search import TfidfSearch
from processor.database.schema import initialize_schema
from processor.database.repository import upsert_repository

@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    initialize_schema(conn)
    return conn

def test_tfidf_search_similarity(db_conn):
    # テストデータの投入
    repos = [
        {
            "github_id": "repo1", "name": "gh-stars", "full_name": "chuson/gh-stars",
            "url": "http://x.com", "description": "TUI tool for managing GitHub stars",
            "primary_language": "Python", "topics": ["tui", "cli", "github"],
            "stars": 1, "forks": 0, "license": "MIT", "readme": None,
            "starred_at": "2024-01-01T00:00:00Z", "synced_at": "2024-01-01T00:00:00Z"
        },
        {
            "github_id": "repo2", "name": "other-tui", "full_name": "someone/other-tui",
            "url": "http://x.com", "description": "A terminal interface for managing bookmarks",
            "primary_language": "Rust", "topics": ["tui", "terminal", "cli"],
            "stars": 1, "forks": 0, "license": "MIT", "readme": None,
            "starred_at": "2024-01-01T00:00:00Z", "synced_at": "2024-01-01T00:00:00Z"
        },
        {
            "github_id": "repo3", "name": "ml-lib", "full_name": "lab/ml-lib",
            "url": "http://x.com", "description": "Fast machine learning library in C++",
            "primary_language": "C++", "topics": ["ml", "ai", "high-performance"],
            "stars": 1, "forks": 0, "license": "MIT", "readme": None,
            "starred_at": "2024-01-01T00:00:00Z", "synced_at": "2024-01-01T00:00:00Z"
        }
    ]
    for r in repos:
        upsert_repository(db_conn, r)
    
    searcher = TfidfSearch(db_conn)
    
    # repo1 に近いのは repo2 (ともに TUI, CLI) であるべき
    similar = searcher.find_similar("repo1", top_k=1)
    assert len(similar) == 1
    assert similar[0]["github_id"] == "repo2"
    
    # repo3 に近いのは repo1 または repo2 よりも他はないが、
    # 語彙が重複していない場合はなにもでないかも
    similar3 = searcher.find_similar("repo3", top_k=1)
    if similar3:
        # とりあえず top_k 分だけ返ってくる場合はあるが、
        # 今回の極小データセットではどれかしら出るはず
        assert similar3[0]["github_id"] in ["repo1", "repo2"]
