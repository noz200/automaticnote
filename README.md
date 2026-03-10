# automaticnote

最新ニュースを収集し、関心が高そうなタイトルを選び、記事を生成して note 投稿までつなぐ自動化スクリプトです。

## 実装方針（今回のおすすめ）

要件にあった3パターンを比較した結果、**既存ログインセッションをPlaywrightで再利用**する設計を標準にしました。

- `manual`: 記事生成 + Markdown保存のみ（投稿は手動）
- `playwright_existing_session` (**推奨/デフォルト**): すでにログイン済みの `note` セッションを使って下書き入力
- `playwright_login`: メール/パスワードで自動ログインして投稿

理由:
- セキュリティ上、アカウントID/PWを保存しない運用が可能
- 2FAやログイン画面変更に強い
- まずは下書きまで自動化し、公開は手動にすることで誤投稿リスクを下げられる

## セットアップ

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

`.env` 例:

```env
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4.1-mini
OUTPUT_DIR=output
NEWS_PER_FEED=20

# existing_session モードで利用（任意）
NOTE_USER_DATA_DIR=.note_profile

# playwright_login モードで利用
NOTE_EMAIL=you@example.com
NOTE_PASSWORD=your-password

# trueで公開ボタンまで押す（デフォルトfalse）
NOTE_AUTO_PUBLISH=false
```

## 実行

```bash
python src/auto_note_pipeline.py --mode playwright_existing_session
```

初回は `.note_profile` にブラウザプロフィールが作られます。必要なら手動でログインしてセッションを保持してください。

## パイプライン

1. RSSから最新記事を収集
2. タイトルをトレンドキーワード・新しさ・読みやすさでスコアリング
3. OpenAIで本文生成
4. Markdown保存
5. noteの投稿フォームへ自動入力（モードに応じてログイン制御）

## 注意

- noteのUI変更でセレクタが変わる可能性があります。
- 自動公開 (`NOTE_AUTO_PUBLISH=true`) は十分に検証してから使ってください。
