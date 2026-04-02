from .base import SimilaritySearchStrategy

def create_search(conn) -> SimilaritySearchStrategy:
    """類似リポジトリ検索のインスタンス化を行います。"""
    try:
        from .tfidf_search import TfidfSearch
        return TfidfSearch(conn)
    except ImportError:
        # scikit-learn がない場合のフォールバック（またはエラー、今回は単純化）
        return None
