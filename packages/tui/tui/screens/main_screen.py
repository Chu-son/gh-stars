from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Input, ListView, ListItem, Label, Static
from textual.containers import Horizontal, Vertical
from textual.binding import Binding
from textual.coordinate import Coordinate
import random
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
    #status_bar {
        background: $accent;
        color: $text;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("g", "cursor_top", "Top", show=False),
        Binding("G", "cursor_bottom", "Bottom", show=False),
        Binding("l", "open_detail", "Open", show=False),
        Binding("ctrl+d", "page_down", "PgDn", show=False),
        Binding("ctrl+u", "page_up", "PgUp", show=False),
        Binding("1", "sort_stars", "Sort Stars", show=False),
        Binding("2", "sort_name", "Sort Name", show=False),
        Binding("3", "sort_language", "Sort Lang", show=False),
        Binding("4", "sort_starred_at", "Sort Date", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.tag_filter = None
        self.keyword = None
        self.sort_by = "starred_at"

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
                Static("", id="status_bar"),
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
            repos = repository.get_all_repositories(
                conn, tag_filter=self.tag_filter, keyword=self.keyword, sort_by=self.sort_by
            )
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
        self._update_status_bar()

    def _update_status_bar(self) -> None:
        """ステータスを表示する静的バーを更新します。"""
        sort_labels = {
            "stars": "⭐ Stars ▼",
            "name": "Name ▲",
            "language": "Language ▲",
            "starred_at": "Starred At ▼",
        }
        sort_label = sort_labels.get(self.sort_by, "")
        filter_label = f"Filter: {self.tag_filter}" if self.tag_filter else "Filter: [All]"
        table = self.query_one("#repo_table", DataTable)
        count_label = f"{table.row_count} items"
        
        parts = [f"Sort: {sort_label}", filter_label, count_label]
        self.query_one("#status_bar", Static).update(" | ".join(parts))

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

    # Vim-like Navigation
    def action_cursor_down(self) -> None:
        table = self.query_one("#repo_table", DataTable)
        if table.cursor_row < table.row_count - 1:
            table.move_cursor(row=table.cursor_row + 1)

    def action_cursor_up(self) -> None:
        table = self.query_one("#repo_table", DataTable)
        if table.cursor_row > 0:
            table.move_cursor(row=table.cursor_row - 1)

    def action_cursor_top(self) -> None:
        self.query_one("#repo_table", DataTable).move_cursor(row=0)

    def action_cursor_bottom(self) -> None:
        table = self.query_one("#repo_table", DataTable)
        if table.row_count > 0:
            table.move_cursor(row=table.row_count - 1)

    def action_page_down(self) -> None:
        table = self.query_one("#repo_table", DataTable)
        half = max(1, table.size.height // 2)
        new_row = min(table.cursor_row + half, table.row_count - 1)
        table.move_cursor(row=new_row)

    def action_page_up(self) -> None:
        table = self.query_one("#repo_table", DataTable)
        half = max(1, table.size.height // 2)
        new_row = max(0, table.cursor_row - half)
        table.move_cursor(row=new_row)

    def action_open_detail(self) -> None:
        table = self.query_one("#repo_table", DataTable)
        if table.row_count > 0:
            repo_id = table.coordinate_to_cell_key(Coordinate(table.cursor_row, 0)).row_key.value
            self.app.push_screen(DetailScreen(repo_id))

    # Sorting
    def action_sort_stars(self) -> None:
        self.sort_by = "stars"
        self.reload_table()

    def action_sort_name(self) -> None:
        self.sort_by = "name"
        self.reload_table()

    def action_sort_language(self) -> None:
        self.sort_by = "language"
        self.reload_table()

    def action_sort_starred_at(self) -> None:
        self.sort_by = "starred_at"
        self.reload_table()

    # Shuffle
    def action_shuffle_list(self) -> None:
        """リストをランダム順に並び替えて再描画する。"""
        app_config = self.app.app_config
        with get_db_connection(app_config.db_path) as conn:
            repos = repository.get_all_repositories(
                conn, tag_filter=self.tag_filter, keyword=self.keyword
            )
            random.shuffle(repos)
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
        self.query_one("#status_bar", Static).update("Sort: 🔀 Shuffled | " + (f"Filter: {self.tag_filter}" if self.tag_filter else "Filter: [All]") + f" | {table.row_count} items")
