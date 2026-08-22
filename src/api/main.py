"""FastAPI entrypoint.

A scaffold. It serves health and status only — deliberately no recipe, ingredient or
province-detail endpoints yet, for two reasons.

**HD-3 is open.** The DCP corpus was fetched under option C — reference layer only,
excluded from any public release, pending a reply to the permission request in
``docs/dcp_permission_request.md``. An endpoint returning DCP-derived rows would resolve
that gate by accident, in the direction of "we published it anyway". Endpoints that serve
corpus content wait for a written answer.

**There is no database to reach.** Bible §11 puts Postgres in local Docker on purpose,
because hosted free tiers pause during the deliberate quiet periods in the schedule. A
deployed instance has no route to it. Rather than fail, ``/status`` reports plainly that
no database is configured — an honest empty state is more useful than a 500.

Nothing here imports the pipeline. ``src.config``, psycopg, torch and geopandas are all
absent at module scope: importing settings would require env vars the deployment does not
have, and the heavy scientific stack would blow the function size limit.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI

app = FastAPI(
    title="FlavorMap API",
    version="0.1.0",
    description="Computational geography of Thai cuisine. Scaffold — see docstring.",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness. Must not touch the database, or a cold start fails the health check."""
    return {"status": "ok", "service": "flavormap-api"}


def _database_url() -> str | None:
    """Read the connection string without importing src.config.

    src.config.Settings requires ANTHROPIC_API_KEY and SCRAPER_CONTACT_EMAIL as well,
    which a deployment has no reason to hold. Reading the one variable directly keeps
    this module importable in an environment configured for nothing else.
    """
    return os.environ.get("DATABASE_URL") or None


@app.get("/status")
def status() -> dict[str, Any]:
    """What this instance can actually see.

    `database: "not configured"` is the expected state for a deployed instance, not an
    error: the database is local by design (Bible §11).
    """
    url = _database_url()
    if not url:
        return {
            "database": "not configured",
            "detail": (
                "FlavorMap's database is local PostgreSQL + PostGIS by design "
                "(Bible §11). A deployed instance has no route to it."
            ),
            "endpoints": ["/health", "/status"],
        }

    try:
        import psycopg  # imported lazily: absent from the deployment's dependencies
    except ImportError:
        return {"database": "driver unavailable", "endpoints": ["/health", "/status"]}

    try:
        with psycopg.connect(url, connect_timeout=5) as conn:
            provinces = conn.execute("SELECT count(*) FROM provinces").fetchone()
            recipes = conn.execute("SELECT count(*) FROM recipes").fetchone()
    except Exception as exc:  # noqa: BLE001 - report the failure, do not crash the app
        return {"database": "unreachable", "error": type(exc).__name__}

    # Counts only. No corpus content is served while HD-3 is open.
    return {
        "database": "connected",
        "provinces": provinces[0] if provinces else 0,
        "recipes": recipes[0] if recipes else 0,
        "note": "counts only — corpus content is not served while HD-3 is open",
    }
