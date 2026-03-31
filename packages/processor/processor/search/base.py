from abc import ABC, abstractmethod

class SimilaritySearchStrategy(ABC):
    """類似リポジトリ検索の基底クラス。"""

    @abstractmethod
    def find_similar(self, repo_id: str, top_k: int = 10) -> list[dict]:
        """
        指定したリポジトリに類似するリポジトリを検索します。
        
        Args:
            repo_id (str): 基準となるリポジトリのgithub_id
            top_k (int): 取得件数
        
        Returns:
            list[dict]: 類似リポジトリ情報のリスト
        """
        pass

    @abstractmethod
    def rebuild_index(self) -> None:
        """キャッシュや検索用インデックスを再構築します。"""
        pass
