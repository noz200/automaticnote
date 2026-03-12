# automaticnote

最新ニュースを収集し、関心が高そうな話題を選び、記事下書きを生成して note 投稿までつなぐ自動化スクリプトです。

## 投稿モード

- `manual`: 記事生成 + Markdown保存のみ（投稿は手動）
- `playwright_existing_session` (**推奨/デフォルト**): 既存ログインセッションを再利用して下書き入力
- `playwright_login`: メール/パスワードでログインして投稿

`playwright_existing_session` を標準にする理由:

- アカウントID/PWを保存しない運用が可能
- 2FAやログイン画面変更の影響を受けにくい
- まず下書きまで自動化し、公開は手動にして誤投稿リスクを下げられる

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

## パイプライン

1. RSSから最新記事を収集
2. タイトルをトレンドキーワード・新しさ・読みやすさでスコアリング
3. OpenAIで本文生成
4. Markdown保存
5. noteの投稿フォームへ自動入力

## CLI（最小実装）

```bash
pip install -e .
automaticnote healthcheck
```

`healthcheck` では `NOTE_API_BASE_URL` と `NOTE_API_TOKEN` の読み込み・検証を行います。

## ブランチ管理

運用ルールは以下を参照してください。

- [docs/branch-strategy.md](docs/branch-strategy.md)

## Windowsで仮想環境と依存インストール

1. Git BashやPowerShellで scripts_setup.sh を実行

   ```bash
   ./scripts_setup.sh
   ```
   または
   ```powershell
   bash scripts_setup.sh
   ```

2. 仮想環境をアクティベート（cmdの場合）
   ```cmd
   .venv\Scripts\activate.bat
   ```

3. 実行例
   ```bash
   python src/auto_note_pipeline.py --mode playwright_existing_session
   ```
