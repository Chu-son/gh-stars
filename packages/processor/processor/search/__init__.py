import sqlite3
import logging
from .base import SimilaritySearchStrategy

logger = logging.getLogger(__name__)

def create_search(db_path: str | sqlite3.Connection, mode: str = "rule_based", **kwargs) -> SimilaritySearchStrategy:
    """動作モードに応じて適切な SimilaritySearchStrategy を生成します。"""
    # 引数の正規化: db_path にコネクションが渡されている場合
    if isinstance(db_path, sqlite3.Connection):
        # connection.py で付与している可能性があるパスを取得、なければ適当な名称
        db_path = getattr(db_path, "db_path", "data/gh_favorite.db")
    
    if mode == "llm":
        try:
            from .embedding_search import EmbeddingSearchStrategy
            return EmbeddingSearchStrategy(db_path=str(db_path))
        except ImportError:
            logger.warning("LLM search requested but dependencies missing. Falling back to TF-IDF.")
    
    try:
        from .tfidf_search import TfidfSearch
        return TfidfSearch(db_path=str(db_path))
    except (ImportError, Exception) as e:
        logger.error(f"Failed to create search engine: {e}")
        return None
