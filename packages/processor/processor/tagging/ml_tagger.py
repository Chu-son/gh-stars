import pickle
from pathlib import Path
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.linear_model import SGDClassifier
from .base import TaggerStrategy
from .rule_based import RuleBasedTagger

class MlTagger(TaggerStrategy):
    """scikit-learn を用いたオンライン学習ベースのタガー。"""

    def __init__(self, model_path: Path, tags_config_path: Path):
        self.model_path = model_path
        self.fallback = RuleBasedTagger(tags_config_path)
        # オンライン学習に適した HashingVectorizer を使用
        self.vectorizer = HashingVectorizer(n_features=2**16)
        self.classifiers: dict[str, SGDClassifier] = {}  # tag_name -> classifier
        self._load_model()

    @property
    def status_text(self) -> str:
        """現在のMLタガーの状態を返します。"""
        if not self.classifiers:
            return "ML (Untrained)"
        return f"ML (Active: {len(self.classifiers)} tags)"

    def _load_model(self) -> None:
        """モデルをディスクからロードします。"""
        if self.model_path.exists():
            try:
                with open(self.model_path, "rb") as f:
                    self.classifiers = pickle.load(f)
            except Exception:
                # ロード失敗時は空で初期化
                self.classifiers = {}

    def _save_model(self) -> None:
        """モデルをディスクに保存します。"""
        try:
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.model_path, "wb") as f:
                pickle.dump(self.classifiers, f)
        except Exception:
            # 保存失敗は無視（またはログ出力）
            pass

    def _extract_text(self, repo: dict) -> str:
        """リポジトリ情報から特徴量として使用するテキストを抽出します。"""
        desc = repo.get("description") or ""
        topics = repo.get("topics") or []
        if isinstance(topics, list):
            topics_str = " ".join(topics)
        else:
            topics_str = str(topics)
        lang = repo.get("primary_language") or ""
        return f"{lang} {desc} {topics_str}".lower()

    def suggest_tags(self, repo: dict) -> list[str]:
        # モデルが一つも学習されていない場合はルールベースにフォールバック
        if not self.classifiers:
            return self.fallback.suggest_tags(repo)

        X = self.vectorizer.transform([self._extract_text(repo)])
        suggested = []
        
        for tag, clf in self.classifiers.items():
            # partial_fit が少なくとも一度呼ばれている（classes_ がある）か確認
            if hasattr(clf, "classes_") and len(clf.classes_) >= 2:
                pred = clf.predict(X)[0]
                if pred == 1:
                    suggested.append(tag)
        
        # 何も提案されなかった場合は 'other'
        if not suggested:
            return [self.fallback.default_tag]
            
        return sorted(list(set(suggested)))

    def learn(self, repo: dict, correct_tags: list[str]) -> None:
        """正解のタグ情報を用いてモデルを更新します。"""
        text = self._extract_text(repo)
        X = self.vectorizer.transform([text])
        
        # 今回の正解タグと、これまでに学習したことがあるタグの総和
        target_tags = set(self.classifiers.keys()).union(set(correct_tags))
        
        for tag in target_tags:
            if tag not in self.classifiers:
                # オンライン学習に適した SGDClassifier (ロジスティック回帰形式)
                self.classifiers[tag] = SGDClassifier(loss="log_loss", random_state=42)
            
            # このタグが付与されているかどうかの二値ラベル
            y = [1 if tag in correct_tags else 0]
            # classes を明示的に指定してオンライン学習
            self.classifiers[tag].partial_fit(X, y, classes=[0, 1])
        
        self._save_model()
