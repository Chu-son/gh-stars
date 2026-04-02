import pytest
from pathlib import Path
from processor.tagging.ml_tagger import MlTagger
from processor.tagging.rule_based import RuleBasedTagger

@pytest.fixture
def temp_model_path(tmp_path):
    return tmp_path / "model.pkl"

@pytest.fixture
def tags_config_path(tmp_path):
    config = tmp_path / "tags.yaml"
    config.write_text("rules:\n  - tag: python\n    match:\n      language: [Python]\n")
    return config

def test_ml_tagger_fallback(temp_model_path, tags_config_path):
    # 学習データがない状態では RuleBasedTagger にフォールバックする
    tagger = MlTagger(temp_model_path, tags_config_path)
    
    repo = {"primary_language": "Python", "description": "", "topics": []}
    suggested = tagger.suggest_tags(repo)
    assert "python" in suggested

def test_ml_tagger_learning(temp_model_path, tags_config_path):
    tagger = MlTagger(temp_model_path, tags_config_path)
    
    # 未知のパターン
    repo = {"primary_language": "C++", "description": "Game engine", "topics": ["graphics"]}
    # 初期状態では 'other' (RuleBased のデフォルト)
    assert tagger.suggest_tags(repo) == ["other"]
    
    # 学習させる
    tagger.learn(repo, ["game-dev", "cpp"])
    
    # 学習後は提案されるはず
    suggested = tagger.suggest_tags(repo)
    assert "game-dev" in suggested
    assert "cpp" in suggested
    
    # 永続化の確認
    tagger2 = MlTagger(temp_model_path, tags_config_path)
    suggested2 = tagger2.suggest_tags(repo)
    assert "game-dev" in suggested2
    assert "cpp" in suggested2

def test_ml_tagger_negative_learning(temp_model_path, tags_config_path):
    tagger = MlTagger(temp_model_path, tags_config_path)
    
    repo1 = {"primary_language": "Go", "description": "Web server", "topics": ["network"]}
    repo2 = {"primary_language": "JavaScript", "description": "React app", "topics": ["frontend"]}

    # 回数を増やして、各分類器が正理例と負例の両方を見れるようにする
    for _ in range(3):
        tagger.learn(repo1, ["backend"])
        tagger.learn(repo2, ["frontend"])
    
    # 正しく分類されるか
    suggested1 = tagger.suggest_tags(repo1)
    suggested2 = tagger.suggest_tags(repo2)
    
    assert "backend" in suggested1
    assert "frontend" in suggested2
    assert "frontend" not in suggested1
    assert "backend" not in suggested2
