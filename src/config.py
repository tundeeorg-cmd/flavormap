"""Project-wide constants, paths, and environment-backed settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent

# §1.6 — every stochastic operation takes this seed, defined once.
RANDOM_SEED = 42

# Pinned explicitly; bump deliberately, never silently.
ANTHROPIC_MODEL = "claude-sonnet-5"

# §7.4 — the degradation rule's threshold for province-level analysis eligibility.
PROVINCE_MIN_N = 20

DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
# data/reference holds curated inputs (provinces.csv). Distinct from
# RAW_DIR / "reference", which caches downloaded source data such as the GADM
# boundaries — different provenance, different retention, do not merge them.
REFERENCE_DIR = DATA_DIR / "reference"
EXPORTS_DIR = DATA_DIR / "exports"

FIGURES_DIR = REPO_ROOT / "figures"
FIGURES_FINAL_DIR = FIGURES_DIR / "final"

DOCS_DIR = REPO_ROOT / "docs"

MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    anthropic_api_key: str
    scraper_contact_email: str


@lru_cache
def get_settings() -> Settings:
    """Load settings from .env / the environment. Lazy, so importing this module never
    requires a configured environment (see tests/test_smoke.py)."""
    return Settings()  # type: ignore[call-arg]  # fields are populated from the environment
