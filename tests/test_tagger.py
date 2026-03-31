from processor.tagging.rule_based import RuleBasedTagger

def test_rule_based_tagger_language():
    tagger = RuleBasedTagger()
    
    repo = {"primary_language": "Python", "description": "", "topics": []}
    assert "python" in tagger.suggest_tags(repo)
    
    repo = {"primary_language": "TypeScript", "description": "", "topics": []}
    assert "javascript" in tagger.suggest_tags(repo)

def test_rule_based_tagger_keywords():
    tagger = RuleBasedTagger()
    
    # Descriptionマッチ
    repo = {"primary_language": None, "description": "A nice CLI tool", "topics": []}
    assert "cli" in tagger.suggest_tags(repo)
    
    # Topicsマッチ
    repo = {"primary_language": None, "description": "", "topics": ["machine-learning", "ai"]}
    assert "ai-ml" in tagger.suggest_tags(repo)
    
    # 複数マッチ
    repo = {"primary_language": "Python", "description": "Deep learning library", "topics": ["ai"]}
    tags = tagger.suggest_tags(repo)
    assert "python" in tags
    assert "ai-ml" in tags

    # その他
    repo = {"primary_language": "HTML", "description": "nothing", "topics": []}
    assert tagger.suggest_tags(repo) == ["other"]
    
    repo = {"primary_language": "Rust", "description": "Database implementation", "topics": ["sql"]}
    tags = tagger.suggest_tags(repo)
    assert "rust" in tags
    assert "database" in tags
