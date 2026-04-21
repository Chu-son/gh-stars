import logging
from .base import SimilaritySearchStrategy

logger = logging.getLogger(__name__)

def create_search(db_path: str, mode: str = "rule_based", **kwargs) -> SimilaritySearchStrategy:
    """動作モードに応じて適切な SimilaritySearchStrategy を生成します。

    Args:
        db_path: データベースパス (str)。configure_backend() 設定済みの場合は任意。
        mode: "llm" でベクトル検索、それ以外は TF-IDF。

    Returns:
        SimilaritySearchStrategy のインスタンス。
    """
    db_path_str = str(db_path) if db_path is not None else ""

    if mode == "llm":
        try:
            from .embedding_search import EmbeddingSearchStrategy
            return EmbeddingSearchStrategy(db_path=db_path_str)
        except ImportError:
            logger.warning("LLM search requested but dependencies missing. Falling back to TF-IDF.")

    try:
        from .tfidf_search import TfidfSearch
        return TfidfSearch(db_path=db_path_str)
    except (ImportError, Exception) as e:
        logger.error("Failed to create search engine: %s", e)
        return None
