from processor.database import repository

def test_repository_upsert_and_get(db_conn):
    repo_data = {
        "github_id": "MDQ6OlJlcG9zaXRvcnkx",
        "name": "test-repo",
        "full_name": "owner/test-repo",
        "url": "https://github.com/owner/test-repo",
        "description": "A test repository",
        "primary_language": "Python",
        "topics": ["test", "python"],
        "stars": 100,
        "forks": 10,
        "license": "MIT",
        "readme": "README content",
        "starred_at": "2024-01-01T00:00:00Z",
        "synced_at": "2024-01-01T00:00:00Z"
    }
    
    # 保存
    repository.upsert_repository(db_conn, repo_data)
    
    # 取得
    retrieved = repository.get_repository_by_id(db_conn, repo_data["github_id"])
    assert retrieved is not None
    assert retrieved["full_name"] == "owner/test-repo"
    assert retrieved["stars"] == 100
    
    # 全件取得
    all_repos = repository.get_all_repositories(db_conn)
    assert len(all_repos) == 1
    assert all_repos[0]["github_id"] == repo_data["github_id"]

def test_tags_management(db_conn):
    repo_id = "repo1"
    # タグ追加
    repository.get_or_create_tag(db_conn, "tag1")
    repository.set_tags_for_repo(db_conn, repo_id, ["tag1", "tag2"], source='manual')
    
    tags = repository.get_tags_for_repo(db_conn, repo_id)
    assert sorted(tags) == ["tag1", "tag2"]
    
    # タグ削除
    repository.remove_tag_from_repo(db_conn, repo_id, "tag1")
    tags = repository.get_tags_for_repo(db_conn, repo_id)
    assert tags == ["tag2"]

def test_sync_meta(db_conn):
    repository.set_sync_meta(db_conn, "last_starred_at", "2024-01-01T12:00:00Z")
    val = repository.get_sync_meta(db_conn, "last_starred_at")
    assert val == "2024-01-01T12:00:00Z"
