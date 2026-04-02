from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, DataTable, Button
from textual.containers import Vertical, Center

class HelpModal(ModalScreen):
    """キーマップ（ショートカットキー）の一覧を表示するヘルプ画面。"""

    DEFAULT_CSS = """
    HelpModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.5);
    }
    #help_panel {
        width: 60;
        height: 35;
        background: $surface;
        border: thick $accent;
        padding: 1;
    }
    #help_title {
        width: 100%;
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    DataTable {
        height: 1fr;
        border: none;
    }
    #close_help_btn {
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="help_panel"):
            yield Label("Keyboard Shortcuts", id="help_title")
            yield DataTable(id="help_table")
            with Center():
                yield Button("Close (Esc)", id="close_help_btn", variant="primary")

    def on_mount(self) -> None:
        table = self.query_one("#help_table", DataTable)
        table.add_columns("Key", "Action")
        table.cursor_type = "row"
        
        shortcuts = [
            ("q", "Quit Application"),
            ("s", "Incremental Sync"),
            ("S", "Full Sync (Sync All)"),
            ("U", "Re-tag all (Local updates)"),
            ("?", "Show this Help"),
            ("/", "Focus Search Bar"),
            ("o", "Open in Browser"),
            ("t", "Edit Tags"),
            ("r", "Pick Random Repo"),
            ("R", "Shuffle current list"),
            ("j / k", "Move Up / Down"),
            ("b", "Toggle Sidebar Mode"),
            ("Esc", "Go Back"),
            ("Enter", "Open Details"),
        ]
        
        for key, description in shortcuts:
            table.add_row(key, description)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close_help_btn":
            self.dismiss()
    
    def key_escape(self) -> None:
        self.dismiss()
