# FlavorMap

A computational geography of Thai cuisine: an ingredient co-occurrence network built from
recipes across Thailand's 77 provinces, analyzed for regional structure and released as an
open dataset and interactive map.

**Primary research question:** do ingredient co-occurrence patterns in Thai home cooking vary
systematically by province — and if so, do those patterns correlate more strongly with
geographic proximity, historical trade routes, or linguistic/ethnic boundaries?

## Research questions

- **RQ1** — What are the most central ingredients in Thai cuisine overall, across all regions?
- **RQ2** — Do regional ingredient communities emerge from the network, and do they align with
  Thailand's four geographic regions?
- **RQ3** — Which provinces have the most distinctive cuisine — ingredients that appear almost
  exclusively in their recipes?
- **RQ4** — Does culinary similarity between provinces correlate with geographic distance,
  linguistic boundaries, or national borders?
- **RQ5** — Can a machine learning model predict a dish's province of origin from its
  ingredients alone, and where does it fail?

See [CLAUDE.md](CLAUDE.md) for the full build plan, non-negotiable rules, data model, and
execution schedule.

## Setup

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (Docker Desktop, OrbStack, or equivalent) —
  the database is local PostgreSQL 15 + PostGIS, not a hosted service
- [`uv`](https://docs.astral.sh/uv/) for Python 3.11 dependency management
- An Anthropic API key

### Install

```bash
cp .env.example .env
# edit .env: set POSTGRES_PASSWORD (and mirror it into DATABASE_URL),
# ANTHROPIC_API_KEY, and SCRAPER_CONTACT_EMAIL

make setup   # starts Postgres+PostGIS via Docker Compose, waits for it to be
             # healthy, installs Python dependencies with uv, and applies
             # db/migrations/*.sql
```

### Run the tests

```bash
make test    # pytest + ruff + mypy
```

### Everyday commands

| Command | What it does |
|---|---|
| `make setup` | Start the database, install dependencies, apply migrations |
| `make test` | Run the test suite, linter, and type checker |
| `scripts/dump_db.sh` | Dump the local database to `data/exports/` |
| `scripts/restore_db.sh <dump.sql.gz>` | Restore the database from a dump |

The rest of the pipeline (`scrape`, `ingest`, `clean`, `analyze`, `vision`, `figures`, `api`,
`web`, `export`) is scaffolded in the `Makefile` and built out phase by phase — see
[CLAUDE.md](CLAUDE.md) for what's live and what's still a stub.
