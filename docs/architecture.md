# システムアーキテクチャ

## パッケージ構成

モノレポ構成（uv workspaces）を採用し、責務を分離しています。

- `packages/collector`: データ収集担当。GitHub GraphQL APIとの通信、同期ロジック。
- `packages/processor`: データ処理担当。SQLite DB管理、タグ付けエンジン(Strategy)、類似検索エンジン(Strategy)。
- `packages/tui`: インターフェース担当。TextualによるUI実装、設定管理、CLIエントリポイント。

## クラス図 (コアロジック)

```mermaid
classDiagram
    direction LR
    class TUIApp {
        +run()
    }
    class GitHubClient {
        +fetch_starred_repos()
    }
    class SyncEngine {
        +incremental_sync()
        +full_sync()
    }
    class Repository {
        +upsert_repo()
        +get_all()
    }
    class TaggerStrategy {
        <<interface>>
        +suggest_tags()
        +learn()
    }
    class RuleBasedTagger {
    }
    
    TUIApp --> SyncEngine
    TUIApp --> Repository
    SyncEngine --> GitHubClient
    SyncEngine --> Repository
    SyncEngine --> TaggerStrategy
    TaggerStrategy <|-- RuleBasedTagger
```

## DBスキーマ (ER図)

```mermaid
erDiagram
    repositories ||--o{ repository_tags : linked
    tags ||--o{ repository_tags : categorization
    repositories {
        string github_id PK
        string name
        string full_name
        string url
        string description
        string primary_language
        string topics
        int stars
        string starred_at
        string synced_at
    }
    tags {
        int id PK
        string name UK
    }
    repository_tags {
        string repo_id FK
        int tag_id FK
        string source
    }
    tag_edit_history {
        int id PK
        string repo_id
        string action
        string tag_name
        datetime edited_at
    }
```
