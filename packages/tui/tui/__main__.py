import argparse
import asyncio
import sys
from .config import load_config
from .app import GhFavoriteApp
from collector.github_client import GitHubClient
from collector.sync import full_sync, incremental_sync
from processor.database.connection import get_db_connection
from processor.database.schema import initialize_schema
from processor.tagging.rule_based import RuleBasedTagger

async def run_sync(config, full=False):
    """同期処理を実行します。"""
    client = GitHubClient(config.github_pat, config.sync_page_size)
    tagger = RuleBasedTagger() # フェーズ1はルールベース固定
    
    with get_db_connection(config.db_path) as conn:
        initialize_schema(conn)
        if full:
            print("Starting full sync...")
            count = await full_sync(client, conn, tagger)
        else:
            print("Starting incremental sync...")
            count = await incremental_sync(client, conn, tagger)
        print(f"Synced {count} repositories.")

def main():
    parser = argparse.ArgumentParser(description="GitHub Star Favorite TUI")
    parser.add_argument("--sync", action="store_true", help="差分同期を実行してから起動")
    parser.add_argument("--sync-full", action="store_true", help="全件同期を実行してから起動")
    parser.add_argument("--sync-only", action="store_true", help="同期のみ実行して終了")
    parser.add_argument("--config", default="config.yaml", help="設定ファイルのパス")
    
    args = parser.parse_args()
    config = load_config(args.config)
    
    if not config.github_pat and (args.sync or args.sync_full or args.sync_only):
        print("Error: GITHUB_PAT is not set. Please set it in .env or environment variable.")
        sys.exit(1)

    if args.sync or args.sync_full or args.sync_only:
        asyncio.run(run_sync(config, full=args.sync_full))
        if args.sync_only:
            return

    # TUI起動
    app = GhFavoriteApp(config)
    app.run()

if __name__ == "__main__":
    main()
