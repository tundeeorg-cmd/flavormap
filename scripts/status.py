"""Print a read-only snapshot of where the project stands, or write it for git.

    uv run python -m scripts.status              # print to the terminal (make status)
    uv run python -m scripts.status --snapshot   # write data/coverage/status_YYYY-MM-DD.md
                                                 # (make status-snapshot)

The terminal form names the provinces with no recipes in each register. The snapshot is
committed to a public repository, so it carries aggregate counts only and omits those
name lists, which are DCP-derived coverage (HD-3, HD-28). See ``src/status.py``.
"""

from __future__ import annotations

import argparse

from src.config import DATA_DIR
from src.status import collect, render

SNAPSHOT_DIR = DATA_DIR / "coverage"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snapshot", action="store_true",
                    help="write the public (aggregate-only) form to data/coverage/")
    args = ap.parse_args()

    status = collect()
    if not args.snapshot:
        print(render(status))
        return 0

    out = SNAPSHOT_DIR / f"status_{status.today.isoformat()}.md"
    body = render(status, public=True)
    out.write_text(
        f"# FlavorMap status — {status.today.isoformat()}\n\n"
        "Written by `make status-snapshot`. Aggregate counts only: per-province name "
        "lists are omitted from committed snapshots (HD-28).\n\n"
        f"```\n{body}```\n",
        encoding="utf-8",
    )
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
