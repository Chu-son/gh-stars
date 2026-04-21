from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Button, Checkbox, Input, Static
from textual.containers import Vertical, Horizontal, Grid
from processor.database import repository
from processor.database.connection import get_db_connection
from textual.binding import Binding

class TagEditModal(ModalScreen[bool]):
    """タグを編集するためのモーダル画面。"""
    
    CSS = """
    TagEditModal {
        align: center middle;
    }
    #modal_container {
        width: 60;
        height: 40;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    #tag_grid {
        grid-size: 2;
        grid-columns: 1fr 1fr;
        height: 20;
        overflow-y: scroll;
        margin: 1 0;
    }
    #add_tag_row {
        height: 3;
        margin: 1 0;
    }
    #add_tag_input {
        width: 30;
    }
    #footer_actions {
        align: right middle;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss_false", "Cancel", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("h", "scroll_left", "Left", show=False),
        Binding("l", "scroll_right", "Right", show=False),
    ]

    def __init__(self, repo_id: str):
        super().__init__()
        self.repo_id = repo_id
        self.selected_tags = set()

    def compose(self) -> ComposeResult:
        with Vertical(id="modal_container"):
            yield Label("Edit Tags", id="modal_title")
            with Vertical(id="tag_grid_container"):
                yield Grid(id="tag_grid")
            with Horizontal(id="add_tag_row"):
                yield Input(placeholder="Add new tag...", id="add_tag_input")
                yield Button("Add", id="add_tag_btn")
            with Horizontal(id="footer_actions"):
                yield Button("Save", variant="primary", id="save_btn")
                yield Button("Cancel", id="cancel_btn")

    def on_mount(self) -> None:
        self.load_tags()

    def load_tags(self) -> None:
        app_config = self.app.app_config
        with get_db_connection(app_config.db_path) as conn:
            all_tags = repository.get_all_tags(conn)
            repo_tags = repository.get_tags_for_repo(conn, self.repo_id)
            self.selected_tags = set(repo_tags)
            
            grid = self.query_one("#tag_grid", Grid)
            grid.remove_children()
            for tag in all_tags:
                checkbox = Checkbox(tag, value=(tag in self.selected_tags), id=f"check_{tag}")
                grid.mount(checkbox)

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        tag_name = str(event.checkbox.label)
        if event.value:
            self.selected_tags.add(tag_name)
        else:
            self.selected_tags.discard(tag_name)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add_tag_btn":
            self.add_new_tag()
        elif event.button.id == "save_btn":
            self.save_and_close()
        elif event.button.id == "cancel_btn":
            self.dismiss(False)

    def add_new_tag(self) -> None:
        input_widget = self.query_one("#add_tag_input", Input)
        new_tag = input_widget.value.strip()
        if new_tag:
            self.selected_tags.add(new_tag)
            # グリッドに追加（既に存在しない場合のみ）
            grid = self.query_one("#tag_grid", Grid)
            existing = [str(c.label) for c in grid.query(Checkbox)]
            if new_tag not in existing:
                grid.mount(Checkbox(new_tag, value=True, id=f"check_{new_tag}"))
            input_widget.value = ""

    def save_and_close(self) -> None:
        app_config = self.app.app_config
        final_tags = list(self.selected_tags)

        with get_db_connection(app_config.db_path) as conn:
            # 既存の全タグと比較して差分を記録する等のこだわりも可能だが、
            # 今回は repository.py の方針に従い manual ソースで一括更新
            repository.set_tags_for_repo(conn, self.repo_id, final_tags, source='manual')

            # ML モードの場合は学習を回す
            if app_config.tagger_mode == "ml":
                from processor.tagging import create_tagger
                repo = repository.get_repository_by_id(conn, self.repo_id)
                if repo:
                    tagger = create_tagger(app_config.tagger_mode, app_config)
                    tagger.learn(repo, final_tags)

            conn.commit()

        # キャッシュモード時: タグをリモートDBへ即時反映 (後勝ち + 競合ログ出力)
        cache_sync = getattr(self.app, "cache_sync", None)
        if cache_sync is not None and cache_sync.is_remote_available():
            cache_sync.push_tags(self.repo_id, final_tags, source="manual")

        self.dismiss(True)

    def action_dismiss_false(self) -> None:
        self.dismiss(False)

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
