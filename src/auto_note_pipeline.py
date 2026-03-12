from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterable

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


def _text_or_empty(elem: ET.Element | None) -> str:
    return (elem.text or "").strip() if elem is not None else ""


def _http_get(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "automaticnote/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


class NewsCollector:
    def __init__(self, feeds: Iterable[str] | None = None) -> None:
        self.feeds = list(feeds or DEFAULT_FEEDS)

    def collect(self, limit_per_feed: int = 20) -> list[NewsItem]:
        items: list[NewsItem] = []
        for feed_url in self.feeds:
            try:
                xml_text = _http_get(feed_url)
                items.extend(self._parse_feed(xml_text, feed_url, limit_per_feed))
            except Exception as exc:
                print(f"[WARN] RSS取得失敗: {feed_url} ({exc})")
        return [item for item in items if item.title and item.url]

    def _parse_feed(self, xml_text: str, feed_url: str, limit_per_feed: int) -> list[NewsItem]:
        root = ET.fromstring(xml_text)
        channel = root.find("channel")
        feed_title = _text_or_empty(channel.find("title") if channel is not None else None) or feed_url

        raw_items = root.findall(".//item")[:limit_per_feed]
        parsed: list[NewsItem] = []
        for entry in raw_items:
            title = _text_or_empty(entry.find("title"))
            url = _text_or_empty(entry.find("link"))
            published = self._to_datetime(_text_or_empty(entry.find("pubDate")))
            parsed.append(NewsItem(title=title, url=url, published=published, source=feed_title))
        return parsed

    @staticmethod
    def _to_datetime(pub_date: str) -> datetime:
        if not pub_date:
            return datetime.now(timezone.utc)
        try:
            from email.utils import parsedate_to_datetime

            dt = parsedate_to_datetime(pub_date)
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return datetime.now(timezone.utc)


class MCPNewsCollector:
    def __init__(self, json_path: str) -> None:
        self.json_path = Path(json_path)

    def collect(self) -> list[NewsItem]:
        raw = json.loads(self.json_path.read_text(encoding="utf-8"))
        items: list[NewsItem] = []
        for entry in raw:
            published_text = entry.get("published")
            published = datetime.fromisoformat(published_text) if published_text else datetime.now(timezone.utc)
            items.append(
                NewsItem(
                    title=entry.get("title", ""),
                    url=entry.get("url", ""),
                    source=entry.get("source", "mcp"),
                    published=published,
                )
            )
        return [item for item in items if item.title and item.url]


class TitleRanker:
    @staticmethod
    def score(item: NewsItem) -> float:
        text = item.title.lower()
        keyword_score = sum(weight for keyword, weight in TREND_KEYWORDS.items() if keyword in text)
        punctuation_score = 0.6 if re.search(r"[!！?？]", item.title) else 0.0
        title_length_score = 0.4 if 18 <= len(item.title) <= 42 else 0.0
        age_hours = max((datetime.now(timezone.utc) - item.published).total_seconds() / 3600, 0)
        recency_score = max(3.0 - (age_hours * 0.1), 0.0)
        return keyword_score + punctuation_score + title_length_score + recency_score

    def pick_best(self, items: list[NewsItem]) -> NewsItem:
        if not items:
            raise ValueError("ニュース項目が0件のため選定できません。")
        return max(items, key=self.score)


class ArticleGenerator:
    def __init__(self, model: str = "gpt-4.1-mini") -> None:
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.model = model

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
        payload = {
            "model": self.model,
            "input": prompt,
            "temperature": 0.7,
        }
        if self.api_key:
            req = urllib.request.Request(
                "https://api.openai.com/v1/responses",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                output_text = body.get("output_text", "").strip()
                if output_text:
                    return f"【最新解説】{item.title}", output_text
            except Exception as exc:
                print(f"[WARN] OpenAI生成失敗。テンプレ生成へフォールバック: {exc}")

        return f"【最新解説】{item.title}", self._fallback_generate(item)

    @staticmethod
    def _fallback_generate(item: NewsItem) -> str:
        return (
            f"## 何が起きたのか\n{item.title} というニュースが公開されました。\n\n"
            "## 事実\n"
            f"- 情報源: {item.source}\n"
            f"- 参照URL: {item.url}\n"
            "- 公開された情報から、業界の変化が進んでいることが読み取れます。\n\n"
            "## 推測\n"
            "- 企業の情報発信や投資テーマが、より短期で切り替わる可能性があります。\n"
            "- 関連市場（AI/半導体/セキュリティ等）で追加発表が続く可能性があります。\n\n"
            "## 今やるべきこと\n"
            "1. 一次情報（公式発表）を確認する\n"
            "2. 自社・自分への影響を3行で整理する\n"
            "3. 1週間以内に取る行動を決める\n\n"
            "## 要点3つ\n"
            "- ニュースの背景を事実と推測で分けて見る\n"
            "- 影響は『短期の運用』と『中長期の方針』で分けて考える\n"
            "- まずは一次情報確認→小さな行動で検証する\n"
        )



class MarkdownStore:
    def __init__(self, output_dir: str = "output") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save(self, title: str, body: str, source_url: str) -> Path:
        path = self.output_dir / f"note_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        path.write_text(f"# {title}\n\n{body}\n\n---\n元ネタ: {source_url}\n", encoding="utf-8")
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

        headless = os.environ.get("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
        async with async_playwright() as p:
            browser = p.chromium
            profile_dir = os.environ.get("NOTE_USER_DATA_DIR", ".note_profile")
            if self.mode == PublishMode.PLAYWRIGHT_LOGIN:
                profile_dir = os.environ.get("NOTE_LOGIN_TMP_PROFILE", ".note_profile_tmp")

            launch_kwargs = {"user_data_dir": profile_dir, "headless": headless}
            executable_path = os.environ.get("NOTE_CHROMIUM_EXECUTABLE")
            if executable_path:
                launch_kwargs["executable_path"] = executable_path
            context = await browser.launch_persistent_context(**launch_kwargs)
            try:
                page = await context.new_page()
                if self.mode == PublishMode.PLAYWRIGHT_LOGIN:
                    await self._login(page)
                await self._post(page, title, body)
            finally:
                await context.close()

    async def _login(self, page) -> None:
        email = os.environ.get("NOTE_EMAIL")
        password = os.environ.get("NOTE_PASSWORD")
        if not email or not password:
            raise RuntimeError("NOTE_EMAIL / NOTE_PASSWORD が未設定です。")

        await page.goto(f"{self.note_base_url}/login", wait_until="domcontentloaded")
        await page.fill('input[type="email"]', email)
        await page.fill('input[type="password"]', password)
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(5000)

    async def _post(self, page, title: str, body: str) -> None:
        await page.goto(f"{self.note_base_url}/notes/new", wait_until="domcontentloaded")

        title_candidates = ['[placeholder="記事タイトル"]', 'input[placeholder*="タイトル"]']
        for selector in title_candidates:
            if await page.locator(selector).count() > 0:
                await page.fill(selector, title)
                break
        else:
            raise RuntimeError("記事タイトル入力欄が見つかりません。")

        if await page.locator('textarea').count() > 0:
            await page.fill('textarea', body)
        elif await page.locator('[contenteditable="true"]').count() > 0:
            await page.locator('[contenteditable="true"]').first.fill(body)
        else:
            raise RuntimeError("本文入力欄が見つかりません。")

        auto_publish = os.environ.get("NOTE_AUTO_PUBLISH", "false").lower() == "true"
        if auto_publish:
            await page.get_by_role("button", name="公開").click()
            print("[INFO] noteに自動投稿しました。")
        else:
            print("[INFO] 下書き入力まで完了。最終公開は手動で実施してください。")


def collect_news() -> list[NewsItem]:
    mcp_json = os.environ.get("MCP_NEWS_JSON")
    if mcp_json:
        print(f"[INFO] MCPニュース入力を使用: {mcp_json}")
        return MCPNewsCollector(mcp_json).collect()
    return NewsCollector().collect(limit_per_feed=int(os.environ.get("NEWS_PER_FEED", "20")))


async def run_pipeline(mode: PublishMode) -> PipelineResult:
    items = collect_news()
    selected = TitleRanker().pick_best(items)
    article_title, article_body = ArticleGenerator(model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")).generate(selected)
    markdown_path = MarkdownStore(output_dir=os.environ.get("OUTPUT_DIR", "output")).save(article_title, article_body, selected.url)
    await NotePublisher(mode=mode).publish(article_title, article_body)
    return PipelineResult(selected, article_title, article_body, markdown_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="最新情報を基にnote投稿を自動化するパイプライン")
    parser.add_argument("--mode", choices=[m.value for m in PublishMode], default=PublishMode.PLAYWRIGHT_LOGIN.value)
    parser.add_argument("--fully-auto", action="store_true", help="公開ボタンまで自動実行")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.fully_auto:
        os.environ["NOTE_AUTO_PUBLISH"] = "true"
        if args.mode == PublishMode.MANUAL.value:
            raise ValueError("--fully-auto を使う場合は --mode manual 以外を指定してください。")

    result = asyncio.run(run_pipeline(PublishMode(args.mode)))
    print("[DONE] selected:", result.selected.title)
    print("[DONE] markdown:", result.markdown_path)


if __name__ == "__main__":
    main()
