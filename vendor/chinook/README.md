# Chinook schema provenance

Author: Luis Rocha. Upstream: https://github.com/lerocha/chinook-database

Pinned revision: `7f67772503d71ba90f19283c38e93923addb43fa`.

Source file: `ChinookDatabase/DataSources/Chinook_PostgreSql.sql` (header version 1.4.5).

`schema.sql` contains the contiguous original DDL from `CREATE TABLE album` through the final foreign-key index, with a provenance comment prepended. The database creation/deletion commands, psql connection command and **all upstream seed records** are excluded. Table/column/constraint definitions are unmodified. Eleven existing relational tables remain present, although our adapter writes only customers.

`LICENSE.md` is the unmodified upstream license at that revision (MIT-form permission text; GitHub's classifier returned NOASSERTION). It permits use, modification and redistribution with the notice retained. Our original code is separately MIT licensed at the repository root. `provenance.json` records file hashes for checking what was included.

All fixtures outside this directory were written for this independent demonstration. No upstream customer data or commercial client data is redistributed.
