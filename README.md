# GitHub Star Management (gh-stars)

GitHubのスター付きリポジトリを効率的に管理・検索・閲覧するためのTUIツールです。

## 特徴
- **TUI (Text User Interface)**: ターミナル上で軽快に動作
- **インクリメンタル同期**: 差分のみを取得するため高速
- **自動タグ付け**: 言語やトピックから自動でカテゴリ分け
- **機械学習タガー (Phase 2)**: ユーザーの手動編集を学習し、タグ付け精度を向上（scikit-learn使用）
- **LLMタガー & セマンティック検索 (Phase 3)**: ローカルLLM (Ollama) を用いた高度な自動タグ付けと、自然言語による「意味の近さ」に基づいた検索を実現
- **類似リポジトリ検索**: 現在のリポジトリに近い他のスター済みプロジェクトを提案。TF-IDF または LLM 埋め込みベクトルの両方式に対応
- **ローカル管理**: データは手元の SQLite に保存。`sqlite-vec` 拡張による高速なベクトル検索をサポート
- **ブラウザ連携**: `o` キーでリポジトリを即座に開く

## セットアップ

### 1. インストール
`uv` がインストールされている必要があります。

```bash
uv sync
```

```bash
uv sync --extra llm  # 全機能（LLM・ベクトル検索）を使用する場合
# または
uv sync --extra ml   # 従来の ML モードのみ使用する場合
```

### 2. LLM のセットアップ (Phase 3 機能)
LLM モードを使用するには、[Ollama](https://ollama.com/) が必要です。

1. **Ollama の起動**: ローカルで Ollama を起動してください。
2. **モデルと環境の初期化**:
   ```bash
   uv run python -m tui --setup-llm
   ```
   ※ `llama3.2` モデルの自動プルなどが行われます。

3. **ベクトルインデックスの作成**:
   既存のスター情報をベクトル検索の対象にするため、一度以下を実行します。
   ```bash
   uv run python -m tui --rebuild-vec
   ```

### 2. 環境設定
`.env` ファイルを作成し、GitHubの Personal Access Token (PAT) を設定してください。

```bash
cp .env.example .env
# .env を編集して GITHUB_PAT を入力
```

`config.yaml` を作成して動作設定を調整できます。

```bash
cp config.yaml.example config.yaml
```

**モードの切り替え:**
`config.yaml` で以下の設定を行うと、タグ付けと検索のアルゴリズムが切り替わります。

- `mode: llm` (推奨): Ollama を使用した高度な推論とセマンティック検索
- `mode: ml`: scikit-learn を使用した軽量な自動学習
- `mode: rule_based`: `tags.yaml` に基づくシンプルなキーワードマッチング

```yaml
tagger:
  mode: llm  # llm, ml, or rule_based
```

## 使い方

### 同期
初回は全件取得が必要です。

```bash
uv run python -m tui --sync-full --sync-only
```

2回目以降は差分同期が可能です。

```bash
uv run python -m tui --sync
```

### TUIの起動

```bash
uv run python -m tui
```

### キーバインド

| キー | 動作 |
|---|---|
| `q` | 終了 |
| `s` | 差分同期実行 |
| `S` | 全件同期実行 |
| `r` | ランダムピック |
| `R` | リストのシャッフル |
| `U` | タグの再適用 (ローカルのみ) |
| `o` | ブラウザで開く |
| `/` | 検索 (キーワード/タグ) |
| `?` | 自由文 (AI) 検索 (例: `? React用UIコンポーネント`) |
| `t` | タグ編集モーダル表示 |
| `Esc` | 前の画面に戻る |
| `b` | サイドバーの表示/非表示トグル |
| `j`/`k` | リストの上下移動 (Vim-like) |
| `1`~`4` | ソート切り替え (Stars / Name / Lang / Date) |

## 開発

### テスト
```bash
# 全テスト実行 (ML機能のテストには scikit-learn が必要)
uv run --group dev --with scikit-learn python -m pytest tests/ -v
```
