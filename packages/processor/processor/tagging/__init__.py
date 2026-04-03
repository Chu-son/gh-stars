from .base import TaggerStrategy
from .rule_based import RuleBasedTagger

def create_tagger(mode: str, config) -> TaggerStrategy:
    """動作モードに応じて適切な TaggerStrategy を生成します。"""
    if mode == "llm":
        try:
            from .llm_tagger import LlmTagger
            return LlmTagger(
                endpoint=config.llm_endpoint,
                model=config.llm_model,
                db_path=config.db_path
            )
        except ImportError:
            return RuleBasedTagger(
                tags_config_path=config.tags_config_path,
                status_text="LLM (Missing Env -> Fallback)"
            )
    if mode == "ml":
        try:
            # scikit-learn がインストールされていない場合に備えた遅延インポート
            from .ml_tagger import MlTagger
            return MlTagger(model_path=config.ml_model_path, tags_config_path=config.tags_config_path)
        except ImportError:
            # フォールバック
            return RuleBasedTagger(
                tags_config_path=config.tags_config_path, 
                status_text="ML (Missing Env -> Fallback)"
            )
    # rule_based または不正なモードの場合はデフォルトで RuleBasedTagger
    return RuleBasedTagger(tags_config_path=config.tags_config_path)
