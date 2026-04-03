import json
import logging
import httpx
import sqlite3
from pathlib import Path
from .base import TaggerStrategy
from .rule_based import RuleBasedTagger

logger = logging.getLogger(__name__)

class LlmTagger(TaggerStrategy):
    """Ollama API を使用してリポジトリのタグを推論するタガー。"""

    def __init__(self, endpoint: str, model: str, db_path: str | Path | None = None):
        self.endpoint = endpoint
        self.model = model
        self.db_path = db_path
        self.fallback = RuleBasedTagger()
        self._status_text = f"LLM ({model})"

    @property
    def status_text(self) -> str:
        return self._status_text

    def _get_history_examples(self, limit: int = 5) -> str:
        """過去の手動修正履歴から Few-Shot 用の例を生成します。"""
        if not self.db_path or not Path(self.db_path).exists():
            return ""
        
        try:
            from ..database.connection import get_db_connection
            with get_db_connection(self.db_path) as conn:
                # 最近の手動修正を取得
                cursor = conn.execute("""
                    SELECT repo_id, action, tag_name 
                    FROM tag_edit_history 
                    ORDER BY edited_at DESC LIMIT ?
                """, (limit * 2,))
                rows = cursor.fetchall()
                if not rows:
                    return ""
                
                examples = "\nUser preferences (history):\n"
                for row in rows:
                    action = "added" if row["action"] == "add" else "removed"
                    examples += f"- For repository {row['repo_id']}, the user {action} the tag '{row['tag_name']}'.\n"
                return examples
        except Exception as e:
            logger.warning(f"Failed to load history for LLM: {e}")
            return ""

    def suggest_tags(self, repo: dict) -> list[str]:
        """LLM に問い合わせてタグを生成します。失敗した場合はルールベースにフォールバックします。"""
        # プロンプトの構築
        name = repo.get("full_name") or repo.get("name")
        description = repo.get("description") or "No description provided."
        lang = repo.get("primary_language") or "Unknown"
        topics = ", ".join(repo.get("topics") or [])
        
        history = self._get_history_examples()
        
        prompt = f"""
Analyze the following GitHub repository and suggest appropriate, concise tags (max 5 tags).
Return ONLY a JSON array of strings.

Repository: {name}
Language: {lang}
Topics: {topics}
Description: {description}
{history}
Instruction: Based on the information and user history above, suggest relevant tags. 
Response example: ["python", "cli", "machine-learning"]
"""

        try:
            import httpx
            # 同期メソッド内で非同期呼び出しを行うための簡易的な対応（または sync 版 httpx を使用）
            with httpx.Client(timeout=15.0) as client:
                response = client.post(
                    f"{self.endpoint}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "format": "json",
                        "stream": False
                    }
                )
                if response.status_code == 200:
                    result = response.json()
                    content = result.get("response", "[]")
                    tags = json.loads(content)
                    if isinstance(tags, list):
                        return [str(t).lower() for t in tags]
                
                logger.error(f"LLM API Error: {response.status_code} {response.text}")
        except Exception as e:
            logger.error(f"LLM Tagger error, falling back to rule-based: {e}")
            
        return self.fallback.suggest_tags(repo)

    def learn(self, repo: dict, correct_tags: list[str]) -> None:
        """
        手動修正を履歴に記録します。
        注意: このメソッド自体は履歴に保存するのみで、推論時にその履歴を参照します。
        実際の保存処理は repository.py などを通じて行うことが多いため、
        ここでは LLM 固有の「追加処理」が必要な場合のみ記述します。
        計画書に基づき、履歴保存は repository.py 側で行われる想定ですが、
        Few-Shot のために必要なデータが揃っているか確認する程度に留めます。
        """
        pass
