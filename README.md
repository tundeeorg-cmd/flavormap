# FlavorMap

A computational geography of Thai cuisine: an ingredient co-occurrence network built from
recipes across Thailand's 77 provinces, analyzed for regional structure and released as an
open dataset and interactive map.

> The data that exists about a population is not the truth about that population,
> and the gap widens with distance from the centre.

## Research questions

**RQ1 — How far do you travel before the food changes, and does it change gradually or all at once?**
<sub>Are cultural boundaries discrete or continuous, and can they be located from compositional data alone? Distance-decay curve with change-point detection; one competing boundary set (linguistic).</sub>

**RQ2 — Is a region's food about what it uses, or about what it refuses to use?**
<sub>Is culinary distinctiveness constituted by inclusion or by exclusion? Distinctiveness decomposed into presence-driven and absence-driven components, validated against stated absences from interviews.</sub>

**RQ3 — Whose cooking did the internet leave out?**
<sub>How much of Thailand's culinary map is legible at all from public online data? Coverage cartography: labelled fraction, provincial recipe counts, source-domain concentration, and how conclusions move as the inclusion threshold varies.</sub>

**RQ4 — What happens if all the garlic in Thailand disappears?**
<sub>Which ingredients hold the cuisine together, and which regional cuisines are most fragile? Node-removal robustness on the PMI-weighted co-occurrence network.</sub>

**RQ5 — Is the food Thailand is famous for the least regional food it has?**
<sub>Does regional signal concentrate in vernacular practice rather than in canonical, externally-facing forms? Classifier run separately per dish category, with the majority-class baseline reported.</sub>

Every question is framed so that a null answer is reportable. Predictions are registered in
[docs/hypotheses.md](docs/hypotheses.md) before any analysis runs, and the negative results
carry full weight in the paper rather than sitting in a footnote.

See [CLAUDE.md](CLAUDE.md) for the build plan, non-negotiable rules, data model, and
execution schedule; [docs/limitations.md](docs/limitations.md) for what this data cannot
support; and [docs/decisions.md](docs/decisions.md) for every judgment call and its reasoning.

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
