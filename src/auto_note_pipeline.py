from __future__ import annotations

import argparse
import asyncio
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv

load_dotenv()

DEFAULT_FEEDS = [
    "https://www.itmedia.co.jp/news/rss/2.0/news_bursts.xml",
    "https://gigazine.net/news/rss_2.0/",
    "https://news.yahoo.co.jp/rss/topics/it.xml",
]

TREND_KEYWORDS = {
    "ai": 3.0,
    "生成ai": 3.5,
    "chatgpt": 3.0,
    "openai": 2.5,
    "llm": 2.5,
    "半導体": 2.0,
    "nvidia": 2.0,
    "x": 1.0,
    "google": 1.3,
    "apple": 1.3,
    "microsoft": 1.3,
    "セキュリティ": 2.4,
    "脆弱性": 2.5,
    "値上げ": 1.5,
}


class PublishMode(str, Enum):
    MANUAL = "manual"
    PLAYWRIGHT_EXISTING_SESSION = "playwright_existing_session"
    PLAYWRIGHT_LOGIN = "playwright_login"


@dataclass
class NewsItem:
    title: str
    url: str
    published: datetime
    source: str


@dataclass
class PipelineResult:
    selected: NewsItem
    article_title: str
    article_body: str
    markdown_path: Path


def build_demo_news_item() -> NewsItem:
    return NewsItem(
        title="生成AI活用の最新動向をローカル検証する",
        url="https://example.com/local-demo",
        published=datetime.now(timezone.utc),
        source="local-demo",
    )


class NewsCollector:
    def __init__(self, feeds: Iterable[str] | None = None) -> None:
        self.feeds = list(feeds or DEFAULT_FEEDS)

    def collect(self, limit_per_feed: int = 20) -> list[NewsItem]:
        import feedparser

        items: list[NewsItem] = []
        for feed_url in self.feeds:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries[:limit_per_feed]:
                published = self._to_datetime(entry)
                items.append(
                    NewsItem(
                        title=entry.get("title", ""),
                        url=entry.get("link", ""),
                        published=published,
                        source=parsed.feed.get("title", feed_url),
                    )
                )
        return [item for item in items if item.title and item.url]

    @staticmethod
    def _to_datetime(entry: dict) -> datetime:
        candidate = entry.get("published_parsed") or entry.get("updated_parsed")
        if candidate is None:
            return datetime.now(timezone.utc)
        return datetime(*candidate[:6], tzinfo=timezone.utc)


class TitleRanker:
    @staticmethod
    def score(item: NewsItem) -> float:
        text = item.title.lower()
        keyword_score = sum(weight for keyword, weight in TREND_KEYWORDS.items() if keyword in text)
        punctuation_score = 0.6 if re.search(r"[!！?？]", item.title) else 0.0
        title_length_score = 0.4 if 18 <= len(item.title) <= 42 else 0.0

        now = datetime.now(timezone.utc)
        age_hours = max((now - item.published).total_seconds() / 3600, 0)
        recency_score = max(3.0 - (age_hours * 0.1), 0.0)
        return keyword_score + punctuation_score + title_length_score + recency_score

    def pick_best(self, items: list[NewsItem]) -> NewsItem:
        if not items:
            raise ValueError("ニュース項目が0件のため選定できません。")
        return max(items, key=self.score)


class ArticleGenerator:
    @staticmethod
    def _create_client(openai_cls):
        api_key = os.environ.get("OPENAI_API_KEY")
        try:
            return openai_cls(api_key=api_key)
        except TypeError:
            import httpx

            http_client = httpx.Client(trust_env=False)
            return openai_cls(api_key=api_key, http_client=http_client)

    def __init__(self, model: str = "gpt-4.1-mini") -> None:
        self.model = model
        self.mock_openai = os.environ.get("AUTOMATICNOTE_MOCK_OPENAI", "false").lower() == "true"

        if self.mock_openai:
            self.client = None
            return

        from openai import OpenAI

        self.client = self._create_client(OpenAI)

    def generate(self, item: NewsItem) -> tuple[str, str]:
        prompt = (
            "あなたはIT系note編集者です。\n"
            "次のニュースを題材に、読者が理解しやすく行動につながる記事を作ってください。\n"
            "条件:\n"
            "- 日本語\n"
            "- 見出し付き\n"
            "- 600〜1000文字\n"
            "- 事実と推測を分ける\n"
            "- 最後に要点3つ\n"
            f"ニュースタイトル: {item.title}\n"
            f"元URL: {item.url}\n"
            f"配信元: {item.source}\n"
        )
        if self.mock_openai:
            body = (
                "## 何が起きたか\n"
                f"{item.source} の記事『{item.title}』を題材に、ローカル検証用の下書きを生成しました。\n\n"
                "## 事実\n"
                f"- 記事タイトル: {item.title}\n"
                f"- 参照URL: {item.url}\n\n"
                "## 推測\n"
                "- 本番では OpenAI API から内容を生成します。\n"
                "- この文章は API 未接続時のモック出力です。\n\n"
                "## 要点3つ\n"
                "1. ローカルでエンドツーエンド実行確認ができる\n"
                "2. 依存外部APIなしで Markdown 出力まで確認できる\n"
                "3. APIキーを設定すれば本番生成に切り替わる\n"
            )
            title = f"【ローカル検証】{item.title}"
            return title, body

        if hasattr(self.client, "responses"):
            response = self.client.responses.create(
                model=self.model,
                input=prompt,
                temperature=0.7,
            )
            body = response.output_text.strip()
        else:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            )
            body = response.choices[0].message.content.strip()
        title = f"【最新解説】{item.title}"
        return title, body


class MarkdownStore:
    def __init__(self, output_dir: str = "output") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save(self, title: str, body: str, source_url: str) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.output_dir / f"note_{timestamp}.md"
        md = f"# {title}\n\n{body}\n\n---\n元ネタ: {source_url}\n"
        path.write_text(md, encoding="utf-8")
        return path


class NotePublisher:
    def __init__(self, mode: PublishMode, note_base_url: str = "https://note.com") -> None:
        self.mode = mode
        self.note_base_url = note_base_url.rstrip("/")

    async def publish(self, title: str, body: str) -> None:
        if self.mode == PublishMode.MANUAL:
            print("[INFO] manual モードのため、投稿は実施しません。")
            return

        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = p.chromium

            if self.mode == PublishMode.PLAYWRIGHT_EXISTING_SESSION:
                user_data_dir = os.environ.get("NOTE_USER_DATA_DIR", ".note_profile")
                context = await browser.launch_persistent_context(user_data_dir=user_data_dir, headless=False)
            else:
                context = await browser.launch_persistent_context(user_data_dir=".note_profile_tmp", headless=False)

            try:
                page = await context.new_page()
                if self.mode == PublishMode.PLAYWRIGHT_LOGIN:
                    await self._login(page)
                await self._post(page, title, body)
            finally:
                await context.close()

    async def _login(self, page: Page) -> None:
        email = os.environ.get("NOTE_EMAIL")
        password = os.environ.get("NOTE_PASSWORD")
        if not email or not password:
            raise RuntimeError("NOTE_EMAIL / NOTE_PASSWORD が未設定です。")

        await page.goto(f"{self.note_base_url}/login", wait_until="domcontentloaded")
        await page.fill('input[type="email"]', email)
        await page.fill('input[type="password"]', password)
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(3000)

    async def _post(self, page: Page, title: str, body: str) -> None:
        await page.goto(f"{self.note_base_url}/notes/new", wait_until="domcontentloaded")
        await page.fill('[placeholder="記事タイトル"]', title)
        await page.fill('textarea, [contenteditable="true"]', body)

        auto_publish = os.environ.get("NOTE_AUTO_PUBLISH", "false").lower() == "true"
        if auto_publish:
            await page.get_by_role("button", name="公開").click()
            print("[INFO] noteに自動投稿しました。")
        else:
            print("[INFO] 下書き入力まで完了。最終公開は手動で実施してください。")


async def run_pipeline(mode: PublishMode) -> PipelineResult:
    collector = NewsCollector()
    ranker = TitleRanker()
    generator = ArticleGenerator(model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"))
    store = MarkdownStore(output_dir=os.environ.get("OUTPUT_DIR", "output"))

    use_local_demo = os.environ.get("AUTOMATICNOTE_LOCAL_DEMO", "false").lower() == "true"
    if use_local_demo:
        selected = build_demo_news_item()
    else:
        items = collector.collect(limit_per_feed=int(os.environ.get("NEWS_PER_FEED", "20")))
        selected = ranker.pick_best(items)
    article_title, article_body = generator.generate(selected)
    markdown_path = store.save(article_title, article_body, selected.url)

    publisher = NotePublisher(mode=mode)
    await publisher.publish(article_title, article_body)

    return PipelineResult(
        selected=selected,
        article_title=article_title,
        article_body=article_body,
        markdown_path=markdown_path,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="最新情報を基にnote投稿を自動化するパイプライン")
    parser.add_argument(
        "--mode",
        choices=[m.value for m in PublishMode],
        default=PublishMode.PLAYWRIGHT_EXISTING_SESSION.value,
        help="投稿モード (推奨: playwright_existing_session)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = asyncio.run(run_pipeline(PublishMode(args.mode)))
    print("[DONE] selected:", result.selected.title)
    print("[DONE] markdown:", result.markdown_path)


if __name__ == "__main__":
    main()
