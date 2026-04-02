import os
import yaml
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

@dataclass
class AppConfig:
    github_pat: str
    db_path: Path
    tagger_mode: str
    llm_endpoint: str
    llm_model: str
    sync_page_size: int
    tags_config_path: Path
    ml_model_path: Path

def load_config(config_path: str = "config.yaml") -> AppConfig:
    """設定をロードします。優先順位: 環境変数 > .env > config.yaml"""
    # .env を読み込む
    load_dotenv()
    
    # デフォルト値
    config_dict = {
        "database": {"path": "./data/gh_favorite.db"},
        "tagger": {
            "mode": "rule_based",
            "tags_config_path": "config/tags.yaml",
            "llm_endpoint": "http://localhost:11434",
            "llm_model": "gemma3",
            "ml_model_path": "~/.local/share/gh_stars/ml_model.pkl"
        },
        "sync": {"page_size": 100}
    }
    
    # config.yaml があれば上書き
    if Path(config_path).exists():
        with open(config_path, "r") as f:
            yaml_config = yaml.safe_load(f)
            if yaml_config:
                # 深いマージ（簡易版）
                for key in ["database", "tagger", "sync"]:
                    if key in yaml_config:
                        config_dict[key].update(yaml_config[key])

    # 環境変数での最終上書き
    pat = os.getenv("GITHUB_PAT")
    if not pat:
        # 開発中のテスト用。本来はエラーにするか入力を促す。
        pat = ""
        
    return AppConfig(
        github_pat=pat,
        db_path=Path(config_dict["database"]["path"]),
        tagger_mode=config_dict["tagger"]["mode"],
        llm_endpoint=config_dict["tagger"]["llm_endpoint"],
        llm_model=config_dict["tagger"]["llm_model"],
        sync_page_size=config_dict["sync"]["page_size"],
        tags_config_path=Path(config_dict["tagger"]["tags_config_path"]),
        ml_model_path=Path(config_dict["tagger"]["ml_model_path"]).expanduser()
    )
