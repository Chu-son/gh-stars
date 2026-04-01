from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, ListView, ListItem, Input, Label, Static
from textual.containers import Horizontal, Vertical, Container
from textual.binding import Binding
from textual.coordinate import Coordinate
from textual.message import Message
import random
from processor.database import repository
from processor.database.connection import get_db_connection
from .detail_screen import DetailScreen
from rich.text import Text
from rich.console import Group, RenderableType

class RepoItem(ListItem):
    """Custom ListItem to display repository information efficiently in one DOM node."""
    
    def __init__(self, repo: dict):
        super().__init__()
        self.repo = repo

    def render(self) -> RenderableType:
        """Render the item using Rich for maximum performance."""
        # Line 1: Stars | Repo Name [Language]
        title_text = Text(f"⭐ {self.repo['stars']} | {self.repo['full_name']}", style="bold cyan")
        if self.repo['primary_language']:
            title_text.append(f" [{self.repo['primary_language']}]", style="green")
        
        renderables = [title_text]
        
        # Line 2: Tags
        tags = self.repo.get("tags_list", [])
        if tags:
            renderables.append(Text(f"Tags: {', '.join(tags)}", style="italic dim"))
            
        # Line 3: Description
        desc = self.repo.get("description", "")
        if desc:
            renderables.append(Text(desc))
            
        return Group(*renderables)

    DEFAULT_CSS = """
    RepoItem {
        padding: 1;
        border-bottom: solid $accent;
        height: auto;
    }
    """

class MainScreen(Screen):
    """リポジトリ一覧表示画面。"""
    
    CSS = """
    #sidebar {
        width: 18%;
        border-right: solid $accent;
    }
    #content {
        width: 1fr;
    }
    #search_bar {
        margin: 1;
    }
    #repo_list {
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
        Binding("h", "scroll_left", "Left", show=False),
        Binding("l", "scroll_right", "Right", show=False),
        Binding("g", "cursor_top", "Top", show=False),
        Binding("G", "cursor_bottom", "Bottom", show=False),
        Binding("b", "toggle_sidebar", "Sidebar", show=False),
        Binding("enter", "open_detail", "Open", show=False),
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
        self.sort_descending = True

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
                ListView(id="repo_list"),
                Static("", id="status_bar"),
                id="content"
            )
        )
        yield Footer()

    async def on_mount(self) -> None:
        await self.reload_data()

    async def reload_data(self) -> None:
        """データを再読み込みして表示を更新します。"""
        await self.reload_tags()
        self.reload_list()

    async def reload_tags(self) -> None:
        """タグ一覧のみを再構築します。"""
        app_config = self.app.app_config
        with get_db_connection(app_config.db_path) as conn:
            tag_list = self.query_one("#tag_list", ListView)
            # 現在の選択を保存
            current_id = None
            if tag_list.highlighted_child:
                current_id = tag_list.highlighted_child.id

            await tag_list.clear()
            tag_list.append(ListItem(Label(" [All] "), id="tag_all"))
            for tag in repository.get_all_tags(conn):
                tag_list.append(ListItem(Label(f" {tag} "), id=f"tag_{tag}"))
            
            # 選択を復元
            if current_id:
                for idx, child in enumerate(tag_list.children):
                    if child.id == current_id:
                        tag_list.index = idx
                        break

    def reload_list(self) -> None:
        """リポジトリ一覧のみを再構築します。"""
        app_config = self.app.app_config
        with get_db_connection(app_config.db_path) as conn:
            repos = repository.get_all_repositories(
                conn, 
                tag_filter=self.tag_filter, 
                keyword=self.keyword, 
                sort_by=self.sort_by,
                sort_descending=self.sort_descending
            )
            repo_list = self.query_one("#repo_list", ListView)
            repo_list.clear()
            for repo in repos:
                repo["tags_list"] = repository.get_tags_for_repo(conn, repo["github_id"])
                repo_list.append(RepoItem(repo))
        self._update_status_bar()

    def _update_status_bar(self) -> None:
        """ステータスを表示する静的バーを更新します。"""
        sort_names = {
            "stars": "⭐ Stars",
            "name": "Name",
            "language": "Language",
            "starred_at": "Starred At",
        }
        direction = "▼" if self.sort_descending else "▲"
        sort_label = f"{sort_names.get(self.sort_by, '')} {direction}"
        filter_label = f"Filter: {self.tag_filter}" if self.tag_filter else "Filter: [All]"
        
        repo_list = self.query_one("#repo_list", ListView)
        count_label = f"{len(repo_list.children)} items"
        
        parts = [f"Sort: {sort_label}", filter_label, count_label]
        self.query_one("#status_bar", Static).update(" | ".join(parts))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """リストが選択された時の処理。"""
        if event.list_view.id == "tag_list":
            if event.item.id == "tag_all":
                self.tag_filter = None
            else:
                self.tag_filter = event.item.id.replace("tag_", "")
            self.reload_list()
        elif event.list_view.id == "repo_list":
            if isinstance(event.item, RepoItem):
                self.app.push_screen(DetailScreen(event.item.repo["github_id"]))

    def on_input_changed(self, event: Input.Changed) -> None:
        """検索ワードが変更された時の処理。"""
        if event.input.id == "search_bar":
            self.keyword = event.value if event.value else None
            self.reload_list()

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
        if self.focused:
            self.focused.action_cursor_down()

    def action_cursor_up(self) -> None:
        if self.focused:
            self.focused.action_cursor_up()

    def action_scroll_left(self) -> None:
        if self.focused:
            self.focused.scroll_relative(x=-4)

    def action_scroll_right(self) -> None:
        if self.focused:
            self.focused.scroll_relative(x=4)

    def action_cursor_top(self) -> None:
        if self.focused:
            if hasattr(self.focused, "index"):
                self.focused.index = 0
            else:
                self.focused.scroll_to(y=0)

    def action_cursor_bottom(self) -> None:
        if self.focused:
            if isinstance(self.focused, ListView):
                self.focused.index = len(self.focused.children) - 1
            else:
                self.focused.scroll_to(y=self.focused.virtual_size.height)

    def action_page_down(self) -> None:
        if self.focused:
            self.focused.scroll_relative(y=self.focused.size.height // 2)

    def action_page_up(self) -> None:
        if self.focused:
            self.focused.scroll_relative(y=-(self.focused.size.height // 2))

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar")
        sidebar.display = not sidebar.display

    def action_open_detail(self) -> None:
        repo_list = self.query_one("#repo_list", ListView)
        if repo_list.highlighted_child and isinstance(repo_list.highlighted_child, RepoItem):
            self.app.push_screen(DetailScreen(repo_list.highlighted_child.repo["github_id"]))

    # Sorting
    def _toggle_sort(self, sort_by: str) -> None:
        if self.sort_by == sort_by:
            self.sort_descending = not self.sort_descending
        else:
            self.sort_by = sort_by
            # デフォルトの方向（スターと日時は降順、名前と言語は昇順）
            self.sort_descending = sort_by in ["stars", "starred_at"]
        self.reload_list()

    def action_sort_stars(self) -> None:
        self._toggle_sort("stars")

    def action_sort_name(self) -> None:
        self._toggle_sort("name")

    def action_sort_language(self) -> None:
        self._toggle_sort("language")

    def action_sort_starred_at(self) -> None:
        self._toggle_sort("starred_at")

    # Shuffle
    def action_shuffle_list(self) -> None:
        """リストをランダム順に並び替えて再描画する。"""
        app_config = self.app.app_config
        with get_db_connection(app_config.db_path) as conn:
            repos = repository.get_all_repositories(
                conn, tag_filter=self.tag_filter, keyword=self.keyword
            )
            random.shuffle(repos)
            repo_list = self.query_one("#repo_list", ListView)
            repo_list.clear()
            for repo in repos:
                repo["tags_list"] = repository.get_tags_for_repo(conn, repo["github_id"])
                repo_list.append(RepoItem(repo))
        self.query_one("#status_bar", Static).update("Sort: 🔀 Shuffled | " + (f"Filter: {self.tag_filter}" if self.tag_filter else "Filter: [All]") + f" | {len(repo_list.children)} items")
