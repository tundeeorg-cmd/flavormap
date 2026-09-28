"""src/backup_paths.py: which same-disk destinations count as off-laptop (HD-31,
amended 2026-09-29). Everything runs against a fake home directory."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.backup_paths import CLOUD_STORAGE, ICLOUD, cloud_sync_kind


@pytest.fixture
def home(tmp_path: Path) -> Path:
    (tmp_path / ICLOUD / "FlavorMap").mkdir(parents=True)
    (tmp_path / CLOUD_STORAGE / "GoogleDrive-a@example.com" / "My Drive").mkdir(parents=True)
    (tmp_path / "Desktop").mkdir()
    (tmp_path / "Library" / "CloudStorageX").mkdir(parents=True)
    return tmp_path


@pytest.mark.parametrize(
    ("relative", "expected"),
    [
        (ICLOUD, "iCloud Drive"),
        (ICLOUD / "FlavorMap", "iCloud Drive"),
        (CLOUD_STORAGE / "GoogleDrive-a@example.com" / "My Drive",
         "GoogleDrive-a@example.com"),
        (CLOUD_STORAGE, None),                     # not itself synced
        (Path("Desktop"), None),
        (Path("Library") / "CloudStorageX", None),  # prefix look-alike
        (Path("."), None),
    ],
)
def test_recognised_locations(home: Path, relative: Path, expected: str | None) -> None:
    assert cloud_sync_kind(home / relative, home) == expected


def test_a_symlink_cannot_disguise_a_local_folder(home: Path) -> None:
    # A link inside the synced folder that points back to the local disk is local.
    link = home / ICLOUD / "looks_synced"
    os.symlink(home / "Desktop", link)
    assert cloud_sync_kind(link, home) is None


def test_a_link_into_a_synced_folder_is_that_synced_folder(home: Path) -> None:
    link = home / "Desktop" / "drive"
    os.symlink(home / CLOUD_STORAGE / "GoogleDrive-a@example.com" / "My Drive", link)
    assert cloud_sync_kind(link, home) == "GoogleDrive-a@example.com"
