# Branch Strategy

## 基本方針

- **GitHub Flow + develop ブランチ** のハイブリッド運用
- `main` は常にデプロイ可能
- 日々の統合は `develop` に集約

## ブランチ種別

- `main`
  - 本番相当ブランチ
  - 直接 push しない
- `develop`
  - 開発統合ブランチ
  - feature 完了後のマージ先
- `feature/<topic>`
  - 新機能開発
  - 例: `feature/note-draft-generator`
- `fix/<topic>`
  - バグ修正
- `chore/<topic>`
  - 依存更新・CI・ドキュメント調整

## 運用ルール

1. `develop` から作業ブランチを切る
2. 小さな単位でコミットする
3. PR を作成しレビューを受ける
4. CI 緑を確認してマージ
5. リリース時に `develop -> main` を PR で反映

## コミットメッセージ例

- `feat: add note draft command scaffold`
- `fix: handle missing NOTE_API_TOKEN`
- `docs: add branch strategy`
