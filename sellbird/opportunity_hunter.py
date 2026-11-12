"""Website Opportunity Hunter: import Notion leads, audit public sites, export review queue.

Run: python -m sellbird.opportunity_hunter --notion-data-source ID --out leads.json
Requires NOTION_API_TOKEN. No emails are sent and no previews are deployed.
"""
import argparse
import asyncio
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx

from sellbird.public_http import public_http_client

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
MAX_PAGE_BYTES = 1024 * 1024


def _plain(prop):
    if not isinstance(prop, dict):
        return ""
    kind = prop.get("type", "")
    if kind in ("title", "rich_text"):
        return "".join(i.get("plain_text", "") for i in prop.get(kind, []))
    if kind in ("url", "email", "phone_number"):
        return prop.get(kind) or ""
    if kind in ("select", "status"):
        return (prop.get(kind) or {}).get("name", "")
    return ""


def normalize_notion_page(page):
    fields = {name.lower().strip(): _plain(value) for name, value in page.get("properties", {}).items()}
    def choose(*keys):
        return next((fields[k] for k in keys if fields.get(k)), "")
    return {
        "source_id": page["id"],
        "source_url": page.get("url", ""),
        "company": choose("name", "business", "business name", "company", "title"),
        "website": choose("website", "website url", "url", "domain"),
        "industry": choose("industry", "category"),
        "city": choose("city", "location"),
        "maps_url": choose("google maps", "maps link", "gmb link", "google business profile"),
        "email": choose("email", "contact email"),
    }


async def import_notion(data_source_id, token, *, max_pages=200):
    """Read Notion database/data source rows with pagination; no writes."""
    if not token:
        raise ValueError("NOTION_API_TOKEN is required")
    results, cursor = [], None
    headers = {"Authorization": f"Bearer {token}", "Notion-Version": NOTION_VERSION}
    # Notion's 2022 API queries a database ID, including single-source databases.
    async with httpx.AsyncClient(timeout=25, trust_env=False) as client:
        while len(results) < max_pages:
            payload = {"page_size": min(100, max_pages - len(results))}
            if cursor:
                payload["start_cursor"] = cursor
            response = await client.post(f"{NOTION_API}/databases/{data_source_id}/query",
                                         headers=headers, json=payload)
            response.raise_for_status()
            obj = response.json()
            results.extend(normalize_notion_page(p) for p in obj.get("results", []))
            cursor = obj.get("next_cursor")
            if not obj.get("has_more") or not cursor:
                break
    return results


def _url(value):
    value = (value or "").strip()
    if not value:
        return ""
    if "://" in value and not re.match(r"^https?://", value, re.I):
        return ""
    if not re.match(r"^https?://", value, re.I):
        value = "https://" + value
    parts = urlparse(value)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
        return ""
    return value


def score_html(html, *, missing_website=False):
    """Explainable lead score, not a claim about a site's actual age."""
    if missing_website:
        return {"score": 90, "findings": ["No website listed"], "confidence": "listing_only"}
    s = html.lower()
    findings, score = [], 0
    tests = [
        (not re.search(r'<meta[^>]+name=["\']viewport["\']', s), 25, "Mobile viewport tag absent"),
        (not re.search(r'<meta[^>]+name=["\']description["\']', s), 10, "Meta description absent"),
        ('application/ld+json' not in s, 15, "Structured data not detected"),
        (not re.search(r'<form\b', s), 15, "No HTML lead form detected"),
        (not re.search(r'booking|book now|schedule|appointment', s), 10, "Online booking not detected"),
        (not re.search(r'<h1\b', s), 10, "Page H1 absent"),
        (not re.search(r'tel:|mailto:', s), 10, "Click-to-call/email links not detected"),
        (not re.search(r'og:title|og:description', s), 5, "Open Graph metadata absent"),
    ]
    for failure, points, reason in tests:
        if failure:
            score += points
            findings.append(reason)
    return {"score": score, "findings": findings, "confidence": "homepage_html_only"}


async def audit_lead(lead):
    result = {**lead, "audit_status": "unreviewed", "preview_status": "approval_required"}
    url = _url(lead.get("website"))
    if not url:
        result.update(score_html("", missing_website=True))
        result["audit_status"] = "no_website_listed"
        return result
    try:
        async with public_http_client(timeout=httpx.Timeout(15.0)) as client:
            async with client.stream("GET", url, headers={"User-Agent": "Sellbird-OpportunityAudit/1.0"}) as response:
                response.raise_for_status()
                if "text/html" not in response.headers.get("content-type", ""):
                    raise ValueError("Not an HTML page")
                chunks, size = [], 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > MAX_PAGE_BYTES:
                        raise ValueError("HTML response exceeds size limit")
                    chunks.append(chunk)
                html = b"".join(chunks).decode("utf-8", errors="replace")
        result.update(score_html(html))
        result.update({"audit_status": "audited", "audited_url": str(response.url)})
    except (httpx.HTTPError, ValueError) as exc:
        result.update({"audit_status": "audit_failed", "audit_error": str(exc)[:180],
                       "score": None, "findings": [], "confidence": "unverified"})
    return result


async def run(args):
    if args.input_json:
        rows = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            raise ValueError("JSON input must be an array of company records")
    else:
        rows = await import_notion(args.notion_data_source, os.getenv("NOTION_API_TOKEN", ""),
                                  max_pages=args.limit)
    rows = rows[:args.limit]
    # Small concurrency protects target sites; avoid aggressively crawling businesses.
    semaphore = asyncio.Semaphore(3)
    async def one(row):
        async with semaphore:
            return await audit_lead(row)
    scored = await asyncio.gather(*(one(r) for r in rows))
    scored.sort(key=lambda p: (p.get("score") is None, -(p.get("score") or 0)))
    output = {"workflow": "sales-bird-website-opportunity-hunter",
              "disclaimer": "Heuristic HTML checks only; visual design, speed, accessibility, ROI, and business fit require manual/independent review.",
              "leads": scored}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(scored)} leads to {args.out}. No websites deployed or emails sent.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--notion-data-source", help="Notion database ID, shared with the integration")
    source.add_argument("--input-json", help="List of lead records exported from Notion")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--out", default="data/opportunity-leads.json")
    args = parser.parse_args()
    if not 1 <= args.limit <= 1000:
        parser.error("--limit must be 1..1000")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
