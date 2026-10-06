# Verification evidence

Checked 2026-10-06. This file separates local checks from remote CI; a configured workflow is not a passing run.

## Local Windows

- Python 3.14.4, PostgreSQL 18.6 (native Windows server), psycopg 3.3.6.
- 55 tests passed, zero failures/errors/skips, 49.25 seconds. JUnit was generated at `test-results/junit.xml`.
- Includes actual process death before commit (apply and undo), lost acknowledgement after commit, concurrent apply/undo, overlapping plans, a normal writer during import, lock timeout, FK failure, ABA changes, ledger failure and HTML escaping.
- Six-step demonstration ran against a separate real database with synthetic data. Its row/relationship readbacks are in `evidence/demo.json`; the HTML and video reflect those results.
- Chromium: all six steps, desktop 1280×900, mobile 390×844, keyboard activation, no page errors or page-level horizontal overflow. Desktop and mobile screenshots visually inspected. Video additionally scrolls to the actual row differences; this browser check was rerun after that recording improvement.
- Ruff lint/format passed. Source distribution and wheel built successfully.
- Installed the wheel in a second isolated environment and ran its CLI outside the source directory. This exposed a Windows legacy-encoding issue in help/output, which was fixed and covered by two additional regression tests. The rebuilt installed wheel then passed with `PYTHONIOENCODING=ascii`; Unicode row values survive through JSON escapes.

## Remote verification

[Final run 37413822459](https://github.com/Hadezu/postgres-import-rehearsal/actions/runs/37413822459) **SUCCESS**, code revision `adcd4e805ad0a23408441f3ffaaccd4ab0029f10`.

- Python 3.12 + PostgreSQL 18.6: 55 tests, zero failures/errors/skips.
- Python 3.14 + PostgreSQL 18.6: 55 tests, zero failures/errors/skips.
- Both jobs passed lint/format, actual database walkthrough, desktop/mobile/keyboard browser checks, and source/wheel packaging.
- The separate Compose job built the Docker image, started a fresh PostgreSQL instance, initialized the schema, completed all six demo states, checked the report and removed only its disposable volume.
- Both job artifacts were downloaded and their JUnit files read back. Counts/timings are preserved in `evidence/test-summary.json`.

The release documentation commit follows this verified implementation and changes only evidence/provenance metadata and this report. It does not change code, schema, dependencies, fixtures, tests or CI. Earlier successful runs (37413408638 and 37413609182) had 53 tests; they are historical evidence, not substitutes for the final 55-test run. No unexecuted check is counted as PASS.

## Limits

Small bounded fixture and targeted failure/concurrency tests, not a production load/security audit. Local Docker is unavailable; Compose was verified in Linux CI. No external database, commercial CRM, client data, production site, paid API or client mailbox was touched. Existing unrelated local website changes were left alone.
