import logging
from textual.app import App
from .screens.main_screen import MainScreen
from processor.database.connection import get_db_connection, configure_backend
from processor.database.schema import initialize_schema

logger = logging.getLogger(__name__)

class GhFavoriteApp(App):
    """GitHub Star Favorite TUI Application."""
    
    CSS = """
    Screen {
        background: $surface;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "sync_incremental", "Sync"),
        ("S", "sync_full", "Full Sync"),
        ("C", "sync_cache", "Cache Sync"),
        ("r", "random_pick", "Random"),
        ("R", "shuffle_list", "Shuffle"),
        ("U", "re_tag_all", "Re-tag"),
        ("o", "open_browser", "Open"),
        ("/", "focus_search", "Search"),
        ("t", "edit_tags", "Tags"),
        ("?", "show_help", "Help"),
        ("escape", "go_back", "Back"),
    ]
    
    def action_show_help(self) -> None:
        from .screens.help_modal import HelpModal
        self.push_screen(HelpModal())

    def __init__(self, config):
        super().__init__()
        self.app_config = config
        self.cache_sync = None  # CacheSyncEngine (キャッシュモード時のみ設定)
        # バックエンドを設定してスキーマを初期化
        self._setup_backend()
        with get_db_connection(self.app_config.db_path) as conn:
            initialize_schema(conn)

    def _setup_backend(self) -> None:
        """設定に基づいてDBバックエンドを設定する。"""
        from processor.database.backends.sqlite_backend import SQLiteBackend

        config = self.app_config

        if config.db_backend == "mariadb":
            from processor.database.backends.mariadb_backend import MariaDBBackend
            from processor.database.sync_cache import CacheSyncEngine

            remote_backend = MariaDBBackend(
                host=config.mariadb_host,
                port=config.mariadb_port,
                user=config.mariadb_user,
                password=config.mariadb_password,
                database=config.mariadb_database,
            )

            if config.cache_enabled:
                # ローカルSQLiteキャッシュをメインバックエンドとして設定
                local_backend = SQLiteBackend(config.cache_path)
                configure_backend(local_backend)
                self.cache_sync = CacheSyncEngine(remote_backend, local_backend)
                logger.info("DB backend: MariaDB (remote) + SQLite cache (local)")
            else:
                # MariaDB 直接接続
                configure_backend(remote_backend)
                logger.info("DB backend: MariaDB (direct)")
        else:
            # SQLite モード (デフォルト)
            configure_backend(SQLiteBackend(config.db_path))
            logger.info("DB backend: SQLite (%s)", config.db_path)

    def on_mount(self) -> None:
        logger.info("GhFavoriteApp started and mounted.")
        self.push_screen(MainScreen())
        # バックグラウンドで検索エンジン（モデル）のロードを開始
        self._preload_search()
        # キャッシュモード時: リモートDB 接続可否を確認してオフライン通知
        if self.cache_sync is not None and not self.cache_sync.is_remote_available():
            self.call_after_refresh(
                self.notify,
                "NAS (MariaDB) is offline. Running in read-only cache mode.",
                severity="warning",
                timeout=8,
            )

    from textual import work
    @work(thread=True)
    def _preload_search(self) -> None:
        """検索エンジン（LLMなど）をバックグラウンドで事前ロードします。"""
        from processor.search import create_search
        try:
            # tagger_mode に関係なく、EmbeddingSearch を使う設定ならロードされる
            searcher = create_search(self.app_config.db_path, self.app_config.tagger_mode)
            if hasattr(searcher, "model"):
                _ = searcher.model  # プロパティアクセスでロードをトリガー
                logger.info("Search engine preloaded successfully.")
        except Exception as e:
            logger.error("Failed to preload search engine: %s", e)

    async def action_sync_cache(self) -> None:
        """NASからローカルキャッシュへデータを差分同期する (Cキー)。"""
        from .screens.progress_modal import ProgressModal

        if self.cache_sync is None:
            self.notify("Cache sync is not configured (backend is not mariadb+cache).",
                        severity="information")
            return

        if not self.cache_sync.is_remote_available():
            self.notify("NAS (MariaDB) is offline. Cannot sync cache.", severity="error")
            return

        self.push_screen(ProgressModal("Syncing cache from NAS..."))
        try:
            count = self.cache_sync.pull()
            self.notify("Cache sync complete: %d repositories updated." % count)
            screen = self.screen
            if isinstance(screen, MainScreen):
                await screen.reload_data()
        except Exception as e:
            self.notify("Cache sync failed: %s" % str(e), severity="error")
        finally:
            self.pop_screen()

    async def action_sync_incremental(self) -> None:
        from collector.github_client import GitHubClient
        from collector.sync import incremental_sync
        from processor.tagging import create_tagger
        from .screens.progress_modal import ProgressModal
        
        self.push_screen(ProgressModal("Syncing incremental data..."))
        client = GitHubClient(self.app_config.github_pat, self.app_config.sync_page_size)
        tagger = create_tagger(self.app_config.tagger_mode, self.app_config)
        
        try:
            with get_db_connection(self.app_config.db_path) as conn:
                count = await incremental_sync(client, conn, tagger)
            self.notify(f"Synced {count} repositories. (Tagger: {tagger.status_text})")
            screen = self.screen
            if isinstance(screen, MainScreen):
                screen.reload_data()
        except Exception as e:
            self.notify(f"Sync failed: {str(e)}", severity="error")
        finally:
            self.pop_screen()

    async def action_sync_full(self) -> None:
        from collector.github_client import GitHubClient
        from collector.sync import full_sync
        from processor.tagging import create_tagger
        from .screens.progress_modal import ProgressModal
        
        self.push_screen(ProgressModal("Syncing ALL starred repositories..."))
        client = GitHubClient(self.app_config.github_pat, self.app_config.sync_page_size)
        tagger = create_tagger(self.app_config.tagger_mode, self.app_config)
        
        try:
            with get_db_connection(self.app_config.db_path) as conn:
                count = await full_sync(client, conn, tagger)
            self.notify(f"Full sync completed: {count} repositories. (Tagger: {tagger.status_text})")
            screen = self.screen
            if isinstance(screen, MainScreen):
                screen.reload_data()
        except Exception as e:
            self.notify(f"Full sync failed: {str(e)}", severity="error")
        finally:
            self.pop_screen()

    async def action_re_tag_all(self) -> None:
        """ローカル DB の全リポジトリに現在の tags.yaml または学習済みモデルを再適用する。"""
        from processor.tagging import create_tagger
        from processor.database import repository
        from .screens.main_screen import MainScreen
        from .screens.progress_modal import ProgressModal

        self.push_screen(ProgressModal("Re-tagging all repositories locally..."))
        tagger = create_tagger(self.app_config.tagger_mode, self.app_config)

        try:
            with get_db_connection(self.app_config.db_path) as conn:
                repos = repository.get_all_repositories_for_retagging(conn)
                for repo in repos:
                    suggested_tags = tagger.suggest_tags(repo)
                    repository.set_tags_for_repo(
                        conn, repo["github_id"], suggested_tags, source="auto"
                    )
                conn.commit()

            count = len(repos)
            self.notify(f"Re-tagging complete: {count} repositories updated. (Tagger: {tagger.status_text})")

            screen = self.screen
            if isinstance(screen, MainScreen):
                await screen.reload_data()

        except Exception as e:
            self.notify(f"Re-tagging failed: {str(e)}", severity="error")
        finally:
            self.pop_screen()

    def action_random_pick(self) -> None:
        screen = self.screen
        if isinstance(screen, MainScreen):
            screen.action_random_pick()

    def action_focus_search(self) -> None:
        screen = self.screen
        if isinstance(screen, MainScreen):
            screen.action_focus_search()

    def action_shuffle_list(self) -> None:
        screen = self.screen
        if isinstance(screen, MainScreen):
            screen.action_shuffle_list()
            
    def action_go_back(self) -> None:
        if len(self.screen_stack) > 2:
            self.pop_screen()
