"""Backup ZIP creation, validation and staged restore."""

from __future__ import annotations

import io
import shutil
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

from unzzz.backup import (
    BackupError,
    apply_pending_restore,
    create_backup,
    stage_restore,
)
from unzzz.db import Store


class BackupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="unzzz-backup-"))
        self.data = self.tmp / "data"
        self.data.mkdir()
        self.store = Store(self.data / "unzzz.sqlite3")
        self.store.add_user("Ada")
        self.store.create_alarm({
            "label": "Backup alarm", "time": "07:30", "days_mask": 31,
            "once_date": None, "enabled": 1, "mode": "standard",
            "difficulty": "normal", "snooze_minutes": 9, "max_snoozes": 2,
            "max_ring_minutes": 15, "next_fire": time.time() + 3600,
            "participants": [], "completion_mode": "all", "target_count": 1,
            "challenge_count": 1, "challenge_plan": None,
            "challenge_order": "fixed", "challenge_random_min": 1,
            "challenge_random_max": 1, "finish_beep": 0, "muted": 0,
            "question_source": "auto", "challenge_type": "math",
            "music_id": None, "calendar_id": None, "slug": "backup-alarm",
        })
        (self.data / "music").mkdir()
        (self.data / "music" / "song.mp3").write_bytes(b"music-bytes")

    def tearDown(self) -> None:
        self.store.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_backup_contains_db_music_and_manifest(self) -> None:
        payload = create_backup(self.store, self.data / "music", "test")
        with zipfile.ZipFile(io.BytesIO(payload)) as zf:
            names = set(zf.namelist())
        self.assertIn("unzzz.sqlite3", names)
        self.assertIn("music/song.mp3", names)
        self.assertIn("manifest.json", names)

    def test_stage_and_apply_restore(self) -> None:
        payload = create_backup(self.store, self.data / "music", "test")
        archive = self.data / "restore.zip"
        archive.write_bytes(payload)
        result = stage_restore(self.data, archive)
        self.assertGreaterEqual(result["music_files"], 1)
        self.store.close()
        self.assertTrue(apply_pending_restore(self.data))
        restored = Store(self.data / "unzzz.sqlite3")
        try:
            self.assertEqual(restored.get_alarm_by_slug("backup-alarm")["label"], "Backup alarm")
        finally:
            restored.close()
        self.assertTrue((self.data / "music" / "song.mp3").is_file())

    def test_restore_rejects_non_zip(self) -> None:
        archive = self.data / "bad.zip"
        archive.write_bytes(b"not a zip")
        with self.assertRaises(BackupError):
            stage_restore(self.data, archive)
