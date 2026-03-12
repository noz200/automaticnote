# Branch Strategy

## 基本方針

- `main` から作業ブランチを1本切って作業する
- 途中で別ブランチを切らない
- 作業ブランチではコミットを積み、最終的に `main` へPRでマージする

## ブランチ種別

- `main`
  - 常に安定状態
  - 直接pushしない
- `feature/<topic>` または `fix/<topic>`
  - 作業用ブランチ
  - 1テーマにつき1本

## 運用ルール

1. `main` 最新化後に作業ブランチを作成
2. そのブランチ内でのみコミットを積む
3. 追加で派生ブランチを作らない
4. PRを作成して `main` へマージ
5. マージ後に作業ブランチを削除

## コミットメッセージ例

- `feat: add title ranking logic`
- `fix: repair pytest import path`
- `docs: simplify branch strategy`
