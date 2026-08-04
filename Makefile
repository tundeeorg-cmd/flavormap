.PHONY: setup scrape clean analyze figures map export test all

setup:
	uv sync
	uv run playwright install
	uv run python -m scripts.migrate

scrape:
	@echo "make scrape: not yet implemented" && exit 1

clean:
	@echo "make clean: not yet implemented" && exit 1

analyze:
	@echo "make analyze: not yet implemented" && exit 1

figures:
	@echo "make figures: not yet implemented" && exit 1

map:
	@echo "make map: not yet implemented" && exit 1

export:
	@echo "make export: not yet implemented" && exit 1

test:
	uv run pytest
	uv run ruff check .
	uv run mypy

all: clean analyze figures
