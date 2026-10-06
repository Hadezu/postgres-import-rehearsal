# Why this project, checked 2026-10-06

## Current offer → missing proof

The live [EN data migration service](https://work.matiushkin.com/en/services/data-migration) and [PL page](https://work.matiushkin.com/services/data-migration) offer mapping, validation, a bounded test import and reconciliation evidence. The live site was read before implementation, including the homepage and integration-testing service; the sitemap confirmed both service URLs.

Existing public repositories were read/listed directly from Hadezu's GitHub. Atomic CRM import review demonstrates browser-side preflight and explicit review outcomes. Reconciliation Evidence Workbench demonstrates offline comparisons, exact amounts, quarantine and report evidence. FastAPI Webhook Reliability demonstrates transactional integration delivery. Operations Approval Desk covers human decisions and concurrency. LLM Extraction Release Gate evaluates model outputs; Resilience4j Retry Review covers a maintenance regression. The portfolio itself covers frontend interaction.

**Missing link:** a CSV plan applied to existing relational customer data, with preserved invoices, exact review binding and a guarded inverse operation. Some database/concurrency techniques overlap earlier work; the new commercial capability is controlled import plus conservative undo, not another CSV checker.

## Primary buyer evidence

[STEMinnoKey buyer brief on Upwork](https://www.upwork.com/freelance-jobs/apply/Senior-Full-Stack-Unity-Engineer-for-Reusable-Curriculum-Multilingual-Content-Architecture_~022091358123747058304/) requests bulk import validation, preview before applying, preservation of existing IDs/relationships and a safe incremental migration/recovery path. Its larger scope also includes Unity and curriculum architecture. This example does not establish our fit for that entire role; it supplies concrete migration acceptance needs. The fetched page's relative freshness is not proof that the vacancy remains open.

[A separate buyer's FastAPI/React platform brief](https://www.upwork.com/freelance-jobs/apply/Senior-FastAPI-React-team-needed-secure-estate-financial-workpaper-platform-000-fixed-price_~022087354899035676865/) asks for inspectable delivery artifacts: source, CI evidence, schema/fixtures, documentation and a short demonstration. Its extensive production, team and security requirements remain outside this case.

These are examples, not market-share statistics or active email leads. No application/contact was made. Marketplace sources informed proof design; they do not change the email-first acquisition policy.

## Buyer and first paid slice

- Product team maintaining a relational application, migration implementer, or software house needing one import component.
- Existing customer schema, anonymized source export, agreed identity/mapping, staging access, acceptance totals and permitted write/undo scope are inputs.
- A realistic first slice: one bounded customer import in a test environment, with dry-run differences, controlled apply and evidence of refusal/recovery cases.
- No price, deadline, availability, production access or client commitment is implied.

## Acceptance criteria announced before implementation

1. Preview cannot modify business rows; it saves only review metadata.
2. Apply is tied to exact saved source, mapping, adapter and target snapshot.
3. Retry cannot duplicate an already applied plan.
4. Failed/crashed apply or undo cannot leave a partial business/ledger transaction.
5. Normal concurrent target writes invalidate stale review, including changes later reversed.
6. Undo preserves later human edits and new invoice references by refusing the entire operation.
7. Another engineer can reproduce it on real PostgreSQL; tests/CI/report/demo are inspectable.
