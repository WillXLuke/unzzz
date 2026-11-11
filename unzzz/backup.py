"""Portable ZIP backup and staged restore for unzzz data."""

from __future__ import annotations

import io
import json
import os
import shutil
import sqlite3
import time
import zipfile
from pathlib import Path

BACKUP_DB = "unzzz.sqlite3"
MANIFEST = "manifest.json"
PENDING = "restore-pending"
MAX_RESTORE_BYTES = 200 * 1024 * 1024


class BackupError(ValueError):
    pass


def create_backup(store, music_dir: Path, version: str) -> bytes:
    """Return a ZIP containing the database, music and manifest."""
    music_dir = Path(music_dir)
    tmp_db = music_dir.parent / f".backup-{os.getpid()}-{int(time.time())}.sqlite3"
    try:
        target = sqlite3.connect(str(tmp_db))
        try:
            store.conn.backup(target)
        finally:
            target.close()
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(tmp_db, BACKUP_DB)
            if music_dir.is_dir():
                for path in sorted(music_dir.iterdir()):
                    if path.is_file():
                        zf.write(path, f"music/{path.name}")
            zf.writestr(
                MANIFEST,
                json.dumps(
                    {
                        "format": 1,
                        "version": version,
                        "created_at": time.time(),
                    },
                    indent=2,
                ),
            )
        return buffer.getvalue()
    finally:
        tmp_db.unlink(missing_ok=True)


def _safe_zip_names(zf: zipfile.ZipFile) -> list[str]:
    names = zf.namelist()
    total = 0
    for name in names:
        clean = Path(name)
        if clean.is_absolute() or ".." in clean.parts:
            raise BackupError("Backup contains an unsafe path")
        if name not in (BACKUP_DB, MANIFEST) and not name.startswith("music/"):
            raise BackupError(f"Unexpected backup entry: {name}")
        try:
            total += zf.getinfo(name).file_size
        except KeyError:
            continue
    if total > MAX_RESTORE_BYTES:
        raise BackupError("Backup is too large")
    if BACKUP_DB not in names:
        raise BackupError("Backup does not contain unzzz.sqlite3")
    return names


def _validate_db(path: Path) -> None:
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            check = conn.execute("PRAGMA integrity_check").fetchone()
            if not check or check[0] != "ok":
                raise BackupError("Backup database failed integrity check")
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            required = {"alarms", "events", "challenges", "questions", "settings"}
            if not required.issubset(tables):
                raise BackupError("Backup database is missing required tables")
        finally:
            conn.close()
    except sqlite3.Error as exc:
        raise BackupError(f"Invalid backup database: {exc}") from exc


def stage_restore(data_dir: Path, upload: Path) -> dict:
    """Validate a backup ZIP and stage it for the next service start."""
    data_dir = Path(data_dir)
    pending = data_dir / PENDING
    temp = data_dir / f".restore-{os.getpid()}-{int(time.time())}"
    shutil.rmtree(temp, ignore_errors=True)
    temp.mkdir(parents=True)
    try:
        try:
            with zipfile.ZipFile(upload) as zf:
                names = _safe_zip_names(zf)
                for name in names:
                    if name == MANIFEST or name.endswith("/"):
                        continue
                    destination = temp / (
                        BACKUP_DB if name == BACKUP_DB else Path("music") / Path(name).name
                    )
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(name) as src, destination.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
        except zipfile.BadZipFile as exc:
            raise BackupError("Not a valid ZIP backup") from exc
        db_path = temp / BACKUP_DB
        _validate_db(db_path)
        (temp / "music").mkdir(parents=True, exist_ok=True)
        shutil.rmtree(pending, ignore_errors=True)
        temp.rename(pending)
        return {
            "music_files": len(list((pending / "music").iterdir())),
            "staged": str(pending),
        }
    except Exception:
        shutil.rmtree(temp, ignore_errors=True)
        raise


def apply_pending_restore(data_dir: Path) -> bool:
    """Apply a staged restore before the store is opened."""
    data_dir = Path(data_dir)
    pending = data_dir / PENDING
    pending_db = pending / BACKUP_DB
    if not pending_db.is_file():
        return False
    db_path = data_dir / BACKUP_DB
    if db_path.exists():
        backup_name = f"unzzz-before-restore-{int(time.time())}.sqlite3"
        shutil.copy2(db_path, data_dir / backup_name)
    for suffix in ("-wal", "-shm"):
        try:
            (data_dir / f"{BACKUP_DB}{suffix}").unlink(missing_ok=True)
        except OSError:
            pass
    shutil.copy2(pending_db, db_path)
    pending_music = pending / "music"
    music_dir = data_dir / "music"
    if pending_music.is_dir():
        old_music = data_dir / f"music-before-restore-{int(time.time())}"
        if music_dir.exists():
            try:
                music_dir.rename(old_music)
            except OSError:
                shutil.rmtree(music_dir, ignore_errors=True)
        shutil.copytree(pending_music, music_dir)
    shutil.rmtree(pending, ignore_errors=True)
    return True
