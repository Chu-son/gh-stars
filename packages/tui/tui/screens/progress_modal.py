from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import LoadingIndicator, Label
from textual.containers import Center, Vertical

class ProgressModal(ModalScreen):
    """同期や学習など、時間のかかる処理中に表示するプログレスモーダル。"""

    DEFAULT_CSS = """
    ProgressModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.5);
    }
    #modal_panel {
        width: 40;
        height: 10;
        background: $surface;
        border: thick $accent;
        align: center middle;
        padding: 1;
    }
    #loading_label {
        width: 100%;
        text-align: center;
        margin-bottom: 1;
    }
    """

    def __init__(self, message: str = "Processing..."):
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="modal_panel"):
            yield Label(self.message, id="loading_label")
            with Center():
                yield LoadingIndicator()
