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


## ローカル実行・テスト手順（Windows cmd）

1. 仮想環境を作成

   ```cmd
   python -m venv .venv
   ```

2. 仮想環境を有効化

   ```cmd
   .venv\Scripts\activate.bat
   ```

3. 依存関係をインストール

   ```cmd
   pip install -r requirements.txt
   ```

4. import確認（dotenv / パイプライン）

   ```cmd
   set PYTHONPATH=src
   python -c "from dotenv import load_dotenv; import auto_note_pipeline; print('import_ok')"
   ```

5. テストを実行

   ```cmd
   pytest -q
   ```

6. パイプラインを手動投稿モードで実行（ローカル完走確認）

   ```cmd
   set AUTOMATICNOTE_LOCAL_DEMO=true
   set AUTOMATICNOTE_MOCK_OPENAI=true
   python src/auto_note_pipeline.py --mode manual
   ```

   > APIキーやRSS取得に依存せず、Markdown出力までローカルで確認できます。

7. 投稿モードを試す（既存セッション）

   ```cmd
   python src/auto_note_pipeline.py --mode playwright_existing_session
   ```

   Playwrightブラウザが未導入の場合は以下を実行してください。

   ```cmd
   playwright install chromium
   ```


## この環境で確認できた範囲

### 注意: `pytest` 成功 = E2E完了 ではありません

- `pytest -q` は **ユニットテスト/ローカル検証** が通ったことを示します。
- 最新ニュース取得 → 記事生成 → noteログイン → 投稿完了、まで確認できて初めて **E2E完了** です。
- この環境では `OPENAI_API_KEY` / `NOTE_EMAIL` / `NOTE_PASSWORD` / `NOTE_USER_DATA_DIR` が未設定で、さらに Playwright 用 Chromium も未導入のため、E2E完了までは確認できていません。

### なぜ `pip install` が失敗しても `pytest` は通るのか

- 現在の実行 Python は `/root/.pyenv/versions/3.10.19/bin/python` です。
- この Python には `feedparser`, `openai`, `playwright`, `python-dotenv` が**既にグローバルに入っている**ため、既存環境では import と `pytest` が通ります。
- 一方で、新規に作成した `.venv_check` では PyPI 取得が proxy/403 で失敗したため、**新規環境への再インストール確認**はできていません。

2026-03-19 時点で、このリポジトリに対して実際に確認できた範囲は次の通りです。

- 仮想環境作成: 可能（`python -m venv .venv_check` で確認）
- `pip install -r requirements.txt`: コマンド実行は可能だが、この環境では PyPI への接続が 403 で失敗
- `dotenv` / パイプライン import: 成功
- `pytest -q`: 成功（`4 passed`）
- `python src/auto_note_pipeline.py --mode manual`: APIキー未設定のままだと失敗
- `AUTOMATICNOTE_LOCAL_DEMO=true` + `AUTOMATICNOTE_MOCK_OPENAI=true` の manual 実行: 成功
- `--mode playwright_existing_session`: Playwright ブラウザ未導入のため未完了

詳しいコマンドと結果は `docs/execution-results.md` を参照してください。


### 実 API / 実投稿の現状

- OpenAI API キーを設定して記事生成を試したところ、SDK互換性の問題（`responses` 属性なし）は修正できました。
- ただしその後、OpenAI API 呼び出し自体が `Network is unreachable` で失敗しました。
- そのため、この環境では**実 OpenAI 記事生成**は未完了です。
- note 投稿については、Playwright Chromium 未導入のため、ログイン・投稿処理は未完了です。

### requirements.txt について

- ご要望に合わせて、`requirements.txt` はこの環境の `python -m pip freeze` と一致する内容へ更新しました。
- これにより、この環境で import に使われていたライブラリ群とバージョンをそのまま記録しています。

## 実行ログ

実際の試行結果は `docs/execution-results.md` に記録しています。
