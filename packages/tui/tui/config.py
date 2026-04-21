import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv


@dataclass
class AppConfig:
    # ---- 既存フィールド ----
    github_pat: str
    db_path: Path           # SQLite バックエンド時のパス (またはキャッシュDB)
    tagger_mode: str
    llm_endpoint: str
    llm_model: str
    sync_page_size: int
    tags_config_path: Path
    ml_model_path: Path

    # ---- DBバックエンド設定 (デフォルト: sqlite) ----
    db_backend: str = "sqlite"      # "sqlite" | "mariadb"

    # ---- MariaDB接続情報 (db_backend == "mariadb" の場合に使用) ----
    mariadb_host: str = "localhost"
    mariadb_port: int = 3306
    mariadb_user: str = ""
    mariadb_password: str = ""
    mariadb_database: str = "gh_stars"

    # ---- ローカルキャッシュ設定 (db_backend == "mariadb" かつ cache.enabled == true の場合) ----
    cache_enabled: bool = False
    cache_path: Path = field(default_factory=lambda: Path("./data/gh_stars_cache.db"))


def load_config(config_path: str = "config.yaml") -> AppConfig:
    """設定をロードします。優先順位: 環境変数 > .env > config.yaml"""
    # .env を読み込む
    load_dotenv()

    # デフォルト値
    config_dict = {
        "database": {
            "backend": "sqlite",
            "path": "./data/gh_favorite.db",
            "mariadb": {
                "host": "localhost",
                "port": 3306,
                "user": "",
                "password": "",
                "database": "gh_stars",
            },
            "cache": {
                "enabled": False,
                "path": "./data/gh_stars_cache.db",
            },
        },
        "tagger": {
            "mode": "rule_based",
            "tags_config_path": "config/tags.yaml",
            "llm_endpoint": "http://localhost:11434",
            "llm_model": "llama3.2",
            "ml_model_path": "~/.local/share/gh_stars/ml_model.pkl"
        },
        "sync": {"page_size": 100}
    }

    # config.yaml があれば上書き
    if Path(config_path).exists():
        with open(config_path, "r") as f:
            yaml_config = yaml.safe_load(f)
            if yaml_config:
                # 深いマージ (簡易版)
                for key in ["tagger", "sync"]:
                    if key in yaml_config:
                        config_dict[key].update(yaml_config[key])
                # database は一段深いネスト構造のため個別マージ
                if "database" in yaml_config:
                    db_yaml = yaml_config["database"]
                    for k in ["backend", "path"]:
                        if k in db_yaml:
                            config_dict["database"][k] = db_yaml[k]
                    if "mariadb" in db_yaml:
                        config_dict["database"]["mariadb"].update(db_yaml["mariadb"])
                    if "cache" in db_yaml:
                        config_dict["database"]["cache"].update(db_yaml["cache"])

    # 環境変数での最終上書き
    pat = os.getenv("GITHUB_PAT", "")
    mariadb_password = os.getenv(
        "MARIADB_PASSWORD",
        config_dict["database"]["mariadb"].get("password", "")
    )

    db_cfg = config_dict["database"]
    mariadb_cfg = db_cfg["mariadb"]
    cache_cfg = db_cfg["cache"]

    return AppConfig(
        github_pat=pat,
        db_path=Path(db_cfg["path"]),
        tagger_mode=config_dict["tagger"]["mode"],
        llm_endpoint=config_dict["tagger"]["llm_endpoint"],
        llm_model=config_dict["tagger"]["llm_model"],
        sync_page_size=config_dict["sync"]["page_size"],
        tags_config_path=Path(config_dict["tagger"]["tags_config_path"]),
        ml_model_path=Path(config_dict["tagger"]["ml_model_path"]).expanduser(),
        # 新規フィールド
        db_backend=db_cfg.get("backend", "sqlite"),
        mariadb_host=mariadb_cfg.get("host", "localhost"),
        mariadb_port=int(mariadb_cfg.get("port", 3306)),
        mariadb_user=mariadb_cfg.get("user", ""),
        mariadb_password=mariadb_password,
        mariadb_database=mariadb_cfg.get("database", "gh_stars"),
        cache_enabled=bool(cache_cfg.get("enabled", False)),
        cache_path=Path(cache_cfg.get("path", "./data/gh_stars_cache.db")),
    )
