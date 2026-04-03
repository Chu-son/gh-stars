from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .base import SimilaritySearchStrategy
from processor.database.repository import get_all_repositories_for_retagging

class TfidfSearch(SimilaritySearchStrategy):
    """TF-IDF とコサイン類似度を用いた類似リポジトリ検索。"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.tfidf_matrix = None
        # リポジトリ情報のリスト (インデックスによる引き当て用)
        self.repo_list = []
        # github_id -> idx のマッピング
        self.repo_id_to_idx = {}

    def rebuild_index(self) -> None:
        """データベースから全件読み込んでインデックスを構築します。"""
        from processor.database.connection import get_db_connection
        with get_db_connection(self.db_path) as conn:
            # repository.py の get_all_repositories_for_retagging を使用
            # (すでに topics が JSON デコードされているため)
            self.repo_list = get_all_repositories_for_retagging(conn)
        texts = []
        self.repo_id_to_idx = {}
        
        for idx, repo in enumerate(self.repo_list):
            self.repo_id_to_idx[repo["github_id"]] = idx
            desc = repo.get("description") or ""
            topics = repo.get("topics") or []
            lang = repo.get("primary_language") or ""
            # スペース区切りで結合
            texts.append(f"{lang} {desc} {' '.join(topics)}".lower())
        
        if texts:
            try:
                self.tfidf_matrix = self.vectorizer.fit_transform(texts)
            except Exception:
                # 語彙が空（すべてのリポジトリに説明等がない）場合など
                self.tfidf_matrix = None

    def find_similar(self, repo_id: str, top_k: int = 5) -> list[dict]:
        """指定したリポジトリに類似するものを検索します。"""
        if self.tfidf_matrix is None or not self.repo_id_to_idx:
            self.rebuild_index()
            
        if self.tfidf_matrix is None:
            return []

        idx = self.repo_id_to_idx.get(repo_id)
        if idx is None:
            return []

        target_vec = self.tfidf_matrix[idx]
        # コサイン類似度を計算
        similarities = cosine_similarity(target_vec, self.tfidf_matrix).flatten()
        
        # 値の大きい順にインデックスをソート (自分自身も含まれる)
        # top_k + 1 個取得 (自分自身が 1 位になるため)
        top_indices = similarities.argsort()[-(top_k + 1):][::-1]
        
        results = []
        for i in top_indices:
            if i != idx: # 自分自身は除外
                results.append(self.repo_list[i])
                if len(results) >= top_k:
                    break
        return results
