from textual.app import App
from .screens.main_screen import MainScreen
from processor.database.connection import get_db_connection
from processor.database.schema import initialize_schema

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
        # 初期化時にスキーマを確認
        with get_db_connection(self.app_config.db_path) as conn:
            initialize_schema(conn)

    def on_mount(self) -> None:
        self.push_screen(MainScreen())

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
