from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Input, ListView, ListItem, Label, Static
from textual.containers import Horizontal, Vertical
from textual.binding import Binding
from processor.database import repository
from processor.database.connection import get_db_connection
from .detail_screen import DetailScreen

class MainScreen(Screen):
    """リポジトリ一覧表示画面。"""
    
    CSS = """
    #sidebar {
        width: 20%;
        border-right: solid $accent;
    }
    #content {
        width: 80%;
    }
    #search_bar {
        margin: 1;
    }
    DataTable {
        height: 1fr;
    }
    """

    def __init__(self):
        super().__init__()
        self.tag_filter = None
        self.keyword = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Vertical(
                Label("Tags"),
                ListView(id="tag_list"),
                id="sidebar"
            ),
            Vertical(
                Input(placeholder="Search by keyword...", id="search_bar"),
                DataTable(id="repo_table"),
                id="content"
            )
        )
        yield Footer()

    async def on_mount(self) -> None:
        table = self.query_one("#repo_table", DataTable)
        table.cursor_type = "row"
        table.add_columns("⭐", "Language", "Name", "Tags", "Description")
        await self.reload_data()

    async def reload_data(self) -> None:
        """データを再読み込みして表示を更新します。"""
        await self.reload_tags()
        self.reload_table()

    async def reload_tags(self) -> None:
        """タグ一覧のみを再構築します。"""
        app_config = self.app.app_config
        with get_db_connection(app_config.db_path) as conn:
            tag_list = self.query_one("#tag_list", ListView)
            await tag_list.clear()
            tag_list.append(ListItem(Label(" [All] "), id="tag_all"))
            for tag in repository.get_all_tags(conn):
                tag_list.append(ListItem(Label(f" {tag} "), id=f"tag_{tag}"))

    def reload_table(self) -> None:
        """リポジトリ一覧のみを再構築します。"""
        app_config = self.app.app_config
        with get_db_connection(app_config.db_path) as conn:
            repos = repository.get_all_repositories(conn, tag_filter=self.tag_filter, keyword=self.keyword)
            table = self.query_one("#repo_table", DataTable)
            table.clear()
            for repo in repos:
                tags = repository.get_tags_for_repo(conn, repo["github_id"])
                table.add_row(
                    str(repo["stars"]),
                    repo["primary_language"] or "-",
                    repo["full_name"],
                    ", ".join(tags),
                    repo["description"] or "",
                    key=repo["github_id"]
                )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """タグが選択された時の処理。"""
        if event.item.id == "tag_all":
            self.tag_filter = None
        else:
            self.tag_filter = event.item.id.replace("tag_", "")
        self.reload_table()

    def on_input_changed(self, event: Input.Changed) -> None:
        """検索ワードが変更された時の処理。"""
        if event.input.id == "search_bar":
            self.keyword = event.value if event.value else None
            self.reload_table()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """リポジトリが選択された時の処理。"""
        repo_id = event.row_key.value
        self.app.push_screen(DetailScreen(repo_id))

    def action_random_pick(self) -> None:
        """ランダムにリポジトリを選択して詳細表示。"""
        app_config = self.app.app_config
        with get_db_connection(app_config.db_path) as conn:
            repo = repository.get_random_repository(conn, tag_filter=self.tag_filter)
            if repo:
                self.app.push_screen(DetailScreen(repo["github_id"]))
            else:
                self.notify("No repositories found.")

    def action_focus_search(self) -> None:
        self.query_one("#search_bar", Input).focus()
