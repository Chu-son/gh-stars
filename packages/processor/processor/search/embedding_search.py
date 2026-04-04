import json
import logging
import sqlite3
from typing import Any
import numpy as np
from .base import SimilaritySearchStrategy

logger = logging.getLogger(__name__)

class EmbeddingSearchStrategy(SimilaritySearchStrategy):
    """
    Sentence Transformers を用いた埋め込みベクトルベースの類似検索。
    sqlite-vec 仮想テーブルを利用して高速な検索を実現します。
    """

    def __init__(self, db_path: str, model_name: str = "all-MiniLM-L6-v2"):
        self.db_path = db_path
        self.model_name = model_name
        self._model = None # 遅延ロード

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def _get_text_for_repo(self, repo: dict) -> str:
        """リポジト描画情報からベクトル化対象のテキストを抽出します。"""
        full_name = repo.get("full_name") or ""
        description = repo.get("description") or ""
        topics = " ".join(repo.get("topics") or [])
        lang = repo.get("primary_language") or ""
        return f"{full_name} {lang} {topics} {description}".strip()

    def find_similar(self, repo_id: str, top_k: int = 10) -> list[dict]:
        """指定されたリポジトリ ID に類似するものを返します。"""
        try:
            from processor.database.connection import get_db_connection
            with get_db_connection(self.db_path) as conn:
                # 1. 指定 ID のベクトルを取得
                cursor = conn.execute("SELECT embedding FROM vec_repositories WHERE repo_id = ?", (repo_id,))
                row = cursor.fetchone()
                if not row:
                    logger.warning(f"Repository {repo_id} not indexed in vector table.")
                    return []
                
                embedding = row["embedding"]
                
                # 2. 近傍検索 (vec_distance_cosine を使用)
                # sqlite-vec においては vec_distance_cosine(embedding, ?) が小さいほど類似
                cursor = conn.execute("""
                    SELECT r.*, v.distance 
                    FROM vec_repositories v
                    JOIN repositories r ON v.repo_id = r.github_id
                    WHERE v.repo_id != ?
                      AND v.embedding MATCH ?
                      AND k = ?
                    ORDER BY distance
                """, (repo_id, embedding, top_k))
                
                # 注: 実際には sqlite-vec の MATCH 文法などはバージョン・設計により異なるため
                # ここでは一般的な距離計算ソートとして記述
                # 実際には以下のような形になる場合が多い (vec_distance_L2 など)
                cursor = conn.execute("""
                    SELECT r.*, vec_distance_cosine(v.embedding, ?) as distance
                    FROM vec_repositories v
                    JOIN repositories r ON v.repo_id = r.github_id
                    WHERE v.repo_id != ?
                    ORDER BY distance ASC
                    LIMIT ?
                """, (embedding, repo_id, top_k))
                
                return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error in find_similar: {e}")
            return []

    def find_similar_by_text(self, query_text: str, top_k: int = 10) -> list[dict]:
        """任意の文章から意味的に近いリポジトリを返します。"""
        try:
            # 1. 問い合わせ文をベクトル化
            query_embedding = self.model.encode(query_text, show_progress_bar=False).astype(np.float32).tobytes()
            
            from processor.database.connection import get_db_connection
            with get_db_connection(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT r.*, vec_distance_cosine(v.embedding, ?) as distance
                    FROM vec_repositories v
                    JOIN repositories r ON v.repo_id = r.github_id
                    ORDER BY distance ASC
                    LIMIT ?
                """, (query_embedding, top_k))
                
                return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error in find_similar_by_text: {e}")
            return []

    def rebuild_index(self) -> None:
        """全リポジトリを走査してベクトルインデックスを再構築します。"""
        print("Rebuilding vector index... This may take a while.")
        try:
            from processor.database.connection import get_db_connection
            with get_db_connection(self.db_path) as conn:
                # 全件取得
                cursor = conn.execute("SELECT * FROM repositories")
                repos = [dict(r) for r in cursor.fetchall()]
                
                if not repos:
                    print("No repositories found to index.")
                    return
                
                # 全文テキストの準備
                texts = [self._get_text_for_repo(r) for r in repos]
                
                # 一括エンコード
                print(f"Encoding {len(repos)} repositories...")
                embeddings = self.model.encode(texts, show_progress_bar=False)
                
                # DB に保存
                print("Saving embeddings to database...")
                conn.execute("DELETE FROM vec_repositories")
                for repo, embedding in zip(repos, embeddings):
                    # float32 のバイト列として保存
                    blob = embedding.astype(np.float32).tobytes()
                    conn.execute(
                        "INSERT INTO vec_repositories (repo_id, embedding) VALUES (?, ?)",
                        (repo["github_id"], blob)
                    )
                conn.commit()
                print("Vector index rebuild finished.")
        except Exception as e:
            logger.error(f"Error rebuilding vector index: {e}")
            print(f"Error: {e}")
