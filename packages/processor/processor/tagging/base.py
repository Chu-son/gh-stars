from abc import ABC, abstractmethod

class TaggerStrategy(ABC):
    """タグ付けアルゴリズムの基底クラス。"""

    @abstractmethod
    def suggest_tags(self, repo: dict) -> list[str]:
        """
        リポジトリ情報から推奨タグのリストを返します。
        
        Args:
            repo (dict): リポジトリ情報の辞書
        
        Returns:
            list[str]: タグ名のリスト
        """
        pass

    @abstractmethod
    def learn(self, repo: dict, correct_tags: list[str]) -> None:
        """
        正解のタグ情報を元に学習（フィードバック）を行います。
        
        Args:
            repo (dict): リポジトリ情報の辞書
            correct_tags (list[str]): 正解のタグ名リスト
        """
        pass
    @property
    @abstractmethod
    def status_text(self) -> str:
        """現在のタガーの状態を示す文字列を返します。"""
        pass
