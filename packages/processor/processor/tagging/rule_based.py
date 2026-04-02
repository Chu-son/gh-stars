import yaml
from pathlib import Path
from .base import TaggerStrategy

class RuleBasedTagger(TaggerStrategy):
    """tags.yaml を読み込んでルールベースのタグ付けを行う。"""

    def __init__(self, tags_config_path: Path = Path("config/tags.yaml"), status_text: str = "Rule-Based"):
        self.rules: list[dict] = []
        self.default_tag: str = "other"
        self._status_text = status_text
        self._load_config(tags_config_path)

    @property
    def status_text(self) -> str:
        return self._status_text

    def _load_config(self, path: Path) -> None:
        """YAML設定ファイルを読み込む。ファイルが存在しない場合はデフォルトルールを使用。"""
        if not path.exists():
            self.rules = []
            self.default_tag = "other"
            return
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            if config:
                self.rules = config.get("rules", [])
                self.default_tag = config.get("default_tag", "other")

    def suggest_tags(self, repo: dict) -> list[str]:
        tags = set()
        lang = (repo.get("primary_language") or "").strip()
        description = (repo.get("description") or "").lower()
        topics = [t.lower() for t in (repo.get("topics") or [])]
        combined_text = description + " " + " ".join(topics)

        for rule in self.rules:
            tag = rule["tag"]
            match = rule.get("match", {})
            # 言語マッチ
            if "language" in match and lang in match["language"]:
                tags.add(tag)
            # キーワードマッチ
            if "keywords" in match:
                if any(kw in combined_text for kw in match["keywords"]):
                    tags.add(tag)

        if not tags:
            tags.add(self.default_tag)
        return sorted(list(tags))

    def learn(self, repo: dict, correct_tags: list[str]) -> None:
        # ルールベースは学習を行わない
        pass
