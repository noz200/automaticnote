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


@dataclass
class AgentTask:
    role: str
    mission: str
    output_format: str


load_dotenv()


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

    @staticmethod
    def _build_agent_tasks() -> list[AgentTask]:
        return [
            AgentTask(
                role="Market Analyst",
                mission="ニュースの本質と、読者が誤解しやすいポイントを分解する。",
                output_format="箇条書きで論点整理",
            ),
            AgentTask(
                role="Opportunity Designer",
                mission="読者の未来が前向きに変わる可能性、具体的な行動、狙うべき細分化市場を示す。",
                output_format="現実的な打ち手を3〜5個",
            ),
            AgentTask(
                role="Note Writer",
                mission="伴走者として、煽りすぎず、それでも未来が変わる感のある note 記事にまとめる。",
                output_format="見出し付きの完成原稿",
            ),
        ]

    @classmethod
    def _build_prompt(cls, item: NewsItem) -> str:
        agent_section = "\n".join(
            [
                f"- {task.role}: {task.mission} / 出力形式: {task.output_format}"
                for task in cls._build_agent_tasks()
            ]
        )
        return (
            "あなたは note のサブスク記事を作る編集チームです。\n"
            "記事の目的は、読者に『未来が変わるかもしれない』『自分にも次の一歩がある』と感じさせることです。\n"
            "ただし、誇大表現・情弱搾取・楽して稼げる系の煽りは禁止です。\n"
            "『不安を解消する』『伴走する』『具体的な一歩を提示する』ことを優先してください。\n\n"
            "## 前提\n"
            "- 日本語\n"
            "- note向け\n"
            "- 見出し付き\n"
            "- 800〜1500文字\n"
            "- 事実と推測を分ける\n"
            "- 読者が誤解しやすいポイントを分解する\n"
            "- 最後に『今日からできる次の一歩』を3つ入れる\n"
            "- トーンは『少し先を歩く実践者』\n"
            "- 市場・需要・競争の観点を入れる\n\n"
            "## 役割分担エージェント\n"
            f"{agent_section}\n\n"
            "## 記事で必ず扱う観点\n"
            "- これは単なる自動化の仕組みなのか、それとも価値のある市場機会なのか\n"
            "- 稼げる/伸びる本質は『仕組み』ではなく『何を自動化するか』であること\n"
            "- 競争が激しい領域と、細分化すると勝てる領域の違い\n"
            "- 読者が次に試すべき、小さく現実的なアクション\n\n"
            "## 入力ニュース\n"
            f"- タイトル: {item.title}\n"
            f"- URL: {item.url}\n"
            f"- 配信元: {item.source}\n"
        )

    def generate(self, item: NewsItem) -> tuple[str, str]:
        prompt = self._build_prompt(item)
        if self.mock_openai:
            body = (
                "## このニュースの本質\n"
                f"{item.source} の記事『{item.title}』は、単なるツール紹介ではなく、"
                "『何を自動化すると価値になるのか』を考える材料になります。\n\n"
                "## 誤解しやすいポイント\n"
                "- 自動化そのものが価値なのではなく、需要のある課題に当てることが重要です。\n"
                "- 競争の激しい領域では、量産だけでは埋もれます。\n\n"
                "## 未来が変わる見方\n"
                "- 読者自身の経験や失敗を、細分化されたニーズに変換すると強みになります。\n"
                "- 『一歩先を歩く伴走者』として発信すると、継続課金に繋がりやすくなります。\n\n"
                "## 今日からできる次の一歩\n"
                "1. 自分が最近ハマった失敗や非効率を3つ書き出す\n"
                "2. その中で『お金を払ってでも解決したい人がいそうなもの』を1つ選ぶ\n"
                "3. 小さな検証記事かツール案として形にする\n"
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
