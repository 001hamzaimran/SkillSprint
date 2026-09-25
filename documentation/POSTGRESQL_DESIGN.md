# PostgreSQL persistence design

SkillSprint now uses PostgreSQL through `psycopg`. `DATABASE_URL` selects the PostgreSQL database and `POSTGRES_SCHEMA` isolates one workspace or test run.

Each application collection is represented by a PostgreSQL table with a text primary key and a JSONB document column. This preserves the existing versioned source, plan snapshot, rubric and audit structures while moving durability, transactions, locking and backups to PostgreSQL. GIN indexes are created for JSONB lookup, and application-level uniqueness rules retain the previous business constraints.

The database layer in `app/db.py` supplies the limited collection/query interface used by the business modules. Atomic job claims and conditional updates acquire PostgreSQL table locks inside transactions. Tests use disposable PostgreSQL schemas rather than disposable MongoDB databases.

Current tables include users, sessions, password resets, login limits, job roles, employees, documents, source sections, requirements, jobs, plans, audit events, plan reviews, learning progress, quiz attempts, practical submissions, conflict resolutions and consistency experiments.

Original uploaded files remain outside PostgreSQL in private storage. Back up the PostgreSQL database and `uploads/` together.
