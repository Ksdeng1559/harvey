# Sales Bird: Website Opportunity Hunter (pilot)

This feature adds a **read-only** Notion lead importer, safe homepage HTML checks and ranked JSON output for human review.

## Setup

1. Share the prospect database with your Notion integration. Set `NOTION_API_TOKEN` in your local environment (never commit it).
2. Install the existing Sellbird dependencies (`pip install -e .`).
3. Run `python -m sellbird.opportunity_hunter --notion-data-source YOUR_DATABASE_ID --limit 10 --out data/opportunity-leads.json`.
4. Or pass a previously exported JSON array with `--input-json leads.json` (company, website, industry, city, maps_url, email).

The output contains evidence findings, a 0-100 **opportunity heuristic**, confidence, source links, audit failures and a required preview-approval status. It does **not** prove a website is old, poorly performing or that a business will buy.

## Website factory / Netlify handoff contract

After reviewing qualified leads, the website factory can read the JSON and accept an approved request:

```json
{
  "company": "Sample Repair",
  "source_id": "notion-page-id",
  "website": "https://example.com",
  "reviewed": true,
  "preview_only": true,
  "publish_publicly": false,
  "template": "astro-local-service",
  "destination": "netlify"
}
```

The factory should build an Astro staging site, label it an **unofficial concept**, use only licensed images and verified business details, avoid pretending to be the business, and return a preview URL and build log. Never automatically contact leads or deploy a site as the prospect's official website.

**Not yet implemented:** Notion write-back, browser-based visual QA, Google PageSpeed API, actual Astro factory invocation, Netlify API deployment, and delivery of proposals. These need separate adapters and credentials. Existing Sellbird outgoing mail still requires its independent approval controls. For Canadian prospects, evaluate CASL consent requirements before outreach.

## Next improvements

Add a review queue that records `qualified`, `preview_approved`, `preview_url`, and `proposal_approved` in Notion; integrate PageSpeed and business-value modeling; connect the website factory's build endpoint; then stage approved builds on Netlify with restricted access.
