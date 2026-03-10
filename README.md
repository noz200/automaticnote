# automaticnote

`note` 投稿作業を自動化するための土台リポジトリです。  
まずは **安全に育てられる最小構成** と **ブランチ運用ルール** を用意しています。

## 何が入っているか

- Python パッケージの最小実装（`src/automaticnote`）
- CLI エントリポイント（`automaticnote`）
- 環境変数ベースの設定ローダ
- ブランチ戦略ドキュメント（`docs/branch-strategy.md`）

## セットアップ

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 使い方（現時点）

```bash
automaticnote healthcheck
```

API 接続はまだ未実装ですが、`NOTE_API_BASE_URL` と `NOTE_API_TOKEN` の読み込みと検証は実装済みです。

## ブランチ管理

ブランチ運用の詳細は以下を参照してください。

- [docs/branch-strategy.md](docs/branch-strategy.md)

要点:

- `main`: 常にリリース可能な状態
- `develop`: 開発統合ブランチ
- `feature/*`, `fix/*`, `chore/*`: 短命ブランチで PR ベース開発
