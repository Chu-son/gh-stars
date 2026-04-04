from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, ListView, ListItem, Label, Static
from ..components.repo_item import RepoItem
from ..components.search_input import SearchInput
from textual.containers import Horizontal, Vertical, Container
from textual.binding import Binding
from textual.coordinate import Coordinate
from textual.message import Message
from textual import work
import random
from processor.database import repository
from processor.database.connection import get_db_connection
from .detail_screen import DetailScreen
from rich.text import Text
from rich.console import Group, RenderableType


class FilterItem(ListItem):
    """タグや言語のフィルタ用ListItem。"""
    def __init__(self, label: str, filter_value: str | None, filter_type: str):
        super().__init__(Label(label))
        self.filter_value = filter_value
        self.filter_type = filter_type # "all", "tag", "lang"

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
        self.language_filter = None
        self.sidebar_mode = "none"  # "none", "tags", "languages"
        self.keyword = None
        self.sort_by = "starred_at"
        self.sort_descending = True

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Vertical(
                Label("Tags", id="sidebar_title"),
                ListView(id="sidebar_list"),
                id="sidebar"
            ),
            Vertical(
                SearchInput(placeholder="Search by keyword...", id="search_bar"),
                ListView(id="repo_list"),
                Static("", id="status_bar"),
                id="content"
            )
        )
        yield Footer()

    async def on_mount(self) -> None:
        self.query_one("#sidebar").display = False
        await self.reload_data()

    async def reload_data(self) -> None:
        """データを再読み込みして表示を更新します。"""
        await self.reload_sidebar()
        self.reload_list()

    async def reload_sidebar(self) -> None:
        """現在のsidebar_modeに応じてサイドバーの中身を再構築します。"""
        if self.sidebar_mode == "none":
            return
            
        app_config = self.app.app_config
        sidebar_list = self.query_one("#sidebar_list", ListView)
        title = self.query_one("#sidebar_title", Label)
        
        # 現在の選択を保存
        current_filter = None
        if sidebar_list.highlighted_child and isinstance(sidebar_list.highlighted_child, FilterItem):
            current_filter = (sidebar_list.highlighted_child.filter_type, sidebar_list.highlighted_child.filter_value)

        await sidebar_list.clear()
        sidebar_list.append(FilterItem(" [All] ", None, "all"))
        
        with get_db_connection(app_config.db_path) as conn:
            if self.sidebar_mode == "tags":
                title.update("Tags")
                for tag in repository.get_all_tags(conn):
                    sidebar_list.append(FilterItem(f" {tag} ", tag, "tag"))
            elif self.sidebar_mode == "languages":
                title.update("Languages")
                for lang in repository.get_all_languages(conn):
                    sidebar_list.append(FilterItem(f" {lang} ", lang, "lang"))
        
        # 選択を復元
        if current_filter:
            for idx, child in enumerate(sidebar_list.children):
                if isinstance(child, FilterItem) and (child.filter_type, child.filter_value) == current_filter:
                    sidebar_list.index = idx
                    break

    def reload_list(self) -> None:
        """リポジトリ一覧のみを再構築します。"""
        app_config = self.app.app_config
        with get_db_connection(app_config.db_path) as conn:
            repos = repository.get_all_repositories(
                conn, 
                tag_filter=self.tag_filter, 
                language_filter=self.language_filter,
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
        repo_list = self.query_one("#repo_list", ListView)
        count_label = f"{len(repo_list.children)} items"
        
        filter_parts = []
        if self.tag_filter: filter_parts.append(f"Tag:{self.tag_filter}")
        if self.language_filter: filter_parts.append(f"Lang:{self.language_filter}")
        filter_label = f"Filter: {' & '.join(filter_parts)}" if filter_parts else "Filter: [All]"
        
        from processor.tagging import create_tagger
        tagger = create_tagger(self.app.app_config.tagger_mode, self.app.app_config)
        tagger_label = f"Tagger: {tagger.status_text}"
        
        parts = [f"Sort: {sort_label}", filter_label, count_label, tagger_label]
        self.query_one("#status_bar", Static).update(" | ".join(parts))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """リストが選択された時の処理。"""
        if event.list_view.id == "sidebar_list":
            item = event.item
            if isinstance(item, FilterItem):
                if item.filter_type == "all":
                    if self.sidebar_mode == "tags":
                        self.tag_filter = None
                    elif self.sidebar_mode == "languages":
                        self.language_filter = None
                elif item.filter_type == "tag":
                    self.tag_filter = item.filter_value
                elif item.filter_type == "lang":
                    self.language_filter = item.filter_value
                self.reload_list()
        elif event.list_view.id == "repo_list":
            if isinstance(event.item, RepoItem):
                self.app.push_screen(DetailScreen(event.item.repo["github_id"]))

    def on_input_changed(self, event: SearchInput.Changed) -> None:
        """検索ワードが変更された時の処理。"""
        if event.input.id == "search_bar":
            val = event.value
            if val and val.startswith("?"):
                # セマンティック検索の場合は入力中のインクリメンタル検索は行わない（Enter待ち）
                return
            self.keyword = val if val else None
            self.reload_list()

    @work(thread=True)
    def _do_semantic_search(self, query: str) -> None:
        """非同期にセマンティック検索を実行します。"""
        from processor.search import create_search
        search_engine = create_search(self.app.app_config.db_path, self.app.app_config.tagger_mode)
        if hasattr(search_engine, "find_similar_by_text"):
            repos = search_engine.find_similar_by_text(query)
            self.app.call_from_thread(self._update_repo_list_after_search, repos, query)
        else:
            self.app.call_from_thread(self.notify, "Semantic search is not supported in current mode.", severity="warning")

    def _update_repo_list_after_search(self, repos: list, query: str) -> None:
        """検索結果でリストを更新します。（メインスレッド用）"""
        repo_list = self.query_one("#repo_list", ListView)
        repo_list.clear()
        with get_db_connection(self.app.app_config.db_path) as conn:
            for repo in repos:
                repo["tags_list"] = repository.get_tags_for_repo(conn, repo["github_id"])
                repo_list.append(RepoItem(repo))
        self.query_one("#status_bar", Static).update(f"Sort: 🧠 Semantic Result | Search: {query} | {len(repos)} items")

    async def on_input_submitted(self, event: SearchInput.Submitted) -> None:
        """Enterキーが押された時の処理。自由文検索に使用。"""
        if event.input.id == "search_bar":
            val = event.value
            if val and val.startswith("?"):
                query = val[1:].strip()
                if not query:
                    return
                # 自由文検索を実行 (ワーカーにオフロード)
                self.notify(f"Semantic searching for: '{query}'...")
                self._do_semantic_search(query)

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
        """検索バーにフォーカスを当てます。/ キーで呼び出される想定です。"""
        search_input = self.query_one("#search_bar", SearchInput)
        search_input.can_focus = True
        search_input.focus()

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

    async def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar")
        if self.sidebar_mode == "none":
            self.sidebar_mode = "tags"
            sidebar.display = True
            await self.reload_sidebar()
        elif self.sidebar_mode == "tags":
            self.sidebar_mode = "languages"
            await self.reload_sidebar()
        else:
            self.sidebar_mode = "none"
            sidebar.display = False

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
