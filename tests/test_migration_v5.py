"""v5 migration: old standard alarms get a shortlink."""

from __future__ import annotations

import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from unzzz.db import Store


class MigrationV5Tests(unittest.TestCase):
    def test_standard_alarm_gets_fallback_slug(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="unzzz-migrate-"))
        db = tmp / "db.sqlite3"
        store = Store(db)
        alarm = store.create_alarm({
            "label": "Old standard",
            "time": "07:30",
            "days_mask": 31,
            "once_date": None,
            "enabled": 1,
            "mode": "standard",
            "difficulty": "normal",
            "snooze_minutes": 9,
            "max_snoozes": 2,
            "max_ring_minutes": 15,
            "next_fire": time.time() + 3600,
            "participants": [],
            "completion_mode": "all",
            "target_count": 1,
            "challenge_count": 1,
            "question_source": "auto",
            "challenge_type": "math",
            "music_id": None,
            "calendar_id": None,
            "slug": "old-standard",
        })
        with store.conn:
            store.conn.execute("UPDATE alarms SET slug=NULL WHERE id=?", (alarm["id"],))
            store.conn.execute("PRAGMA user_version=4")
        store.close()

        conn = sqlite3.connect(db)
        conn.execute("ALTER TABLE alarms DROP COLUMN link_expires_at")
        conn.execute("DROP TABLE IF EXISTS retired_links")
        conn.commit()
        conn.close()

        store = Store(db)
        try:
            self.assertEqual(
                store.conn.execute("PRAGMA user_version").fetchone()[0], 6
            )
            row = store.get_alarm(alarm["id"])
            self.assertEqual(row["slug"], "alarm-1")
            self.assertIsNone(row["link_expires_at"])
        finally:
            store.close()
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
