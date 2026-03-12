from datetime import datetime, timedelta, timezone
import json

from src.auto_note_pipeline import MCPNewsCollector, NewsCollector, NewsItem, TitleRanker


def test_keyword_and_recency_scoring_prefers_recent_ai_news():
    now = datetime.now(timezone.utc)
    old_generic = NewsItem(
        title="国内企業の新サービス発表",
        url="https://example.com/a",
        published=now - timedelta(hours=30),
        source="example",
    )
    recent_ai = NewsItem(
        title="生成AIで業務効率化、最新トレンドを解説！",
        url="https://example.com/b",
        published=now - timedelta(hours=1),
        source="example",
    )

    ranker = TitleRanker()
    assert ranker.score(recent_ai) > ranker.score(old_generic)
    assert ranker.pick_best([old_generic, recent_ai]) == recent_ai


def test_mcp_news_collector_reads_json(tmp_path):
    payload = [
        {
            "title": "MCP News",
            "url": "https://example.com/mcp",
            "source": "mcp",
            "published": "2026-01-01T00:00:00+00:00",
        }
    ]
    file_path = tmp_path / "news.json"
    file_path.write_text(json.dumps(payload), encoding="utf-8")

    items = MCPNewsCollector(str(file_path)).collect()
    assert len(items) == 1
    assert items[0].title == "MCP News"


def test_rss_parse_works_from_xml_string():
    xml = """<?xml version='1.0'?>
<rss><channel><title>Sample Feed</title>
<item><title>生成AIの新展開</title><link>https://example.com/1</link><pubDate>Wed, 12 Mar 2025 12:00:00 +0000</pubDate></item>
</channel></rss>
"""
    collector = NewsCollector(feeds=[])
    items = collector._parse_feed(xml, "https://example.com/feed", limit_per_feed=5)
    assert len(items) == 1
    assert items[0].source == "Sample Feed"
    assert items[0].title == "生成AIの新展開"
