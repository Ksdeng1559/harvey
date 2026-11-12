from sellbird.opportunity_hunter import normalize_notion_page, score_html, _url


def test_no_site_is_explicitly_unverified():
    out = score_html("", missing_website=True)
    assert out["score"] == 90
    assert out["confidence"] == "listing_only"


def test_full_markup_scores_zero():
    html = """<html><head><meta name="viewport" content="width=device-width"><meta name="description" content="x"><meta property="og:title" content="x"><script type="application/ld+json">{}</script></head><body><h1>Hi</h1><form></form><a href="tel:123">Call</a><a href="/booking">Book now</a></body></html>"""
    assert score_html(html)["score"] == 0


def test_notion_page_normalization():
    page = {"id": "p1", "url": "https://notion.so/p1", "properties": {
        "Business Name": {"type": "title", "title": [{"plain_text": "Sample Auto"}]},
        "Website": {"type": "url", "url": "https://example.org"}
    }}
    assert normalize_notion_page(page)["company"] == "Sample Auto"
    assert normalize_notion_page(page)["website"] == "https://example.org"


def test_invalid_url_rejected():
    assert _url("file:///etc/passwd") == ""
    assert _url("https://user:pass@example.com") == ""
