.PHONY: setup db-up db-down db-reset scrape ingest clean analyze vision figures api web export test all verify

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

figures:
	@echo "make figures: not yet implemented" && exit 1

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
