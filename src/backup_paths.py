"""Which backup destinations count as off-laptop (HD-31, amended 2026-09-29).

``scripts/backup.sh`` refuses a destination on the same disk as the repo, because a
backup on the laptop it protects is not a backup. A cloud-sync folder is the exception:
it sits on this disk, but its contents are uploaded off the laptop. Only locations macOS
itself uses for sync are recognised:

- **iCloud Drive**: ``~/Library/Mobile Documents/com~apple~CloudDocs`` and below.
- **File Provider sync** (current Google Drive, OneDrive, Dropbox):
  ``~/Library/CloudStorage/<provider>/`` and below. ``CloudStorage`` itself is not synced,
  so the destination must be inside a provider folder.

Everything else on this disk stays refused, including a legacy ``~/Dropbox`` folder,
which can't be told apart from an ordinary folder by its path. Paths are resolved first,
so a symlink cannot make a local folder look like a synced one.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ICLOUD = Path("Library") / "Mobile Documents" / "com~apple~CloudDocs"
CLOUD_STORAGE = Path("Library") / "CloudStorage"


def cloud_sync_kind(destination: str | Path, home: str | Path) -> str | None:
    """"iCloud Drive" or the provider folder's name when `destination` is inside a
    recognised sync location, else None."""
    dest = Path(os.path.realpath(destination))
    home_real = Path(os.path.realpath(home))
    icloud = home_real / ICLOUD
    if dest == icloud or icloud in dest.parents:
        return "iCloud Drive"
    storage = home_real / CLOUD_STORAGE
    if storage in dest.parents:
        return dest.relative_to(storage).parts[0]
    return None


if __name__ == "__main__":
    # Used by scripts/backup.sh: prints the sync kind, or nothing.
    print(cloud_sync_kind(sys.argv[1], sys.argv[2]) or "")
