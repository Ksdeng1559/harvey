# LeadSniperAI Growth Signal Engine — Harvey Integration

Status: **M0 architecture baseline / implementation plan**, not a working LeadSniperAI connection.
Branch: `feature/leadsniper-growth-signals`.

## Architectural decision

Harvey is the **agent worker** and existing discovery/signal platform. LeadSniperAI owns the multi-tenant prospect intelligence, cross-vertical opportunity registry, compliance policies and routing. Supabase/PostgreSQL is the canonical store for business identities, evidence, opportunities, approved contacts, assignments and outcomes. Atomic CRM remains the relationship/pipeline interface.

**Do not build another DataForSEO connector without checking the existing provider.** This Harvey fork v0.3.0 already documents DataForSEO Business Listings, DataForSEO SERP, `REVIEW_RATING`, `REVIEW_COUNT`, cohort filters, signal confirmation and outbox approval. Use the existing implementation as the starting point.

## Product strategies

| Strategy key | ICP | Discovery signal | Verified opportunity | Outcome |
| --- | --- | --- | --- | --- |
| `construction_jobs_appointments` | HVAC, plumbing, roofing, electrical and specialist trades in BC | High reviews rating relative to low review count; weak quote/contact flow; limited search coverage | Evidence-backed potential to improve qualified job enquiries and booked estimates | Contractor appointments, estimates and jobs won |
| `commercial_mortgage_broker_growth` | Licensed commercial mortgage brokers and their target borrower segments | Broker digital demand gaps and independent real project/borrower signals | Verified borrowing interest and permission to introduce; eligible broker/mandate | Confirmed borrower consultations, applications, funded deals |
| `business_expansion_intelligence` | Growing BC businesses and relevant service providers | New site, permits, hiring surge, acquisition, capacity investment | Separately verified requirement, decision maker and provider fit | Authorized provider appointments, contracts |

Do not infer financing demand from a low review count, and do not equate an expansion announcement with consent or current buying intent.

## M0 repository inspection tasks

1. Confirm all existing discovery providers, DataForSEO API invocation/filters, the signals catalog, cohort query, profile enrichment, persistence and CLI interfaces.
2. Identify configuration/auth, database migrations, agent skills, dashboard and outbound approval dependencies. Keep existing behavior backward compatible.
3. Map tenant/strategy context into a `client.brain.md` schema; do not bake one client's ICP into global Harvey config.
4. Inventory external licensing/retention and Canadian CASL/privacy/licensed-broker referral constraints. Keep sending disabled for new strategies until independently approved.
5. Publish tests for current discovery and signal behavior before changing providers.

## M1 initial integration slice

- Add a **LeadSniperAI export / adapter boundary**, not a parallel DataForSEO connector. Prefer a small typed interface that extracts canonical business, location, source identifiers, rating, review count, website, timestamps, observation provenance and run cost.
- Support dry-run and mock backend, secrets in environment only, idempotency keys and per-run spend/record caps.
- Identity resolve by stable provider identifiers, normalized domain/phone/address; put uncertain branches/franchises into manual review.
- Record source-observation date separately from ingestion timestamp; mark missing fields unknown.
- Keep original Harvey SQLite operational data intact while synchronizing approved canonical records to Supabase by an authenticated server-side service.
- No automatic emails or external lead handoff in M1.

## M2 opportunity-classification logic

**Construction hidden gem baseline (pilot rule):** rating >=4.5, review count 10–50, below half of comparable cohort median, at least 15 comparable local category peers. Use shrinkage-adjusted ratings; benchmark is inconclusive when the cohort is biased or too small. Independently investigate visible quote/booking friction. A gap is a research hypothesis, not proof of lost jobs.

**Broker growth:** separate brokerage-firm marketing diagnosis from borrower origination. Borrower lead status requires first-party verified interest, geography/property/mandate fit, consent and documented broker eligibility.

**Expansion:** require dated sourced events; status `weak_indicator | announced | implementation | operational`. Route to providers only after validation of service need and permissions.

Each result should expose evidence URLs, fact vs hypothesis, score, separate evidence-confidence value, last verified, suggested offer, compliance state, human approval and an auditable next action.

## Suggested schemas (adapt to actual codebase)

```python
from dataclasses import dataclass
from typing import Literal

Strategy = Literal[
    "construction_jobs_appointments",
    "commercial_mortgage_broker_growth",
    "business_expansion_intelligence",
]

@dataclass(frozen=True)
class ObservationExport:
    company_external_key: str
    provider: str
    field: str
    value: str | float | int | None
    observed_at: str | None
    retrieved_at: str
    source_url: str | None
    confidence: float | None

@dataclass(frozen=True)
class OpportunityExport:
    tenant_id: str
    strategy: Strategy
    company_key: str
    evidence_keys: list[str]
    hypothesis: str
    need_verified: bool
    requires_human_approval: bool = True
```

Build actual serialization/validation with the repository's established conventions, not direct unvalidated dict persistence. Prefer adapter APIs and provider-neutral types.

## Quality and security gates

- 100% outbound messages require documented human review and applicable CASL basis, identification/unsubscribe/suppression controls.
- Zero unauthorized cross-tenant access via automated tests; only service-to-service credential handles sensitive synchronization.
- >=95% entity matching precision over a manually audited 100-record pilot sample.
- >=90% supported factual claims across 50 human-audited opportunity briefs.
- Every pilot job has cost ceiling, duplicate control, result provenance, logs and safe retries.
- No loan qualification claims based solely on publicly observed business signals.
- A booking is counted only after calendar confirmation; distinguish our B2B prospect demos from the contractor's own customer bookings.

## Claude Code execution sequence

1. Read this document, current `README.md`, `CLAUDE.md`, signal/provider code and tests.
2. Execute M0 audit and update this plan with **actual filenames, classes and integration seams** before coding.
3. Implement M1 on a separate PR, including tests, environment variable template, rollback, README and a dry-run example.
4. Only after passing M1, implement M2 classifiers and score calibration.
5. After that, add Supabase/Atomic CRM sync, approval queue, scheduling and outcome attribution.
6. Report test commands, verified results, files changed and any blockers. Do not claim live integrations until tested.

## Source documents

- [LeadSniperAI implementation specification](https://app.notion.com/p/3fc9e94cf0a481d1ad98d01f9bfaf95c)
- [LeadSniperAI reusable prospecting skill](https://app.notion.com/p/3fc9e94cf0a4816d93d1e5cd48091107)
- [Original Harvey](https://github.com/ethanplusai/harvey)
