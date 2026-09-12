.PHONY: setup db-up db-down db-reset db-dump scrape scrape-dcp scrape-kapook ingest clean analyze vision figures api web export test all verify

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

# Fetch, then parse-and-load. `ingest` depends on `scrape` so `make ingest` alone takes
# a fresh clone all the way to a loaded `recipes` table; `make scrape` (or a single
# `scrape-*` target) on its own still works for re-fetching without touching the
# database.
#
# dcp_food only for now. kapook_cooking has no parse-and-load step: mapping a kapook
# *page* to `recipes` *rows* is an open call src/ingest/kapook_page.py's own docstring
# declines to make ("an analytical choice about the unit of observation ... left to the
# caller") — some pages hold one dish, one holds 46 (a listicle), others split one dish
# across two ingredient sections (batter, dipping sauce), and nothing in the markup
# tells those two shapes apart. scripts/parse_kapook.py is not written until that call is
# made; see docs/decisions.md.
ingest: scrape
	uv run python -m scripts.parse_dcp

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
