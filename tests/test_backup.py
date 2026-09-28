"""scripts/backup.sh (HD-31): an encrypted backup that verifies itself, refuses the
laptop's own disk, and leaves no plaintext behind.

Runs the real script with its two test-only hooks: a throwaway GNUPGHOME with a dummy
passphrase (never the researcher's keyring or passphrase), and permission to use a
same-disk destination, since a test cannot plug in an external drive. The same-disk
refusal itself is tested with the hook off.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import os
import subprocess
import tarfile
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from src.config import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "backup.sh"
PASSPHRASE = "test-only-passphrase-not-real"


@pytest.fixture
def gpg_env(tmp_path: Path) -> Iterator[dict[str, str]]:
    home = Path(tempfile.mkdtemp(prefix="fmgpg"))  # short path: gpg-agent socket limit
    home.chmod(0o700)
    passfile = tmp_path / "pass"
    passfile.write_text(PASSPHRASE)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    env = {
        **os.environ,
        "GNUPGHOME": str(home),
        "TMPDIR": str(scratch),
        "FLAVORMAP_BACKUP_TEST_PASSPHRASE_FILE": str(passfile),
    }
    yield env
    subprocess.run(["gpgconf", "--kill", "gpg-agent"], env=env, check=False)
    subprocess.run(["rm", "-rf", str(home)], check=False)


def _run(dest: object, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), str(dest)], cwd=REPO_ROOT, env=env,
        capture_output=True, text=True, timeout=180, check=False,
    )


def _decrypt(path: Path, env: dict[str, str], passphrase: str = PASSPHRASE) -> bytes:
    result = subprocess.run(
        ["gpg", "--quiet", "--batch", "--pinentry-mode", "loopback",
         "--passphrase", passphrase, "--decrypt", str(path)],
        env=env, capture_output=True, check=False,
    )
    if result.returncode != 0:
        raise ValueError("decryption failed")
    return result.stdout


def test_a_backup_is_encrypted_complete_and_verified(
    tmp_path: Path, gpg_env: dict[str, str]
) -> None:
    dest = tmp_path / "drive"
    dest.mkdir()
    result = _run(dest, {**gpg_env, "FLAVORMAP_BACKUP_TEST_ALLOW_SAME_DISK": "1"})
    assert result.returncode == 0, result.stderr
    assert "Verified: decrypts and matches" in result.stdout
    [backup] = list(dest.glob("flavormap_backup_*.tar.gz.gpg"))

    # Ciphertext: not gzip, and no readable SQL or Thai text.
    raw = backup.read_bytes()
    assert raw[:2] != b"\x1f\x8b"
    assert b"CREATE TABLE" not in raw and "หอมแดง".encode() not in raw

    # Decrypted: every interview file and the newest dump, byte for byte, plus a manifest
    # whose checksums hold.
    with tarfile.open(fileobj=io.BytesIO(_decrypt(backup, gpg_env)), mode="r:gz") as tar:
        members = {m.name: tar.extractfile(m).read()  # type: ignore[union-attr]
                   for m in tar.getmembers() if m.isfile()}
    newest_dump = max((REPO_ROOT / "data" / "exports").glob("flavormap_*.sql.gz"),
                      key=lambda p: p.stat().st_mtime)
    assert members[f"flavormap_backup/exports/{newest_dump.name}"] == newest_dump.read_bytes()
    for f in (REPO_ROOT / "data" / "interviews").glob("*.toml"):
        assert members[f"flavormap_backup/interviews/{f.name}"] == f.read_bytes()
    manifest = members["flavormap_backup/MANIFEST"].decode()
    for line in manifest.splitlines():
        if line.startswith("#"):
            continue
        digest, path = line.split("  ", 1)
        assert hashlib.sha256(members[f"flavormap_backup/{path}"]).hexdigest() == digest
    assert gzip.decompress(members[f"flavormap_backup/exports/{newest_dump.name}"])[:5]


def test_the_wrong_passphrase_cannot_open_it(tmp_path: Path, gpg_env: dict[str, str]) -> None:
    dest = tmp_path / "drive"
    dest.mkdir()
    assert _run(dest, {**gpg_env, "FLAVORMAP_BACKUP_TEST_ALLOW_SAME_DISK": "1"}).returncode == 0
    [backup] = list(dest.glob("*.gpg"))
    subprocess.run(["gpgconf", "--kill", "gpg-agent"], env=gpg_env, check=False)  # no cache
    with pytest.raises(ValueError):
        _decrypt(backup, gpg_env, passphrase="wrong")


def test_no_plaintext_is_left_behind(tmp_path: Path, gpg_env: dict[str, str]) -> None:
    dest = tmp_path / "drive"
    dest.mkdir()
    assert _run(dest, {**gpg_env, "FLAVORMAP_BACKUP_TEST_ALLOW_SAME_DISK": "1"}).returncode == 0
    # The staging and check directories are gone. uv's own lock files may remain in
    # TMPDIR; they hold no backup content.
    left = [p for p in Path(gpg_env["TMPDIR"]).rglob("*") if not p.name.startswith("uv-")]
    assert left == []
    assert [p.suffix for p in dest.iterdir()] == [".gpg"]


def test_the_laptops_own_disk_is_refused(tmp_path: Path, gpg_env: dict[str, str]) -> None:
    dest = tmp_path / "same_disk"
    dest.mkdir()
    result = _run(dest, gpg_env)  # no same-disk hook
    assert result.returncode != 0
    assert "same disk as this repo and is not a recognised" in result.stderr
    assert list(dest.iterdir()) == []


def test_a_cloud_sync_folder_is_accepted_without_the_same_disk_hook(
    tmp_path: Path, gpg_env: dict[str, str]
) -> None:
    """HD-31 as amended: a folder inside ~/Library/CloudStorage/<provider>/ counts as
    off-laptop even though it sits on this disk. HOME is a fake home; uv keeps its real
    cache so nothing is reinstalled."""
    fake_home = tmp_path / "home"
    synced = fake_home / "Library" / "CloudStorage" / "GoogleDrive-test" / "My Drive"
    synced.mkdir(parents=True)
    uv_cache = subprocess.run(["uv", "cache", "dir"], capture_output=True, text=True,
                              check=True).stdout.strip()
    result = _run(synced, {**gpg_env, "HOME": str(fake_home), "UV_CACHE_DIR": uv_cache})
    assert result.returncode == 0, result.stderr
    assert "GoogleDrive-test folder" in result.stdout
    assert "Check the sync status before relying on it" in result.stdout
    assert len(list(synced.glob("*.gpg"))) == 1


@pytest.mark.parametrize("dest", ["", "/nonexistent/drive"])
def test_a_missing_destination_is_an_error(dest: str, gpg_env: dict[str, str]) -> None:
    result = _run(dest, gpg_env)
    assert result.returncode != 0
    assert "Usage" in result.stderr or "not a writable directory" in result.stderr
