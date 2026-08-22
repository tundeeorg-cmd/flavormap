"""The API entrypoint must import and serve in an environment configured for nothing.

That is the deployment's actual condition: no DATABASE_URL, no ANTHROPIC_API_KEY, no
SCRAPER_CONTACT_EMAIL. `src.config.Settings` requires all three, so importing it at
module scope would make the app un-importable on Vercel — which is the failure this
scaffold exists to prevent.
"""

from __future__ import annotations

import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_health_needs_no_configuration() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_status_reports_absent_database_rather_than_failing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    body = client.get("/status").json()
    assert body["database"] == "not configured"


def test_status_degrades_on_an_unreachable_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@127.0.0.1:9/x")
    body = client.get("/status").json()
    assert body["database"] == "unreachable"


def test_no_endpoint_serves_corpus_content_while_hd3_is_open() -> None:
    """HD-3 is unresolved, so nothing DCP-derived may be exposed. Counts only."""
    paths = set(client.get("/openapi.json").json()["paths"])
    assert paths == {"/health", "/status"}


def test_module_imports_with_no_environment_at_all() -> None:
    """The real regression guard: a clean interpreter with an empty environment.

    monkeypatch cannot catch an import-time settings read, because this module is
    already imported by the time a test runs.
    """
    result = subprocess.run(
        [sys.executable, "-c", "import src.api.main; print(src.api.main.app.title)"],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": "."},
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "FlavorMap API" in result.stdout


def test_heavy_dependencies_are_not_imported() -> None:
    """torch and geopandas would blow the 250 MB function limit if pulled in."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, src.api.main; "
            "print([m for m in ('torch','geopandas','psycopg','pandas') if m in sys.modules])",
        ],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": "."},
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[]"
