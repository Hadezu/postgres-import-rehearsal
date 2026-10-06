# Verification evidence

Checked 2026-10-06. This file separates local checks from remote CI; a configured workflow is not a passing run.

## Local Windows

- Python 3.14.4, PostgreSQL 18.6 (native Windows server), psycopg 3.3.6.
- 53 tests passed, zero failures/skips, 44.71 seconds. JUnit was generated at `test-results/junit.xml`.
- Includes actual process death before commit (apply and undo), lost acknowledgement after commit, concurrent apply/undo, overlapping plans, a normal writer during import, lock timeout, FK failure, ABA changes, ledger failure and HTML escaping.
- Six-step demonstration ran against a separate real database with synthetic data. Its row/relationship readbacks are in `evidence/demo.json`; the HTML and video reflect those results.
- Chromium: all six steps, desktop 1280×900, mobile 390×844, keyboard activation, no page errors or page-level horizontal overflow. Desktop screenshot visually inspected.
- Ruff lint/format passed. Source distribution and wheel built successfully.

## Remote verification

GitHub Actions will run the same tests on Python 3.12 and 3.14 with PostgreSQL 18.6, browser checks, packaging and a separate fresh Docker Compose walkthrough. Status pending until an actual run is inspected; this section will be updated before delivery.

## Limits

Small bounded fixture and targeted failure/concurrency tests, not a production load/security audit. Local Docker is unavailable; Compose is to be verified in CI. No external database, commercial CRM, client data, production site, paid API or client mailbox was touched. Existing unrelated local website changes were left alone.
