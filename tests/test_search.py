from app.models.schemas import Passage
from app.services.search.filters import filter_passages, is_junk_url
from app.services.search.query_builder import build_web_queries, is_academic_query, mentions_youtube


def test_youtube_query_is_not_academic():
    assert not is_academic_query("best youtube channel for system design")


def test_build_web_queries_includes_youtube_site_search():
    queries = build_web_queries(
        "best youtube channel for preparing for system design",
        "Which YouTube channels teach system design interviews?",
    )
    assert any("site:youtube.com" in q for q in queries)
    assert any("system design" in q.lower() for q in queries)


def test_filter_removes_junk_urls():
    passages = [
        Passage(
            text="Shop electronics at Best Buy",
            url="https://www.bestbuy.com",
            title="Best Buy",
            source="duckduckgo",
        ),
        Passage(
            text="Gaurav Sen covers system design interviews in depth",
            url="https://www.youtube.com/@gkcs",
            title="Gaurav Sen - System Design",
            source="duckduckgo",
        ),
    ]
    filtered = filter_passages(passages, "best youtube channel system design")
    assert len(filtered) == 1
    assert "youtube.com" in filtered[0].url


def test_is_junk_youtube_homepage():
    assert is_junk_url("https://www.youtube.com/")
    assert not is_junk_url("https://www.youtube.com/@gkcs")
