import webbrowser
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Markdown, Label, Static, Button, ListView
from textual.containers import Vertical, Horizontal, Container, VerticalScroll
from ..components.repo_item import RepoItem
from textual.binding import Binding
from processor.database import repository
from processor.database.connection import get_db_connection
from .tag_edit_modal import TagEditModal

class DetailScreen(Screen):
    """リポジトリの詳細情報を表示する画面。"""
    
    CSS = """
    #detail_content {
        padding: 2;
        background: $surface;
        height: 1fr;
    }
    #repo_markdown {
        height: auto;
        margin-bottom: 1;
    }
    #similar_section {
        height: auto;
        margin-top: 2;
        border-top: tall $accent;
    }
    #similar_list {
        height: auto;
        min-height: 5;
    }
    #actions {
        margin-top: 1;
        height: 3;
    }
    Button {
        margin-right: 2;
    }
    """

    BINDINGS = [
        Binding("h", "scroll_left", "Left", show=False),
        Binding("l", "scroll_right", "Right", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("g", "cursor_top", "Top", show=False),
        Binding("G", "cursor_bottom", "Bottom", show=False),
        Binding("escape", "go_back", "Back", show=False),
        Binding("o", "open_browser", "Open Browser", show=False),
        Binding("t", "edit_tags", "Edit Tags", show=False),
        Binding("ctrl+d", "page_down", "PgDn", show=False),
        Binding("ctrl+u", "page_up", "PgUp", show=False),
    ]

    def __init__(self, repo_id: str):
        super().__init__()
        self.repo_id = repo_id

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="detail_content"):
            yield Markdown(id="repo_markdown")
            with Vertical(id="similar_section"):
                yield Label("### Similar Repositories", id="similar_title")
                yield ListView(id="similar_list")
            with Horizontal(id="actions"):
                yield Button("Open in Browser (o)", id="open_btn", variant="primary")
                yield Button("Edit Tags (t)", id="edit_tags_btn")
                yield Button("Back (Esc)", id="back_btn")
        yield Footer()

    def on_mount(self) -> None:
        self.reload_data()

    def reload_data(self) -> None:
        app_config = self.app.app_config
        with get_db_connection(app_config.db_path) as conn:
            repo = repository.get_repository_by_id(conn, self.repo_id)
            if not repo:
                self.app.pop_screen()
                return
                
            tags = repository.get_tags_for_repo(conn, self.repo_id)
            
            md_content = f"""
# {repo['full_name']}

**Stars:** ⭐ {repo['stars']:,}  |  **Forks:** 🍴 {repo['forks']:,}  |  **Language:** {repo['primary_language'] or '-'}  |  **License:** {repo['license'] or '-'}

**Tags:** {", ".join([f"`{t}`" for t in tags])}

---

{repo['description'] or "*No description provided.*"}

---

**URL:** [{repo['url']}]({repo['url']})
**Starred at:** {repo['starred_at']}
"""
            # 類似リポジトリ表示を追加
            from processor.search import create_search
            searcher = create_search(
                app_config.db_path, 
                mode=app_config.tagger_mode, 
                conn=conn
            )
            
            similar_list = self.query_one("#similar_list", ListView)
            similar_list.clear()
            title = self.query_one("#similar_title", Label)
            
            if searcher:
                try:
                    similar = searcher.find_similar(self.repo_id, top_k=5)
                    if similar:
                        title.update("### Similar Repositories")
                        for r in similar:
                            # タグ情報も取得しておく
                            r["tags_list"] = repository.get_tags_for_repo(conn, r["github_id"])
                            similar_list.append(RepoItem(r))
                    else:
                        title.update("### Similar Repositories (None found)")
                except Exception as e:
                    title.update(f"### Similar Repositories (Error: {str(e)})")
            else:
                title.update("### Similar Repositories (ML dependency missing)")

            self.query_one("#repo_markdown", Markdown).update(md_content)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """類似リポジトリが選択されたらその詳細画面へ遷移する。"""
        if event.list_view.id == "similar_list":
            if isinstance(event.item, RepoItem):
                self.app.push_screen(DetailScreen(event.item.repo["github_id"]))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "open_btn":
            self.action_open_browser()
        elif event.button.id == "edit_tags_btn":
            self.action_edit_tags()
        elif event.button.id == "back_btn":
            self.app.pop_screen()

    def action_open_browser(self) -> None:
        app_config = self.app.app_config
        with get_db_connection(app_config.db_path) as conn:
            repo = repository.get_repository_by_id(conn, self.repo_id)
            if repo:
                webbrowser.open(repo["url"])
                self.notify(f"Opening {repo['url']}...")

    def action_edit_tags(self) -> None:
        self.app.push_screen(TagEditModal(self.repo_id), self.on_modal_close)

    def on_modal_close(self, result: bool) -> None:
        if result:
            self.reload_data()
            # メイン画面も更新が必要な可能性があるため、スタックを確認
            for screen in self.app.screen_stack:
                if hasattr(screen, "reload_data"):
                    screen.reload_data()

    def action_go_back(self) -> None:
        """メイン画面に戻ります。"""
        self.app.pop_screen()

    # Vim-like Navigation
    def action_cursor_down(self) -> None:
        self.query_one("#repo_markdown").scroll_relative(y=1)

    def action_cursor_up(self) -> None:
        self.query_one("#repo_markdown").scroll_relative(y=-1)

    def action_scroll_left(self) -> None:
        self.query_one("#repo_markdown").scroll_relative(x=-4)

    def action_scroll_right(self) -> None:
        self.query_one("#repo_markdown").scroll_relative(x=4)

    def action_cursor_top(self) -> None:
        self.query_one("#repo_markdown").scroll_to(y=0)

    def action_cursor_bottom(self) -> None:
        md = self.query_one("#repo_markdown")
        md.scroll_to(y=md.virtual_size.height)

    def action_page_down(self) -> None:
        md = self.query_one("#repo_markdown")
        md.scroll_relative(y=md.size.height // 2)

    def action_page_up(self) -> None:
        md = self.query_one("#repo_markdown")
        md.scroll_relative(y=-(md.size.height // 2))
