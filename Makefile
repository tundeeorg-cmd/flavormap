.PHONY: setup db-up db-down db-reset db-dump scrape scrape-dcp scrape-kapook ingest cook-along lexicon interviews backup dcp-manual status status-snapshot clean analyze vision figures api web export test all verify

setup: db-up
	uv sync
	uv run playwright install
	uv run python -m scripts.migrate

db-up:
	docker compose up -d --wait

db-down:
	docker compose down

# DESTROYS THE LIVE DATABASE VOLUME, and every row in it. Not needed for restores
# (scripts/restore_db.sh --force replaces a database safely) or for verification
# (make verify uses a throwaway stack). Take `make db-dump` first if you run this.
db-reset:
	docker compose down -v
	docker compose up -d --wait
	uv run python -m scripts.migrate

# HD-31: encrypted off-laptop backup of the interview files and the newest dump.
#   make backup TO=/Volumes/YourDrive
# Refuses a destination on the laptop's own disk; gpg asks for the passphrase.
backup:
	@test -n "$(TO)" || (echo "Usage: make backup TO=/path/to/external/drive" >&2; exit 1)
	./scripts/backup.sh "$(TO)"

# Timestamped, gzip-compressed pg_dump to data/exports/ (gitignored) — scripts/dump_db.sh.
# Carries the full parsed corpus, so it never leaves the machine it was taken on.
db-dump:
	./scripts/dump_db.sh

# Fetch only, per source — writes to data/raw/{source}/ (gitignored), touches no
# database. Both are resumable: neither fetcher re-requests a file already on disk, so
# re-running after a partial run only requests what is still missing.
scrape-dcp:
	uv run python -m scripts.fetch_dcp_food

scrape-kapook:
	uv run python -m scripts.fetch_kapook

scrape: scrape-dcp scrape-kapook

# Fetch, then parse-and-load both sources. `ingest` depends on `scrape` so `make ingest`
# alone takes a fresh clone all the way to a loaded `recipes` table; `make scrape` (or a
# single `scrape-*` target) on its own still works for re-fetching without touching the
# database.
#
# kapook_cooking loads under HD-22 option C only (docs/decisions.md, decided
# 2026-09-12): a page becomes a `recipes` row only when it carries exactly one
# ingredient section — the unambiguous case. Multi-section pages (roundups, or one dish
# split across sections) still get a raw_recipes row, just no recipes row, pending the
# rest of HD-22.
ingest: scrape
	uv run python -m scripts.parse_dcp
	uv run python -m scripts.parse_kapook

# HD-6/HD-10 — the hand-authored lexicon (data/reference/lexicon/*.csv) into
# canonical_ingredients, ingredient_aliases and ingredient_conflations. All-or-nothing;
# nothing is ever deleted.
lexicon:
	uv run python -m scripts.load_lexicon

# HD-35 — hand-transcribed DCP forms (data/dcp_manual/*.toml, gitignored) for documents
# with no text layer. Flagged extraction_method='manual'. All-or-nothing.
dcp-manual:
	uv run python -m scripts.load_dcp_manual

# HD-29/HD-30 — fieldwork interview files (data/interviews/*.toml, gitignored) into
# informants, interview_dishes and the domestic register. All-or-nothing; refuses any
# file without consent or with personal data.
interviews:
	uv run python -m scripts.load_interviews

# RQ4 — hand-written cook-along logs (data/cook_along/*.toml) into cook_along_log.
# All-or-nothing: one invalid file, including one carrying personal data, loads none.
cook-along:
	uv run python -m scripts.load_cook_along

clean:
	@echo "make clean: not yet implemented" && exit 1

# §7.5 — eligible-province counts at every threshold 5-30, per register, from
# v_recipes_clean. Writes data/processed/eligibility_sweep.csv. The only analysis step
# built so far; the rest of `analyze` does not exist yet.
analyze:
	uv run python -m scripts.eligibility_sweep

vision:
	@echo "make vision: not yet implemented" && exit 1

# Rule 5 — every figure is regenerated from the database, never hand-edited. Figures not
# listed here do not exist yet; a figure that stops regenerating is a broken build, not a
# stale file to be patched.
figures:
	uv run python -m scripts.make_figure2
	uv run python -m scripts.make_figure4
	uv run python -m scripts.make_fidelity_matrix

api:
	uv run uvicorn src.api.main:app --reload --port 8000

web:
	@echo "make web: not yet implemented" && exit 1

export:
	@echo "make export: not yet implemented" && exit 1

# Read-only snapshot of where the project stands. Never writes to the database.
status:
	uv run python -m scripts.status

# The same snapshot, aggregate counts only (HD-28), written to
# data/coverage/status_YYYY-MM-DD.md for committing, so progress shows in git history.
status-snapshot:
	uv run python -m scripts.status --snapshot

test:
	uv run pytest
	uv run ruff check .
	uv run mypy

all: clean analyze figures

# Fresh-clone reproducibility check (CLAUDE.md §2.2): applies every migration to an
# empty database and runs the full test suite against it. Runs on a THROWAWAY stack
# (project flavormap_verify, port $${VERIFY_PORT:-5439}) via scripts/verify.sh, and never
# touches the live database. It used to be `db-reset test`, which deleted the live volume.
verify:
	./scripts/verify.sh
