# GitHub Star Favorite (gh-favorite)

GitHubのスター付きリポジトリを効率的に管理・検索・閲覧するためのTUIツールです。

## 特徴
- **TUI (Text User Interface)**: ターミナル上で軽快に動作
- **インクリメンタル同期**: 差分のみを取得するため高速
- **自動タグ付け**: 言語やトピックから自動でカテゴリ分け
- **ローカル管理**: データは手元の SQLite に保存
- **ブラウザ連携**: `o` キーでリポジトリを即座に開く

## セットアップ

### 1. インストール
`uv` がインストールされている必要があります。

```bash
uv sync
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
| `r` | ランダムピック |
| `o` | ブラウザで開く |
| `/` | 検索 (キーワード/タグ) |
| `t` | タグ編集モーダル表示 |
| `Esc` | 前の画面に戻る |

## 開発

### テスト
```bash
uv run pytest
```
