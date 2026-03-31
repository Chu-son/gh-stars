import logging
import sqlite3
from datetime import datetime
from .github_client import GitHubClient
from processor.database import repository
from processor.tagging.base import TaggerStrategy

logger = logging.getLogger(__name__)

async def full_sync(
    client: GitHubClient,
    conn: sqlite3.Connection,
    tagger: TaggerStrategy,
) -> int:
    """全件同期を実行します。"""
    return await _sync(client, conn, tagger, since_iso=None)

async def incremental_sync(
    client: GitHubClient,
    conn: sqlite3.Connection,
    tagger: TaggerStrategy,
) -> int:
    """差分同期を実行します。"""
    last_starred_at = repository.get_sync_meta(conn, "last_starred_at")
    return await _sync(client, conn, tagger, since_iso=last_starred_at)

async def _sync(
    client: GitHubClient,
    conn: sqlite3.Connection,
    tagger: TaggerStrategy,
    since_iso: str | None = None
) -> int:
    """内部的な同期共通ロジック。"""
    count = 0
    newest_starred_at = None
    
    async for repo_data in client.fetch_starred_repos(since_iso=since_iso):
        # 1. リポジトリ情報を保存
        repository.upsert_repository(conn, repo_data)
        
        # 2. 自動タグ付け
        suggested_tags = tagger.suggest_tags(repo_data)
        if suggested_tags:
            repository.set_tags_for_repo(conn, repo_data["github_id"], suggested_tags, source='auto')
        
        if newest_starred_at is None:
            newest_starred_at = repo_data["starred_at"]
            
        count += 1
        if count % 50 == 0:
            logger.info(f"Synced {count} repositories...")
            conn.commit() # 定期的にコミット
            
    if count > 0:
        conn.commit()
        # 最新のスター日時を記録
        if newest_starred_at:
            # 既に記録されているものより新しければ更新
            current_last = repository.get_sync_meta(conn, "last_starred_at")
            if not current_last or newest_starred_at > current_last:
                repository.set_sync_meta(conn, "last_starred_at", newest_starred_at)
        
        repository.set_sync_meta(conn, "last_synced_at", datetime.now().isoformat())
        conn.commit()
        
    return count
