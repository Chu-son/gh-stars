# GitHub Star管理TUIツール 実装計画書（フェーズ3完了版）

GitHubのスター付きリポジトリをAI（ローカルLLM）とベクトル検索で高度に管理するTUIアプリケーション。

**ステータス**: フェーズ3 全機能実装完了 (2026-04-03)
**環境**: `uv` + `Ollama` (Native)  
**主要技術**: Textual, SQLite, `sqlite-vec`, `sentence-transformers`  

---

## プロジェクト構造（フェーズ1〜2 完全版）

```
gh_favorite/
├── pyproject.toml                   # uv workspaces定義・dev-dependencies
├── uv.lock                          # ロックファイル（コミット対象）
├── .env.example                     # GITHUB_PATのサンプル
├── .env                             # 実際のPAT（gitignore対象）
├── config.yaml.example              # アプリ設定サンプル
├── config.yaml                      # 実際の設定（gitignore対象）
├── .gitignore
├── README.md
│
├── docs/
│   ├── requirements.md              # 要件定義書（原文）
│   └── architecture.md             # パッケージ依存図・DBスキーマER図
│
├── data/                            # SQLiteファイル（gitignore対象）
│   └── .gitkeep
│
├── packages/
│   ├── collector/                   # 【データ収集パッケージ】
│   │   ├── pyproject.toml
│   │   └── collector/
│   │       ├── __init__.py
│   │       ├── github_client.py    # GraphQL APIクライアント (httpx)
│   │       └── sync.py             # 初回・差分同期ロジック
│   │
│   ├── processor/                   # 【データ処理パッケージ】
│   │   ├── pyproject.toml
│   │   └── processor/
│   │       ├── __init__.py
│   │       ├── database/
│   │       │   ├── __init__.py
│   │       │   ├── schema.py       # SQLiteスキーマ・初期化
│   │       │   ├── connection.py   # DB接続管理（コンテキストマネージャ）
│   │       │   └── repository.py  # CRUD操作
│   │       ├── tagging/
│   │       │   ├── __init__.py
│   │       │   ├── base.py         # TaggerStrategy (ABC)
│   │       │   ├── rule_based.py   # ルールベース（フェーズ1）
│   │       │   ├── ml_tagger.py    # scikit-learn (フェーズ2: mode=ml)
│   │       │   └── llm_tagger.py   # Ollama API (フェーズ3: mode=llm)
│   │       └── search/
│   │           ├── __init__.py
│   │           ├── base.py         # SimilaritySearchStrategy (ABC)
│   │           ├── tfidf_search.py # TF-IDF（フェーズ2: mode=rule_based/ml）
│   │           └── embedding_search.py # sentence-transformers（フェーズ3: mode=llm）
│   │
│   └── tui/                         # 【アプリケーションインターフェイスパッケージ】
│       ├── pyproject.toml
│       └── tui/
│           ├── __init__.py
│           ├── __main__.py          # `python -m tui` / `uv run python -m tui`
│           ├── app.py               # Textualメインアプリ・キーバインド定義
│           ├── config.py            # .env + config.yaml 読み込み
│           └── screens/
│               ├── __init__.py
│               ├── main_screen.py   # リスト・タグフィルタ・キーワード検索
│               ├── detail_screen.py # 詳細・ブラウザオープン
│               └── tag_edit_modal.py # タグ手動編集モーダル（CRUD）
│
└── tests/
    ├── conftest.py                  # インメモリDB・APIモック共通フィクスチャ
    ├── test_schema.py
    ├── test_sync.py
    └── test_tagger.py
```

---

## パッケージ依存関係

```
tui  ──▶  processor  ──▶  (stdlib: sqlite3)
 │
 └──▶  collector  ──▶  httpx
```

---

## 詳細設計

### A. 設定ファイル・環境変数

#### [NEW] [.gitignore](file:///home/chuson/develop/gh_favorite/.gitignore)

```gitignore
.env
config.yaml
data/*.db
__pycache__/
.venv/
*.egg-info/
```

#### [NEW] [.env.example](file:///home/chuson/develop/gh_favorite/.env.example)

```dotenv
GITHUB_PAT=ghp_xxxxxxxxxxxxxxxxxxxx
```

#### [NEW] [config.yaml.example](file:///home/chuson/develop/gh_favorite/config.yaml.example)

```yaml
database:
  path: ./data/gh_stars.db

tagger:
  mode: rule_based               # rule_based | ml
  ml_model_path: ~/.local/share/gh_stars/ml_model.pkl  # MLモデル保存先（フェーズ2）
  llm_endpoint: http://localhost:11434  # Ollama（フェーズ3）
  llm_model: gemma3              # Ollamaモデル名（フェーズ3）

sync:
  page_size: 100
```

#### [NEW] [tui/config.py](file:///home/chuson/develop/gh_favorite/packages/tui/tui/config.py)

```python
# ロード優先順位: 環境変数 > .env > config.yaml
@dataclass
class AppConfig:
    github_pat: str
    db_path: str
    tagger_mode: str    # "rule_based" | "ml" | "llm"
    llm_endpoint: str   # フェーズ3
    llm_model: str      # フェーズ3
    sync_page_size: int

def load_config(config_path: str = "config.yaml") -> AppConfig: ...
```

---

### B. pyproject.toml 構成

#### [NEW] ルート [pyproject.toml](file:///home/chuson/develop/gh_favorite/pyproject.toml)

```toml
[tool.uv.workspace]
members = ["packages/*"]

[tool.uv]
dev-dependencies = [
  "pytest>=8",
  "pytest-asyncio>=0.23",
  "respx>=0.21",
]
```

#### 各パッケージの依存関係

| パッケージ | フェーズ1 dependencies | フェーズ2追加 | フェーズ3追加 |
|---|---|---|---|
| `collector` | `httpx>=0.27` | — | — |
| `processor` | （なし） | `scikit-learn` | `sentence-transformers`, `sqlite-vec` |
| `tui` | `textual>=0.70`, `python-dotenv>=1.0`, `pyyaml>=6`, `collector`, `processor` | — | — |

---

### C. DBスキーマ（`processor/database/schema.py`）

```sql
CREATE TABLE repositories (
  github_id        TEXT PRIMARY KEY,
  name             TEXT NOT NULL,
  full_name        TEXT NOT NULL,
  url              TEXT NOT NULL,
  description      TEXT,
  primary_language TEXT,
  topics           TEXT,          -- JSON配列文字列 例: '["cli","python"]'
  stars            INTEGER DEFAULT 0,
  forks            INTEGER DEFAULT 0,
  license          TEXT,
  readme           TEXT,          -- タグ付け用（取得できない場合はNULL）
  starred_at       TEXT NOT NULL, -- ISO8601 例: "2024-01-15T10:30:00Z"
  synced_at        TEXT NOT NULL
);

CREATE TABLE tags (
  id   INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL
);

CREATE TABLE repository_tags (
  repo_id TEXT    NOT NULL REFERENCES repositories(github_id) ON DELETE CASCADE,
  tag_id  INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  source  TEXT    NOT NULL CHECK(source IN ('auto', 'manual')),
  PRIMARY KEY (repo_id, tag_id)
);

-- タグ編集履歴（フェーズ2/3: 学習機能・Few-Shotプロンプト生成に使用）
CREATE TABLE tag_edit_history (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  repo_id   TEXT NOT NULL,
  action    TEXT NOT NULL CHECK(action IN ('add', 'remove')),
  tag_name  TEXT NOT NULL,
  edited_at TEXT NOT NULL
);

CREATE TABLE sync_meta (
  key   TEXT PRIMARY KEY,  -- last_starred_at | last_synced_at
  value TEXT
);
```

---

### D. `processor/database/repository.py` 公開インターフェース

```python
def upsert_repository(conn, repo: dict) -> None
def get_all_repositories(conn, tag_filter: str | None = None,
                         keyword: str | None = None) -> list[dict]
def get_repository_by_id(conn, github_id: str) -> dict | None
def get_random_repository(conn, tag_filter: str | None = None) -> dict | None

def get_or_create_tag(conn, name: str) -> int
def get_tags_for_repo(conn, repo_id: str) -> list[str]
def set_tags_for_repo(conn, repo_id: str, tag_names: list[str], source: str = 'auto') -> None
def add_tag_to_repo(conn, repo_id: str, tag_name: str, source: str) -> None
def remove_tag_from_repo(conn, repo_id: str, tag_name: str) -> None
def get_all_tags(conn) -> list[str]

def get_sync_meta(conn, key: str) -> str | None
def set_sync_meta(conn, key: str, value: str) -> None
```

---

### E. `collector/github_client.py` GraphQLクエリ

```graphql
query StarredRepos($cursor: String, $pageSize: Int!) {
  viewer {
    starredRepositories(first: $pageSize, after: $cursor,
                        orderBy: {field: STARRED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      edges {
        starredAt
        node {
          id
          name
          nameWithOwner
          url
          description
          primaryLanguage { name }
          repositoryTopics(first: 20) { nodes { topic { name } } }
          stargazerCount
          forkCount
          licenseInfo { name }
        }
      }
    }
  }
}
```

```python
class GitHubClient:
    def __init__(self, pat: str, page_size: int = 100): ...

    async def fetch_starred_repos(
        self, since: str | None = None
    ) -> AsyncIterator[dict]:
        # 1リポジトリ=1dict のストリーム（ページネーション透過）
        # dict keys: github_id, name, full_name, url, description,
        #            primary_language, topics(list[str]), stars, forks,
        #            license, starred_at
```

---

### F. `collector/sync.py` 同期ロジック

```python
# TaggerStrategy を引数で注入（DI）
async def full_sync(client, conn, tagger: TaggerStrategy) -> int: ...
async def incremental_sync(client, conn, tagger: TaggerStrategy) -> int: ...
```

---

### G. Strategyパターン設計（`processor` パッケージ）

#### tagging/base.py

```python
class TaggerStrategy(ABC):
    @abstractmethod
    def suggest_tags(self, repo: dict) -> list[str]: ...
    @abstractmethod
    def learn(self, repo: dict, correct_tags: list[str]) -> None: ...
```

#### tagging/rule_based.py（フェーズ1）

| 条件 | 付与タグ |
|---|---|
| `primary_language == "Python"` | `python` |
| `primary_language in ["TypeScript", "JavaScript"]` | `javascript` |
| `primary_language == "Rust"` | `rust` |
| `primary_language == "Go"` | `go` |
| topics/description に `cli` / `terminal` / `tui` | `cli` |
| topics/description に `web` / `frontend` / `react` / `vue` | `frontend` |
| topics/description に `machine-learning` / `ml` / `ai` / `llm` | `ai-ml` |
| topics/description に `database` / `sql` / `orm` | `database` |
| topics/description に `infra` / `devops` / `docker` / `k8s` | `devops` |
| topics/description に `api` / `rest` / `graphql` | `api` |
| マッチなし | `other` |

#### tagging/ml_tagger.py（フェーズ2: `mode=ml`）

- `scikit-learn SGDClassifier` を使ったオンライン学習
- `learn()` でユーザー修正データをfitして永続化
- モデル保存先: `config.yaml` の `tagger.ml_model_path`（デフォルト: `~/.local/share/gh_stars/ml_model.pkl`）

#### tagging/llm_tagger.py（**フェーズ3**: `mode=llm`）

- Ollama HTTP API (`POST /api/generate`) を呼び出し
- `learn()` で `tag_edit_history` からFew-Shot事例を動的生成してプロンプトに埋め込む
- Ollamaが起動していない場合は `rule_based` にフォールバック

#### search/base.py

```python
class SimilaritySearchStrategy(ABC):
    @abstractmethod
    def find_similar(self, repo_id: str, top_k: int = 10) -> list[dict]: ...
    @abstractmethod
    def rebuild_index(self) -> None: ...
```

#### search/tfidf_search.py（フェーズ2）
- `description + topics` テキストをTF-IDFベクトル化してコサイン類似度検索

#### search/embedding_search.py（**フェーズ3**）
- `sentence-transformers` でベクトル化 → `sqlite-vec` で近似最近傍探索

---

### H. CLIエントリポイント（`tui/__main__.py`）

```python
# uv run python -m tui [オプション]

parser.add_argument("--sync",      action="store_true", help="差分同期後にTUI起動")
parser.add_argument("--sync-full", action="store_true", help="全件同期後にTUI起動")
parser.add_argument("--sync-only", action="store_true", help="同期のみ（TUI起動しない）")
```

---

### I. TUI設計（`tui` パッケージ）

#### app.py キーバインド

| キー | 動作 | 画面 |
|------|------|------|
| `q` | 終了 | 全画面 |
| `s` | 差分同期 | メイン |
| `S` | 全件同期 | メイン |
| `r` | ランダムピック（詳細に遷移） | メイン |
| `R` | リストをシャッフル | メイン |
| `U` | タグを再適用（ローカル） | メイン |
| `o` | ブラウザで開く | メイン/詳細 |
| `/` | 検索バーにフォーカス | メイン |
| `t` | タグ編集モーダルを開く | メイン/詳細 |
| `j` / `k` | リスト上下移動 | メイン |
| `g` / `G` | リスト先頭/末尾ジャンプ | メイン |
| `l` | 詳細画面へ（Enter と同等） | メイン |
| `h` | 前画面に戻る | 詳細 |
| `ctrl+d` / `ctrl+u` | 半ページスクロール | メイン |
| `1` / `2` / `3` / `4` | ソート切替（Stars/Name/Lang/Date） | メイン |
| `Escape` | 前画面に戻る | 詳細/モーダル |

#### main_screen.py レイアウト

```
┌─ GH Favorite ────────────────────────────┐
│ [/検索バー___________________________]    │
├──────────┬───────────────────────────────┤
│ タグ一覧 │ リポジトリ一覧 (DataTable)    │
│ [all]    │ ⭐  名前        言語  タグ    │
│ [python] │ 12k foo/bar    Py   cli      │
│ [cli]    │  3k baz/qux    TS   api      │
├──────────┴───────────────────────────────┤
│ 全42件 | フィルタ: python | 最終同期: 5分前 │
└──────────────────────────────────────────┘
```

#### detail_screen.py レイアウト

```
┌─ foo/bar ─────────────────────────────────┐
│ # foo/bar                                 │
│ ⭐12,345  🍴234  Python  MIT             │
│ タグ: [cli] [python]                      │
│ A great CLI tool for...                   │
│ https://github.com/foo/bar                │
│ [o]ブラウザで開く  [t]タグ編集  [Esc]戻る  │
└───────────────────────────────────────────┘
```

#### tag_edit_modal.py レイアウト

```
┌─ タグ編集: foo/bar ──────────────────┐
│ [x] cli      [x] python             │
│ [ ] frontend [ ] devops             │
│ 新規タグ: [____________] [追加]      │
│                     [保存] [閉じる]  │
└──────────────────────────────────────┘
```
保存時: `repository_tags` 更新 + `tag_edit_history` に `source='manual'` で記録

---

## 依存パッケージまとめ

### フェーズ1

| パッケージ | 用途 |
|---|---|
| `textual>=0.70` | TUIフレームワーク |
| `httpx>=0.27` | 非同期HTTPクライアント |
| `python-dotenv>=1.0` | `.env` 読み込み |
| `pyyaml>=6` | `config.yaml` 読み込み |

### テスト

| パッケージ | 用途 |
|---|---|
| `pytest>=8` | テストフレームワーク |
| `pytest-asyncio>=0.23` | 非同期テスト |
| `respx>=0.21` | httpxモック |

### フェーズ2（拡張）

| パッケージ | 用途 |
|---|---|
| `scikit-learn` | MLタガー・TF-IDF類似検索 |

### フェーズ3（LLM拡張）

| パッケージ | 用途 |
|---|---|
| `sentence-transformers` | Embeddingベース類似検索 |
| `sqlite-vec` | ベクトルDB拡張 |
| *(Ollama: ホストにネイティブインストール)* | ローカルLLM推論 |

---

### J. UI/UX改善機能の実装（フェーズ1追加改修）

以下の5つの機能追加により、UI/UXを向上させます。他開発者へのハンドオフを想定した詳細な手順です。

#### 1. 全タブでのVimライクなキーバインド対応
**対象ファイル:** `packages/tui/tui/screens/main_screen.py`
- **目的:** 既存の `DataTable` 以外のコンポーネント（特にサイドバーの `ListView`）でも `j`, `k`, `g`, `G` などのスクロール操作を可能にする。
- **手法:**
  - `action_cursor_down(self)`, `action_cursor_up(self)`, `action_cursor_top(self)`, `action_cursor_bottom(self)` メソッドを改修。
  - `self.focused` を用いて、現在フォーカスされているコンポーネント（ウィジェット）を取得する。
  - `isinstance()` で型判定し、フォーカス先がタグ一覧の `ListView`（サイドバー）であれば、そのコンポーネントの `action_cursor_down()` 等を呼んで操作を移譲する。
  - 変更後のメインリスト（後述の `ListView` や `DataTable`）がフォーカスされている場合は、該当コンポーネントの操作を行う。

#### 2. h, l キーでの水平スクロール対応
**対象ファイル:** `packages/tui/tui/screens/main_screen.py`
- **目的:** 画面内に収まらない長いテキスト列を持つリストなどが存在した場合、左右のスクロールをキー操作で可能にする。
- **手法:**
  - `BINDINGS` リストに `Binding("h", "scroll_left", "Left", show=False)`, `Binding("l", "scroll_right", "Right", show=False)` を追加する。
  - `action_scroll_left(self)` および `action_scroll_right(self)` メソッドを新規定義する。
  - 現在フォーカスされているコンポーネントに対し、Textual標準のスクロールメソッドである `self.focused.scroll_relative(x=-1)` (左) / `self.focused.scroll_relative(x=1)` (右) などを呼び出し水平オフセット移動を実装する。

#### 3. Tagsタブ（サイドバー）のトグル表示
**対象ファイル:** `packages/tui/tui/screens/main_screen.py`
- **目的:** 画面幅を有効活用するため、Tags一覧を `b` キーで表示・非表示（トグル）できるようにする。
- **手法:**
  - `BINDINGS` に `Binding("b", "toggle_sidebar", "Toggle Sidebar")` を追加。
  - 新規に `action_toggle_sidebar(self)` を定義。
  - `sidebar = self.query_one("#sidebar")` でサイドバーの UI コンテナ要素を取得し、`sidebar.display = not sidebar.display` とブール値を反転してセットする。これによりTextualのDOMから一時的に消え、メインのコンテンツエリアが全幅に自動展開される。

#### 4. リポジトリリストの幅圧縮に伴う複数行対応（DataTable → ListView）
**対象ファイル:** `packages/tui/tui/screens/main_screen.py`
- **目的:** ウィンドウ幅が圧縮（またはサイドバー表示状態）されても、情報が途切れず自動で改行される「カード」形式のUIに変更する。
- **手法:**
  - **UI定義の置換:** `compose()` 内で定義している `#repo_table` (`DataTable`) を `ListView(id="repo_list")` へ変更する。
  - **カスタム ListItem クラス定義:** `RepoItem(ListItem)` を `main_screen.py` 内（または専用モジュール）に定義する。
    - `__init__` でリポジトリデータを DI する。
    - `compose()` で `Vertical`, `Horizontal` を使い、情報をレイアウト（上段: repo_name / stars /lang、下段: description）。
    - 説明文用ラベルの CSS で `height: auto` を適用し、複数行の自動折り返しが動作するように設定する。
  - **データバインディング改修:** `reload_table()` メソッドを `reload_list()` とし、各リポジトリから `RepoItem` を生成して `ListView.append()` で登録するロジックに書き換える。
  - **選択イベント改修:** `on_data_table_row_selected` イベントを `on_list_view_selected` に置き換える。選択された `RepoItem` からIDを抽出し、`DetailScreen` に遷移させる。

#### 5. ソートにおける昇順・降順（ASC/DESC）のトグル機能
**対象ファイル:** `packages/tui/tui/screens/main_screen.py` および `packages/processor/processor/database/repository.py`
- **目的:** ワンキー（同じソートキーの連続押下）でソートの表示順を反転（トグル）できるようにする。
- **手法 (main_screen.py):**
  - メイン画面のインスタンス変数（状態）として `self.sort_descending = True` (デフォルト) を追加。
  - 各 `action_sort_*` (例: `action_sort_stars`) メソッドにおいて、現在の `self.sort_by` と押下された項目が一致した場合は、`self.sort_descending = not self.sort_descending` として順番を反転。一致しない場合は項目を切り替え、対象のデフォルトの順番へ戻す。
  - `_update_status_bar` メソッドで、`self.sort_descending` に応じてステータスバー上のアイコンを `▼` （降順）や `▲` （昇順）に動的に変更する。
- **手法 (repository.py):**
  - `get_all_repositories` 関数の引数にソート方向の指定 `sort_descending: bool = True` を追加する。
  - 内部で組み立てている SQL クエリの `ORDER BY` 句に、変数の状態から生成した文字列 (`DESC` または `ASC`) を挿入し、正しい順番でデータを取得できるように修正する。

---

## 検証計画

```bash
# テスト実行
uv run pytest tests/ -v

# 初回セットアップ
cp .env.example .env          # GITHUB_PAT を記入
cp config.yaml.example config.yaml

# 全件同期
uv run python -m tui --sync-full --sync-only

# TUI起動
uv run python -m tui
```

| 確認項目 | 操作 | 期待結果 |
|---|---|---|
| リスト表示 | 起動 | リポジトリ一覧表示 |
| タグフィルタ | タグクリック | 絞り込み |
| キーワード検索 | `/` + 入力 | インクリメンタル絞り込み |
| 詳細表示 | Enter | 詳細画面遷移 |
| ブラウザ | `o` | デフォルトブラウザでGitHub表示 |
| ランダム | `r` | ランダム詳細表示 |
| タグ編集 | `t` | モーダル表示・保存 |
| 差分同期 | `s` | 新着のみ取得 |
