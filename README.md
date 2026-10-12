# FlavorMap

Thai regional cooking recorded three times, by three actors with three different motives:
the state (231 Department of Cultural Promotion forms, 3 dishes per province), the market
(recipe websites) and the kitchen (interviews with home cooks in Nakhon Ratchasima and
Buri Ram). The gaps between those records are the finding. Released as two open datasets
and an interactive map.

> The data that exists about a population is not the truth about that population,
> and the gap widens with distance from the centre.

## Research questions

**RQ1: Does the food the government picks to represent your province match what people there actually cook?**
<sub>Do the state, the market and the kitchen agree on what a province eats? Pairwise cosine distance between the three registers' ingredient profiles, per province.</sub>

**RQ2: Is a region's food about what it uses, or about what it refuses to use?**
<sub>Is regional identity built from what's included or what's refused? Distinctiveness decomposed into presence-driven and absence-driven components, validated against absences cooks state in interviews.</sub>

**RQ3: Whose cooking didn't make the government's list?**
<sub>What does the official record leave out? Dish- and ingredient-level overlap between the state's three dishes per province and what cooks report.</sub>

**RQ4: After the computer cleans up a recipe, is it still a recipe?**
<sub>Can you cook a dish from the normalised dataset? Eight dishes cooked from the cleaned ingredient lists, with what survived, degraded or was lost.</sub>

**RQ5: The government says these dishes are at risk. Do the people who cook them agree?**
<sub>Do cooks agree with the state about which dishes are disappearing? The government forms' endangerment level compared with what cooks report.</sub>

Four of the five depend on fieldwork and one on cooking. Every question is framed so that a
null answer is reportable, and negative results carry full weight in the paper. The full
statement of each question is in [docs/research_questions.md](docs/research_questions.md).
Predictions go in [docs/hypotheses.md](docs/hypotheses.md) before any analysis runs.

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
| `make verify` | Fresh-clone check: apply every migration to a throwaway empty database and run the full suite there. Never touches your live database |
| `scripts/dump_db.sh` | Dump the local database to `data/exports/` |
| `scripts/restore_db.sh <dump.sql.gz>` | Restore the database from a dump. Refuses a database that already has tables unless given `--force`. Restores into a staging copy first, stops at the first error, and replaces the target only on success. `--db NAME` restores into a different database, e.g. to check a dump without touching the live one |

The rest of the pipeline (`scrape`, `ingest`, `clean`, `analyze`, `vision`, `figures`, `api`,
`web`, `export`) is scaffolded in the `Makefile` and built out phase by phase — see
[CLAUDE.md](CLAUDE.md) for what's live and what's still a stub.

### Backing up off this laptop

```bash
make backup TO=/Volumes/YourDrive
```

This encrypts the fieldwork interview files and the newest database dump into one file
on an external drive or a cloud-synced folder: iCloud Drive, or a Google Drive, OneDrive
or Dropbox folder inside `~/Library/CloudStorage/`. It refuses any other folder on this
laptop's own disk. A synced copy is safe only once it has finished uploading. gpg asks for a passphrase; **lose it and the backup cannot be opened**, so keep
it somewhere safe. The backup is checked before it reports success. To restore:
`gpg --decrypt <file>.tar.gz.gpg | tar -xz`, then `scripts/restore_db.sh --force` on the
dump inside, and copy the interview files back into `data/interviews/`.

### Checking progress

```bash
make status            # print a snapshot to the terminal
make status-snapshot   # write it to data/coverage/status_YYYY-MM-DD.md for committing
```

`make status` prints row counts, province coverage per register, lexicon health,
migrations, whether the database container is up, backup age, the latest decision, and
whether each research question's input data exists yet. Questions waiting on fieldwork
show as `blocked-on-fieldwork`, not as failures. It never writes to the database, and any
line it can't compute shows `n/a`, so it also runs on a fresh clone.

`make status-snapshot` writes the same report in aggregate form (counts only, with no
per-province name lists), so it can be committed to this public repo. Commit one now and
then, and the project's progress shows up in git history.

---

## Author

**Jenissa Vichiansin**  
International School Bangkok

---

## License

MIT — see [LICENSE](LICENSE)
