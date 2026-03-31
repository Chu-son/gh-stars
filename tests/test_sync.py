import pytest
import respx
from httpx import Response
from collector.github_client import GitHubClient
from collector.sync import full_sync
from processor.tagging.rule_based import RuleBasedTagger
from processor.database import repository

@pytest.mark.asyncio
async def test_full_sync(db_conn, mock_api):
    # GraphQLレスポンスのモック
    mock_payload = {
        "data": {
            "viewer": {
                "starredRepositories": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "edges": [
                        {
                            "starredAt": "2024-01-01T00:00:00Z",
                            "node": {
                                "id": "repo1",
                                "name": "repo1",
                                "nameWithOwner": "owner/repo1",
                                "url": "https://github.com/owner/repo1",
                                "description": "python cli tool",
                                "primaryLanguage": {"name": "Python"},
                                "repositoryTopics": {"nodes": [{"topic": {"name": "cli"}}]},
                                "stargazerCount": 100,
                                "forkCount": 10,
                                "licenseInfo": {"name": "MIT"}
                            }
                        }
                    ]
                }
            }
        }
    }
    mock_api.post("https://api.github.com/graphql").mock(return_value=Response(200, json=mock_payload))
    
    client = GitHubClient("token")
    tagger = RuleBasedTagger()
    
    count = await full_sync(client, db_conn, tagger)
    
    assert count == 1
    repo = repository.get_repository_by_id(db_conn, "repo1")
    assert repo["name"] == "repo1"
    
    # 自動タグ付けの確認
    tags = repository.get_tags_for_repo(db_conn, "repo1")
    assert "python" in tags
    assert "cli" in tags
    
    # 同期メタデータの更新確認
    assert repository.get_sync_meta(db_conn, "last_starred_at") == "2024-01-01T00:00:00Z"
