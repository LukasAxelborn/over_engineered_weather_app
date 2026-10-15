-- Runs once on first Postgres init (against $POSTGRES_DB == weather).
-- Create the sibling databases used by the analytics/errors profiles.
-- CREATE DATABASE cannot run inside a transaction, and the entrypoint runs
-- each file with psql (no wrapping transaction), so this is safe.

SELECT 'CREATE DATABASE umami'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'umami')\gexec

SELECT 'CREATE DATABASE glitchtip'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'glitchtip')\gexec
