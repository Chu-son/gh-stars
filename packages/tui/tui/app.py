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
        ("o", "open_browser", "Open"),
        ("/", "focus_search", "Search"),
        ("t", "edit_tags", "Tags"),
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, config):
        super().__init__()
        self.app_config = config
        # 初期化時にスキーマを確認
        with get_db_connection(self.app_config.db_path) as conn:
            initialize_schema(conn)

    def on_mount(self) -> None:
        self.push_screen(MainScreen())

    async def action_sync_incremental(self) -> None:
        # 非同期で同期処理を呼び出す（UIをブロックしないためには工夫が必要だが今回はシンプルに）
        from collector.github_client import GitHubClient
        from collector.sync import incremental_sync
        from processor.tagging.rule_based import RuleBasedTagger
        
        self.notify("Starting incremental sync...")
        client = GitHubClient(self.app_config.github_pat, self.app_config.sync_page_size)
        tagger = RuleBasedTagger()
        
        try:
            with get_db_connection(self.app_config.db_path) as conn:
                count = await incremental_sync(client, conn, tagger)
            self.notify(f"Synced {count} repositories.")
            # メイン画面のリロードを通知
            screen = self.screen
            if isinstance(screen, MainScreen):
                screen.reload_data()
        except Exception as e:
            self.notify(f"Sync failed: {str(e)}", severity="error")

    async def action_sync_full(self) -> None:
        from collector.github_client import GitHubClient
        from collector.sync import full_sync
        from processor.tagging.rule_based import RuleBasedTagger
        
        self.notify("Starting full sync...")
        client = GitHubClient(self.app_config.github_pat, self.app_config.sync_page_size)
        tagger = RuleBasedTagger()
        
        try:
            with get_db_connection(self.app_config.db_path) as conn:
                count = await full_sync(client, conn, tagger)
            self.notify(f"Full sync completed: {count} repositories.")
            screen = self.screen
            if isinstance(screen, MainScreen):
                screen.reload_data()
        except Exception as e:
            self.notify(f"Full sync failed: {str(e)}", severity="error")

    def action_random_pick(self) -> None:
        screen = self.screen
        if isinstance(screen, MainScreen):
            screen.action_random_pick()

    def action_focus_search(self) -> None:
        screen = self.screen
        if isinstance(screen, MainScreen):
            screen.action_focus_search()
            
    def action_go_back(self) -> None:
        if len(self.screen_stack) > 2:
            self.pop_screen()
