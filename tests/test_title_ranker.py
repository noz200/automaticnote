from datetime import datetime, timedelta, timezone

from src.auto_note_pipeline import NewsItem, TitleRanker


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
