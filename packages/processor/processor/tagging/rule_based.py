from .base import TaggerStrategy

class RuleBasedTagger(TaggerStrategy):
    """キーワードマッチングに基づくルールベースのタグ付け。"""

    def suggest_tags(self, repo: dict) -> list[str]:
        tags = set()
        
        # 1. 言語による判定
        lang = (repo.get("primary_language") or "").lower()
        if lang == "python":
            tags.add("python")
        elif lang in ["typescript", "javascript"]:
            tags.add("javascript")
        elif lang == "rust":
            tags.add("rust")
        elif lang == "go":
            tags.add("go")

        # 2. キーワードによる判定 (topics, description)
        description = (repo.get("description") or "").lower()
        topics = [t.lower() for t in (repo.get("topics") or [])]
        
        combined_text = description + " " + " ".join(topics)
        
        # CLI関連
        if any(kw in combined_text for kw in ["cli", "terminal", "tui", "command-line"]):
            tags.add("cli")
            
        # Frontend関連
        if any(kw in combined_text for kw in ["web", "frontend", "react", "vue", "svelte", "nextjs"]):
            tags.add("frontend")
            
        # AI/ML関連
        if any(kw in combined_text for kw in ["machine-learning", "ml", "ai", "llm", "neural-network", "deep-learning", "pytorch", "tensorflow"]):
            tags.add("ai-ml")
            
        # Database関連
        if any(kw in combined_text for kw in ["database", "sql", "orm", "postgres", "sqlite", "redis", "mongodb"]):
            tags.add("database")
            
        # DevOps/Infra関連
        if any(kw in combined_text for kw in ["infra", "devops", "docker", "kubernetes", "k8s", "terraform", "ansible", "cloud"]):
            tags.add("devops")
            
        # API関連
        if any(kw in combined_text for kw in ["api", "rest", "graphql", "grpc", "http"]):
            tags.add("api")

        if not tags:
            tags.add("other")
            
        return sorted(list(tags))

    def learn(self, repo: dict, correct_tags: list[str]) -> None:
        # ルールベースは学習を行わない
        pass
