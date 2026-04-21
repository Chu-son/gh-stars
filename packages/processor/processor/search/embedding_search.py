"""Sentence Transformers を用いた埋め込みベクトルベースの類似検索。

sqlite-vec 拡張ではなく Python (numpy) によるインメモリ計算を使用する。
TfidfSearch と同様に全件ロード→メモリ上でコサイン類似度計算を行うアプローチ。
"""
import logging
import numpy as np
from .base import SimilaritySearchStrategy

logger = logging.getLogger(__name__)


class EmbeddingSearchStrategy(SimilaritySearchStrategy):
    """Sentence Transformers を用いた埋め込みベクトルベースの類似検索。

    初回 find_similar() 呼び出し時に DB から全埋め込みをメモリにロードし、
    numpy によるコサイン類似度計算で上位 k 件を返す。
    """

    def __init__(self, db_path: str, model_name: str = "all-MiniLM-L6-v2"):
        self.db_path = db_path
        self.model_name = model_name
        self._model = None  # 遅延ロード

        # インメモリキャッシュ (TfidfSearch と同アプローチ)
        self._embeddings: np.ndarray | None = None  # shape: (N, D)
        self._repo_list: list[dict] = []
        self._repo_id_to_idx: dict[str, int] = {}

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def _get_text_for_repo(self, repo: dict) -> str:
        """リポジトリ情報からベクトル化対象のテキストを抽出します。"""
        full_name = repo.get("full_name") or ""
        description = repo.get("description") or ""
        topics_raw = repo.get("topics") or []
        if isinstance(topics_raw, str):
            import json
            try:
                topics_raw = json.loads(topics_raw)
            except (json.JSONDecodeError, TypeError):
                topics_raw = []
        topics = " ".join(topics_raw)
        lang = repo.get("primary_language") or ""
        return f"{full_name} {lang} {topics} {description}".strip()

    def _load_index(self) -> None:
        """DB から embedding をロードしてメモリにキャッシュします。"""
        try:
            from processor.database.connection import get_db_connection

            # embedding データを取得
            with get_db_connection(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT repo_id, embedding FROM vec_repositories"
                )
                rows = cursor.fetchall()

            if not rows:
                logger.info("vec_repositories is empty. Run --rebuild-vec first.")
                return

            embeddings = []
            repo_ids = []
            for row in rows:
                repo_id = row["repo_id"] if isinstance(row, dict) else row[0]
                blob = row["embedding"] if isinstance(row, dict) else row[1]
                if blob is None:
                    continue
                vec = np.frombuffer(blob, dtype=np.float32).copy()
                embeddings.append(vec)
                repo_ids.append(repo_id)

            if not embeddings:
                return

            self._embeddings = np.stack(embeddings)  # (N, D)
            self._repo_id_to_idx = {rid: i for i, rid in enumerate(repo_ids)}

            # リポジトリ情報も取得 (github_id → dict)
            with get_db_connection(self.db_path) as conn:
                cursor = conn.execute("SELECT * FROM repositories")
                all_repos = {
                    (row["github_id"] if isinstance(row, dict) else row[0]): dict(row)
                    for row in cursor.fetchall()
                }

            self._repo_list = [
                all_repos.get(rid, {"github_id": rid}) for rid in repo_ids
            ]
            logger.info("Embedding index loaded: %d vectors", len(self._repo_list))

        except Exception as e:
            logger.error("Failed to load embedding index: %s", e)

    def _cosine_similarity(
        self, vec_a: np.ndarray, matrix: np.ndarray
    ) -> np.ndarray:
        """ベクトルと行列の各行とのコサイン類似度を計算します。"""
        vec_a_norm = vec_a / (np.linalg.norm(vec_a) + 1e-8)
        matrix_norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-8
        matrix_normalized = matrix / matrix_norms
        return matrix_normalized @ vec_a_norm  # shape: (N,)

    def find_similar(self, repo_id: str, top_k: int = 10) -> list[dict]:
        """指定されたリポジトリ ID に類似するものを返します。"""
        if self._embeddings is None:
            self._load_index()
        if self._embeddings is None or len(self._embeddings) == 0:
            return []

        idx = self._repo_id_to_idx.get(repo_id)
        if idx is None:
            logger.warning("Repository %s is not indexed. Run --rebuild-vec.", repo_id)
            return []

        query_vec = self._embeddings[idx]
        similarities = self._cosine_similarity(query_vec, self._embeddings)

        # 類似度の高い順にソートし、自分自身を除いて top_k 件返す
        sorted_indices = similarities.argsort()[::-1]
        results = []
        for i in sorted_indices:
            if int(i) != idx:
                results.append(self._repo_list[int(i)])
                if len(results) >= top_k:
                    break
        return results

    def find_similar_by_text(self, query_text: str, top_k: int = 10) -> list[dict]:
        """任意の文章から意味的に近いリポジトリを返します。"""
        if self._embeddings is None:
            self._load_index()
        if self._embeddings is None or len(self._embeddings) == 0:
            return []

        try:
            query_vec = (
                self.model.encode(query_text, show_progress_bar=False)
                .astype(np.float32)
            )
            similarities = self._cosine_similarity(query_vec, self._embeddings)
            sorted_indices = similarities.argsort()[-top_k:][::-1]
            return [self._repo_list[int(i)] for i in sorted_indices]
        except Exception as e:
            logger.error("Error in find_similar_by_text: %s", e)
            return []

    def rebuild_index(self) -> None:
        """全リポジトリを走査してベクトルインデックスを再構築します。

        DB の vec_repositories テーブルに embedding (BLOB) を保存し、
        메モリキャッシュも同時に更新します。
        """
        print("Rebuilding vector index... This may take a while.")
        try:
            from processor.database.connection import get_db_connection

            with get_db_connection(self.db_path) as conn:
                cursor = conn.execute("SELECT * FROM repositories")
                repos = [dict(r) for r in cursor.fetchall()]

            if not repos:
                print("No repositories found to index.")
                return

            texts = [self._get_text_for_repo(r) for r in repos]

            print(f"Encoding {len(repos)} repositories...")
            embeddings = self.model.encode(texts, show_progress_bar=False)

            print("Saving embeddings to database...")
            with get_db_connection(self.db_path) as conn:
                conn.execute("DELETE FROM vec_repositories")
                for repo, embed in zip(repos, embeddings):
                    blob = embed.astype(np.float32).tobytes()
                    conn.execute(
                        "INSERT INTO vec_repositories (repo_id, embedding) VALUES (?, ?)",
                        (repo["github_id"], blob),
                    )
                conn.commit()

            # メモリキャッシュを更新
            self._embeddings = embeddings.astype(np.float32)
            self._repo_list = repos
            self._repo_id_to_idx = {
                r["github_id"]: i for i, r in enumerate(repos)
            }
            print(f"Vector index rebuild finished. {len(repos)} repositories indexed.")

        except Exception as e:
            logger.error("Error rebuilding vector index: %s", e)
            print(f"Error: {e}")
