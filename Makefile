.PHONY: setup db-up db-down db-reset db-dump scrape ingest clean analyze vision figures api web export test all verify

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

scrape:
	@echo "make scrape: not yet implemented" && exit 1

ingest:
	@echo "make ingest: not yet implemented" && exit 1

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

verify:
	@echo "make verify: not yet implemented" && exit 1
