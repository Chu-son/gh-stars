from textual.widgets import ListItem
from rich.text import Text
from rich.console import Group, RenderableType

class RepoItem(ListItem):
    """リポジトリ情報を表示するための共通 ListItem コンポーネント。"""
    
    def __init__(self, repo: dict):
        super().__init__()
        self.repo = repo

    def render(self) -> RenderableType:
        """Rich を使用してリポジトリの要約情報を描画します。"""
        # Line 1: Stars | Repo Name [Language]
        title_text = Text(f"⭐ {self.repo['stars']} | {self.repo['full_name']}", style="bold cyan")
        if self.repo.get('primary_language'):
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
