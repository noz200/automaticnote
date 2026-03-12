# automaticnote

最新ニュースを収集し、関心が高そうなタイトルを選び、記事を生成し、noteへ投稿する自動化ツールです。

## すぐ実行する（仮想環境なしでも開始可）

```bash
bash scripts_setup.sh
source .venv/bin/activate
```

この時点で **ニュース収集 + 記事生成 + Markdown保存** は動きます。

## MCPは使ってる？

使えます。`MCP_NEWS_JSON` を指定すると、MCPで集めたニュースJSONを入力として利用します。

- RSS利用（標準）: `MCP_NEWS_JSON` 未指定
- MCP利用: `MCP_NEWS_JSON=./mcp_news.json`

JSON形式:

```json
[
  {
    "title": "ニュースタイトル",
    "url": "https://example.com",
    "source": "mcp-source",
    "published": "2026-01-01T00:00:00+00:00"
  }
]
```

## 実行方法

### 1) まず動作確認（投稿なし）

```bash
source .venv/bin/activate
export OPENAI_API_KEY=...
python src/auto_note_pipeline.py --mode manual
```

### 2) 完全自動投稿（ログイン→作成→公開）

> Playwrightインストールが必要です（ネットワーク許可時）

```bash
source .venv/bin/activate
pip install playwright
python -m playwright install chromium

export OPENAI_API_KEY=...
export NOTE_EMAIL=...
export NOTE_PASSWORD=...
python src/auto_note_pipeline.py --mode playwright_login --fully-auto
```

## 環境変数

```env
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4.1-mini
OUTPUT_DIR=output
NEWS_PER_FEED=20

# MCPニュースを使う場合のみ指定
MCP_NEWS_JSON=./mcp_news.json

# 投稿関連
NOTE_USER_DATA_DIR=.note_profile
NOTE_LOGIN_TMP_PROFILE=.note_profile_tmp
NOTE_EMAIL=you@example.com
NOTE_PASSWORD=your-password
NOTE_AUTO_PUBLISH=false
PLAYWRIGHT_HEADLESS=true
```

## 注意

- noteのUI変更でセレクタが変わる可能性があります。
- 完全自動公開はテストアカウントで検証してから本番運用してください。
