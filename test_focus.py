from textual.app import App
from textual.widgets import Input, Button
from textual.containers import Vertical

class TestApp(App):
    def compose(self):
        yield Vertical(
            Input(id="in"),
            Button("b1", id="b1"),
            Button("b2", id="b2")
        )
    
    def on_mount(self):
        # Prevent tab focus by overriding focus method? Or just intercepting keys.
        pass
