import httpx
import logging
from typing import AsyncIterator, Optional

logger = logging.getLogger(__name__)

GRAPHQL_QUERY = """
query StarredRepos($cursor: String, $pageSize: Int!) {
  viewer {
    starredRepositories(
      first: $pageSize
      after: $cursor
      orderBy: {field: STARRED_AT, direction: DESC}
    ) {
      pageInfo {
        hasNextPage
        endCursor
      }
      edges {
        starredAt
        node {
          id
          name
          nameWithOwner
          url
          description
          primaryLanguage { name }
          repositoryTopics(first: 20) {
            nodes { topic { name } }
          }
          stargazerCount
          forkCount
          licenseInfo { name }
        }
      }
    }
  }
}
"""

class GitHubClient:
    def __init__(self, pat: str, page_size: int = 100):
        self.pat = pat
        self.page_size = page_size
        self.url = "https://api.github.com/graphql"
        self.headers = {
            "Authorization": f"bearer {self.pat}",
            "Content-Type": "application/json",
        }

    async def fetch_starred_repos(
        self,
        since_iso: Optional[str] = None
    ) -> AsyncIterator[dict]:
        """
        スター付きリポジトリを非同期イテレータとして返します。
        since_iso が指定された場合、それより新しいスターのみを返します。
        """
        cursor = None
        has_next_page = True

        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            while has_next_page:
                variables = {
                    "cursor": cursor,
                    "pageSize": self.page_size
                }
                
                try:
                    response = await client.post(
                        self.url,
                        json={"query": GRAPHQL_QUERY, "variables": variables}
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    if "errors" in data:
                        logger.error(f"GraphQL Errors: {data['errors']}")
                        break
                        
                    starred_repos = data["data"]["viewer"]["starredRepositories"]
                    page_info = starred_repos["pageInfo"]
                    edges = starred_repos["edges"]
                    
                    for edge in edges:
                        starred_at = edge["starredAt"]
                        
                        # since_iso より古いスターが出てきたら終了（降順のため）
                        if since_iso and starred_at <= since_iso:
                            has_next_page = False
                            break
                            
                        node = edge["node"]
                        
                        # 扱いやすいフラットな辞書に変換
                        repo = {
                            "github_id": node["id"],
                            "name": node["name"],
                            "full_name": node["nameWithOwner"],
                            "url": node["url"],
                            "description": node["description"],
                            "primary_language": node["primaryLanguage"]["name"] if node["primaryLanguage"] else None,
                            "topics": [t["topic"]["name"] for t in node["repositoryTopics"]["nodes"]],
                            "stars": node["stargazerCount"],
                            "forks": node["forkCount"],
                            "license": node["licenseInfo"]["name"] if node["licenseInfo"] else None,
                            "readme": None, # README本文の取得はフェーズ6以降で検討
                            "starred_at": starred_at
                        }
                        yield repo
                    
                    if not has_next_page:
                        break
                        
                    has_next_page = page_info["hasNextPage"]
                    cursor = page_info["endCursor"]
                    
                    # レート制限の確認 (Header: X-RateLimit-Remaining)
                    remaining = response.headers.get("X-RateLimit-Remaining")
                    if remaining and int(remaining) < 10:
                        logger.warning("GitHub API Rate limit almost reached.")
                        # ここで必要に応じてスリープを入れる等の対応が可能
                        
                except httpx.HTTPStatusError as e:
                    logger.error(f"HTTP Error: {e.response.status_code} - {e.response.text}")
                    break
                except Exception as e:
                    logger.error(f"Unexpected Error during fetch: {str(e)}")
                    break
