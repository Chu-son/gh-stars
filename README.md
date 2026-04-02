# GitHub Star Management (gh-stars)

GitHubのスター付きリポジトリを効率的に管理・検索・閲覧するためのTUIツールです。

## 特徴
- **TUI (Text User Interface)**: ターミナル上で軽快に動作
- **インクリメンタル同期**: 差分のみを取得するため高速
- **自動タグ付け**: 言語やトピックから自動でカテゴリ分け
- **機械学習タガー (Phase 2)**: ユーザーの手動編集を学習し、タグ付け精度を向上（scikit-learn使用）
- **類似リポジトリ検索 (Phase 2)**: 現在のリポジトリに近い他のスター済みプロジェクトを提案
- **ローカル管理**: データは手元の SQLite に保存
- **ブラウザ連携**: `o` キーでリポジトリを即座に開く

## セットアップ

### 1. インストール
`uv` がインストールされている必要があります。

```bash
uv sync
```

機械学習機能（MLモード）を使用する場合は、追加の依存関係をインストールしてください。

```bash
uv pip install -e "packages/processor[ml]"
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

**MLモードの有効化:**
`config.yaml` で以下の設定を行うと、ルールベースから機械学習ベースのタグ付けに切り替わります。

```yaml
tagger:
  mode: ml
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
| `t` | タグ編集モーダル表示 |
| `Esc` | 前の画面に戻る |
| `b` | サイドバーの表示/非表示トグル |
| `j`/`k` | リストの上下移動 (Vim-like) |

## 開発

### テスト
```bash
# 全テスト実行 (ML機能のテストには scikit-learn が必要)
uv run --group dev --with scikit-learn python -m pytest tests/ -v
```
