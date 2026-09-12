.PHONY: setup db-up db-down db-reset db-dump scrape scrape-dcp scrape-kapook ingest ingest-gdcatalog ingest-local-dish ingest-food67 clean analyze vision figures api web export test all verify

setup: db-up
	uv sync
	uv run playwright install
	uv run python -m scripts.migrate

db-up:
	docker compose up -d --wait

db-down:
	docker compose down

# Destroys the named volume. Only for verifying that migrations apply from empty.
db-reset:
	docker compose down -v
	docker compose up -d --wait
	uv run python -m scripts.migrate

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

# Not fetched and not part of `ingest` — culture.gdcatalog.go.th is consulted by hand
# only (ETHICS.md), and this loader needs a manually-downloaded CSV in place plus a
# completed source audit before it can run at all (docs/decisions.md, 2026-09-12).
# Kept as its own target so it does not break `make ingest` for a clone that has
# neither yet.
ingest-gdcatalog:
	uv run python -m scripts.parse_gdcatalog

# Same shape as ingest-gdcatalog and the same reason it is not part of `ingest`: a
# manually-downloaded CSV (data/raw/gdcatalog/อาหารพื้นถิ่น.csv) and a completed source
# audit are both preconditions this target does not itself satisfy.
ingest-local-dish:
	uv run python -m scripts.parse_local_dish_inventory

# Same two unmet preconditions as the other gdcatalog targets (the CSV, and a sources
# seed row), plus its own: provenance is undocumented and unverified against source
# (docs/decisions.md, Task 0). `--report` works without either precondition —
# uv run python -m scripts.parse_food67 --report
ingest-food67:
	uv run python -m scripts.parse_food67

clean:
	@echo "make clean: not yet implemented" && exit 1

analyze:
	@echo "make analyze: not yet implemented" && exit 1

vision:
	@echo "make vision: not yet implemented" && exit 1

# Rule 5 — every figure is regenerated from the database, never hand-edited. Figures not
# listed here do not exist yet; a figure that stops regenerating is a broken build, not a
# stale file to be patched.
figures:
	uv run python -m scripts.make_figure2
	uv run python -m scripts.make_figure4

api:
	uv run uvicorn src.api.main:app --reload --port 8000

web:
	@echo "make web: not yet implemented" && exit 1

export:
	@echo "make export: not yet implemented" && exit 1

test:
	uv run pytest
	uv run ruff check .
	uv run mypy

all: clean analyze figures

# Fresh-clone reproducibility check (CLAUDE.md §2.2, and db-reset's own comment: "only
# for verifying that migrations apply from empty"). Destroys the local database volume,
# rebuilds it from nothing, re-applies every migration in order, and runs the full test
# suite against the result. A green `verify` is the claim "a stranger who clones this
# repo today and runs `make setup && make verify` gets a working, tested schema" —
# checked here rather than assumed from the last time it happened to work.
verify: db-reset test
