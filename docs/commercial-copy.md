# Prepared copy — not published to the production website

## Relevant pages

- EN: https://work.matiushkin.com/en/services/data-migration
- PL: https://work.matiushkin.com/services/data-migration
- Existing migration demo: https://work.matiushkin.com/en/proof/migration
- Repository: https://github.com/Hadezu/postgres-import-rehearsal

## EN portfolio block

**Reviewed imports with guarded undo**

An independent PostgreSQL example extending the open-source Chinook schema. Preview customer changes, apply the exact reviewed plan and retry without duplicate records. Tests demonstrate transaction recovery after process failure, stale-plan refusal and an undo that refuses to overwrite later changes or remove a customer with new invoices. Includes a reproducible database, source, CI and a short demonstration. Synthetic data; not a client migration.

## PL portfolio block

**Import z podglądem zmian i kontrolowanym wycofaniem**

Niezależny przykład oparty na PostgreSQL i otwartym schemacie Chinook. Pokazuje podgląd zmian klientów, wykonanie sprawdzonego planu i ponowienie bez duplikowania rekordów. Testy obejmują awarię procesu, nieaktualny plan oraz odmowę wycofania zmian, gdy naruszyłoby to późniejsze edycje lub powiązane faktury. Kod, odtwarzalna baza, CI i krótka demonstracja. Dane syntetyczne; nie jest to migracja wykonana dla klienta.

## One relevant email sentence

Use only after reading the buyer's actual request; this is not a universal opening.

EN: “For the import preview and rollback part of your project, I built a related PostgreSQL example: [reviewed import and guarded undo](https://github.com/Hadezu/postgres-import-rehearsal). It shows what happens when the process fails or someone edits the data after review; it uses synthetic data.”

PL: “W kontekście podglądu importu i wycofywania zmian przygotowałem podobny przykład w PostgreSQL: [import z kontrolowanym wycofaniem](https://github.com/Hadezu/postgres-import-rehearsal). Pokazuje również awarię procesu i edycję danych po sprawdzeniu planu; korzysta z danych syntetycznych.”

Do not attach every repository. Send this when controlled data changes, recovery or relational integrity are the relevant requirement. Reply with the exact examples/details the buyer asks for.

## Qualification boundaries

- `DIRECT_PROOF_FIT`: bounded Python/PostgreSQL customer import, validation, transactions, conflict handling and inspectable evidence.
- `PROOF_COMPENSABLE_EXPERIENCE_GAP`: buyer accepts an implemented related example instead of identical-domain history; verify that explicitly.
- `HARD_EXPERIENCE_GATE`: mandatory client references, certified ERP experience, commercial years, regulated migration sign-off or production-scale history. This repository does not satisfy those gates.
- `REQUIREMENT_AMBIGUOUS_VERIFY`: unknown target schema, zero-downtime promise, large volumes, multi-table mapping, production access, or a buyer who has not stated whether independent examples are acceptable.

Search families: PostgreSQL import contractor; CSV migration dry run project; data migration validation contractor; existing database import rollback; software house data migration subcontractor. Queries are discovery inputs, not evidence of paid demand. Require an actual paid external task and a published permissible email route. No lead/contact, price, deadline, CV, platform submission or site deployment was made by this project.
