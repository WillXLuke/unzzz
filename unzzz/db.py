"""SQLite persistence for unzzz.

One connection, one re-entrant lock.  The workload (a handful of alarms and
a few phones polling) is tiny, so serialising database access is both simpler
and safer than a pool -- and easier on a Raspberry Pi's SD card.
"""

from __future__ import annotations

import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    active     INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS music (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    stored_name TEXT NOT NULL UNIQUE,
    mime        TEXT NOT NULL,
    size        INTEGER NOT NULL,
    created_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS calendars (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS calendar_days (
    calendar_id INTEGER NOT NULL REFERENCES calendars(id) ON DELETE CASCADE,
    date        TEXT NOT NULL,              -- YYYY-MM-DD
    kind        TEXT NOT NULL,              -- working | holiday
    note        TEXT,
    PRIMARY KEY (calendar_id, date)
);

CREATE TABLE IF NOT EXISTS alarms (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    label            TEXT NOT NULL,
    time             TEXT NOT NULL,              -- HH:MM (local wall clock)
    days_mask        INTEGER NOT NULL DEFAULT 0, -- bit 0 = Monday ... bit 6 = Sunday
    once_date        TEXT,                       -- YYYY-MM-DD, used when days_mask = 0
    enabled          INTEGER NOT NULL DEFAULT 1,
    mode             TEXT NOT NULL DEFAULT 'standard',
    difficulty       TEXT NOT NULL DEFAULT 'normal',
    snooze_minutes   INTEGER NOT NULL DEFAULT 9,
    max_snoozes      INTEGER NOT NULL DEFAULT 2,
    max_ring_minutes INTEGER NOT NULL DEFAULT 15,
    next_fire        REAL,                       -- epoch seconds, UTC
    last_fired_at    REAL,
    created_at       REAL NOT NULL,
    slug             TEXT,                       -- public challenge link
    completion_mode  TEXT NOT NULL DEFAULT 'all', -- all | count
    target_count     INTEGER NOT NULL DEFAULT 1,
    challenge_count  INTEGER NOT NULL DEFAULT 1, -- questions per participant
    link_expires_at  REAL,                      -- public shortlink expiry
    question_source  TEXT NOT NULL DEFAULT 'auto', -- legacy; see challenge_type
    challenge_type   TEXT NOT NULL DEFAULT 'math', -- math|text|choice|color|pattern
    skip_next        INTEGER NOT NULL DEFAULT 0,
    music_id         INTEGER REFERENCES music(id) ON DELETE SET NULL,
    calendar_id      INTEGER REFERENCES calendars(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_alarms_fire ON alarms(enabled, next_fire);

CREATE TABLE IF NOT EXISTS alarm_users (
    alarm_id INTEGER NOT NULL REFERENCES alarms(id) ON DELETE CASCADE,
    user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (alarm_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_alarm_users_alarm ON alarm_users(alarm_id);

CREATE TABLE IF NOT EXISTS events (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    alarm_id         INTEGER REFERENCES alarms(id) ON DELETE SET NULL,
    alarm_label      TEXT NOT NULL,
    mode             TEXT NOT NULL,
    difficulty       TEXT NOT NULL DEFAULT 'normal',
    state            TEXT NOT NULL,              -- ringing|snoozed|completed|stopped|expired|interrupted|missed
    fired_at         REAL NOT NULL,
    ends_at          REAL,
    stopped_at       REAL,
    stop_reason      TEXT,
    snooze_until     REAL,
    snooze_count     INTEGER NOT NULL DEFAULT 0,
    max_snoozes      INTEGER NOT NULL DEFAULT 2,
    snooze_minutes   INTEGER NOT NULL DEFAULT 9,
    max_ring_minutes INTEGER NOT NULL DEFAULT 15,
    manual           INTEGER NOT NULL DEFAULT 0,
    completion_mode  TEXT NOT NULL DEFAULT 'all',
    target_count     INTEGER NOT NULL DEFAULT 1,
    challenge_count  INTEGER NOT NULL DEFAULT 1,
    question_source  TEXT NOT NULL DEFAULT 'auto', -- legacy
    challenge_type   TEXT NOT NULL DEFAULT 'math',
    shared_questions TEXT, -- JSON snapshot for random-choice sessions
    music_id         INTEGER REFERENCES music(id) ON DELETE SET NULL,
    music_name       TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_state ON events(state, fired_at);

CREATE TABLE IF NOT EXISTS challenges (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id    INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    user_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    user_name   TEXT NOT NULL,
    token       TEXT NOT NULL UNIQUE,
    question    TEXT,
    answer      TEXT,
    answer_type TEXT NOT NULL DEFAULT 'number',  -- number | text | choice | color | pattern
    challenge_type TEXT NOT NULL DEFAULT 'math',
    payload     TEXT,                            -- type-specific JSON
    question_id INTEGER,
    attempts    INTEGER NOT NULL DEFAULT 0,
    solved      INTEGER NOT NULL DEFAULT 0,
    answered_at REAL,
    created_at  REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_challenges_event ON challenges(event_id);

CREATE TABLE IF NOT EXISTS retired_links (
    slug       TEXT PRIMARY KEY,
    label      TEXT NOT NULL,
    expires_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS questions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    question   TEXT NOT NULL,
    answer     TEXT NOT NULL,
    kind       TEXT NOT NULL DEFAULT 'text',      -- text | choice
    options    TEXT,                              -- JSON array for choice
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    user_agent TEXT
);
"""


class Store:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(
            str(self.path), check_same_thread=False, timeout=15.0
        )
        self.conn.row_factory = sqlite3.Row
        with self.lock:
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")
            self.conn.execute("PRAGMA foreign_keys=ON")
            self.conn.execute("PRAGMA busy_timeout=15000")
            self.conn.executescript(SCHEMA)
            self.conn.commit()
            self._migrate()

    def _migrate(self) -> None:
        """Upgrade a v1 database in place (idempotent)."""
        version = int(
            self.conn.execute("PRAGMA user_version").fetchone()[0] or 0
        )
        alarm_cols = {
            r[1] for r in self.conn.execute("PRAGMA table_info(alarms)").fetchall()
        }
        additions = [
            ("slug", "TEXT"),
            ("completion_mode", "TEXT NOT NULL DEFAULT 'all'"),
            ("target_count", "INTEGER NOT NULL DEFAULT 1"),
            ("question_source", "TEXT NOT NULL DEFAULT 'auto'"),
            ("challenge_type", "TEXT NOT NULL DEFAULT 'math'"),
            ("challenge_count", "INTEGER NOT NULL DEFAULT 1"),
            ("link_expires_at", "REAL"),
            ("skip_next", "INTEGER NOT NULL DEFAULT 0"),
            ("music_id", "INTEGER"),
            ("calendar_id", "INTEGER"),
        ]
        for name, ddl in additions:
            if name not in alarm_cols:
                self.conn.execute(f"ALTER TABLE alarms ADD COLUMN {name} {ddl}")

        event_cols = {
            r[1] for r in self.conn.execute("PRAGMA table_info(events)").fetchall()
        }
        for name, ddl in [
            ("completion_mode", "TEXT NOT NULL DEFAULT 'all'"),
            ("target_count", "INTEGER NOT NULL DEFAULT 1"),
            ("question_source", "TEXT NOT NULL DEFAULT 'auto'"),
            ("challenge_type", "TEXT NOT NULL DEFAULT 'math'"),
            ("challenge_count", "INTEGER NOT NULL DEFAULT 1"),
            ("shared_questions", "TEXT"),
            ("music_id", "INTEGER"),
            ("music_name", "TEXT"),
        ]:
            if name not in event_cols:
                self.conn.execute(f"ALTER TABLE events ADD COLUMN {name} {ddl}")

        challenge_cols = {
            r[1] for r in self.conn.execute("PRAGMA table_info(challenges)").fetchall()
        }
        for name, ddl in [
            ("answer_type", "TEXT NOT NULL DEFAULT 'number'"),
            ("challenge_type", "TEXT NOT NULL DEFAULT 'math'"),
            ("payload", "TEXT"),
            ("solved", "INTEGER NOT NULL DEFAULT 0"),
            ("question_id", "INTEGER"),
        ]:
            if name not in challenge_cols:
                self.conn.execute(f"ALTER TABLE challenges ADD COLUMN {name} {ddl}")

        question_cols = {
            r[1] for r in self.conn.execute("PRAGMA table_info(questions)").fetchall()
        }
        for name, ddl in [
            ("kind", "TEXT NOT NULL DEFAULT 'text'"),
            ("options", "TEXT"),
        ]:
            if name not in question_cols:
                self.conn.execute(f"ALTER TABLE questions ADD COLUMN {name} {ddl}")

        self.conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_alarms_slug "
            "ON alarms(slug COLLATE NOCASE) WHERE slug IS NOT NULL"
        )

        if version < 2:
            # v1 challenge alarms implicitly used up to six active users.
            # Preserve that behaviour after the upgrade, but make the
            # selection explicit.
            rows = self.conn.execute(
                "SELECT id FROM alarms WHERE mode='challenge' "
                "AND id NOT IN (SELECT alarm_id FROM alarm_users)"
            ).fetchall()
            for (alarm_id,) in rows:
                user_ids = self.conn.execute(
                    "SELECT id FROM users WHERE active=1 ORDER BY id LIMIT 6"
                ).fetchall()
                for (user_id,) in user_ids:
                    self.conn.execute(
                        "INSERT OR IGNORE INTO alarm_users(alarm_id, user_id) "
                        "VALUES(?,?)",
                        (alarm_id, user_id),
                    )

            # Give legacy challenge alarms a usable public shortlink.
            legacy = self.conn.execute(
                "SELECT id FROM alarms WHERE mode='challenge' "
                "AND (slug IS NULL OR slug='')"
            ).fetchall()
            for (alarm_id,) in legacy:
                base = f"alarm{alarm_id}"
                slug = base
                while self.conn.execute(
                    "SELECT 1 FROM alarms WHERE slug = ? COLLATE NOCASE AND id != ?",
                    (slug, alarm_id),
                ).fetchone():
                    slug = f"{base}-{secrets.token_hex(2)}"
                self.conn.execute(
                    "UPDATE alarms SET slug=? WHERE id=?", (slug, alarm_id)
                )

        if version < 3:
            # Map the v2 question_source flag onto the typed-challenge model.
            self.conn.execute(
                "UPDATE alarms SET challenge_type = CASE "
                "WHEN question_source = 'custom' THEN 'text' ELSE 'math' END "
                "WHERE challenge_type IS NULL OR challenge_type = 'math'"
            )
            self.conn.execute(
                "UPDATE events SET challenge_type = CASE "
                "WHEN question_source = 'custom' THEN 'text' ELSE 'math' END "
                "WHERE challenge_type IS NULL OR challenge_type = 'math'"
            )
            self.conn.execute(
                "UPDATE challenges SET challenge_type = CASE "
                "WHEN answer_type = 'text' THEN 'text' ELSE 'math' END "
                "WHERE challenge_type IS NULL OR challenge_type = 'math'"
            )
            self.conn.execute("UPDATE questions SET kind='text' WHERE kind IS NULL")

        if version < 4:
            self.conn.execute("UPDATE alarms SET challenge_count=1 WHERE challenge_count IS NULL")
            self.conn.execute("UPDATE events SET challenge_count=1 WHERE challenge_count IS NULL")
            self.conn.execute(
                "UPDATE challenges SET solved = CASE WHEN answered_at IS NULL THEN 0 ELSE 1 END"
            )

        if version < 5:
            # Standard alarms now also have a shortlink. Give old rows a stable
            # fallback; new rows are generated by the validator.
            rows = self.conn.execute(
                "SELECT id FROM alarms WHERE slug IS NULL"
            ).fetchall()
            for row in rows:
                alarm_id = int(row[0])
                base = f"alarm-{alarm_id}"
                candidate = base
                n = 1
                while self.conn.execute(
                    "SELECT 1 FROM alarms WHERE slug = ? COLLATE NOCASE", (candidate,)
                ).fetchone():
                    n += 1
                    candidate = f"{base}-{n}"
                self.conn.execute(
                    "UPDATE alarms SET slug=? WHERE id=?", (candidate, alarm_id)
                )

        self.conn.execute("PRAGMA user_version=5")
        self.conn.commit()

    def close(self) -> None:
        with self.lock:
            try:
                self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except sqlite3.Error:
                pass
            self.conn.close()

    # ------------------------------------------------------------------ core
    def _all(self, sql: str, params: tuple | list = ()) -> list[dict]:
        with self.lock:
            rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def _one(self, sql: str, params: tuple | list = ()) -> dict | None:
        with self.lock:
            row = self.conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def _exec(self, sql: str, params: tuple | list = ()) -> int:
        with self.lock:
            cur = self.conn.execute(sql, params)
            self.conn.commit()
            return cur.rowcount

    @contextmanager
    def tx(self):
        """Exclusive write transaction.  Never nest calls to this."""
        with self.lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                yield self.conn
            except BaseException:
                self.conn.rollback()
                raise
            else:
                self.conn.commit()

    # -------------------------------------------------------------- settings
    def get_setting(self, key: str, default: str | None = None) -> str | None:
        row = self._one("SELECT value FROM settings WHERE key = ?", (key,))
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self._exec(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    def delete_setting(self, key: str) -> None:
        self._exec("DELETE FROM settings WHERE key = ?", (key,))

    # ----------------------------------------------------------------- users
    def list_users(self, active_only: bool = False) -> list[dict]:
        sql = "SELECT * FROM users"
        if active_only:
            sql += " WHERE active = 1"
        return self._all(sql + " ORDER BY id")

    def get_user(self, user_id: int) -> dict | None:
        return self._one("SELECT * FROM users WHERE id = ?", (user_id,))

    def count_users(self) -> int:
        row = self._one("SELECT COUNT(*) AS n FROM users")
        return int(row["n"]) if row else 0

    def add_user(self, name: str, active: bool = True) -> dict:
        now = time.time()
        with self.tx() as c:
            cur = c.execute(
                "INSERT INTO users(name, active, created_at) VALUES(?,?,?)",
                (name, 1 if active else 0, now),
            )
            user_id = int(cur.lastrowid)
        return self.get_user(user_id)  # type: ignore[return-value]

    def update_user(
        self, user_id: int, name: str | None = None, active: bool | None = None
    ) -> dict | None:
        sets, params = [], []
        if name is not None:
            sets.append("name = ?")
            params.append(name)
        if active is not None:
            sets.append("active = ?")
            params.append(1 if active else 0)
        if sets:
            params.append(user_id)
            self._exec(f"UPDATE users SET {', '.join(sets)} WHERE id = ?", params)
        return self.get_user(user_id)

    def delete_user(self, user_id: int) -> bool:
        return self._exec("DELETE FROM users WHERE id = ?", (user_id,)) > 0

    def user_in_active_event(self, user_id: int) -> dict | None:
        return self._one(
            "SELECT e.id, e.alarm_label FROM events e "
            "JOIN challenges c ON c.event_id = e.id "
            "WHERE c.user_id = ? AND e.state IN ('ringing','snoozed') "
            "ORDER BY e.fired_at DESC LIMIT 1",
            (user_id,),
        )


    # ----------------------------------------------------------------- music
    def add_music(self, name: str, stored_name: str, mime: str, size: int) -> dict:
        with self.tx() as c:
            cur = c.execute(
                "INSERT INTO music(name, stored_name, mime, size, created_at) "
                "VALUES(?,?,?,?,?)",
                (name, stored_name, mime, size, time.time()),
            )
            music_id = int(cur.lastrowid)
        return self.get_music(music_id)  # type: ignore[return-value]

    def list_music(self) -> list[dict]:
        return self._all("SELECT * FROM music ORDER BY id DESC")

    def get_music(self, music_id: int) -> dict | None:
        return self._one("SELECT * FROM music WHERE id = ?", (music_id,))

    def music_in_use(self, music_id: int) -> dict:
        alarm = self._one(
            "SELECT id, label FROM alarms WHERE music_id = ? ORDER BY id LIMIT 1",
            (music_id,),
        )
        event = self._one(
            "SELECT id, alarm_label FROM events WHERE music_id = ? "
            "AND state IN ('ringing','snoozed') ORDER BY id DESC LIMIT 1",
            (music_id,),
        )
        return {"alarm": alarm, "event": event}

    def delete_music(self, music_id: int) -> bool:
        return self._exec("DELETE FROM music WHERE id = ?", (music_id,)) > 0

    # ------------------------------------------------------------- questions
    def list_questions(self) -> list[dict]:
        return self._all("SELECT * FROM questions ORDER BY id DESC")

    def get_question(self, question_id: int) -> dict | None:
        return self._one("SELECT * FROM questions WHERE id = ?", (question_id,))

    def add_question(
        self, question: str, answer: str, kind: str = "text", options: str | None = None
    ) -> dict:
        with self.tx() as c:
            cur = c.execute(
                "INSERT INTO questions(question, answer, kind, options, created_at) "
                "VALUES(?,?,?,?,?)",
                (question, answer, kind, options, time.time()),
            )
            question_id = int(cur.lastrowid)
        return self.get_question(question_id)  # type: ignore[return-value]

    def update_question(
        self, question_id: int, question: str, answer: str,
        kind: str = "text", options: str | None = None,
    ) -> dict | None:
        self._exec(
            "UPDATE questions SET question=?, answer=?, kind=?, options=? WHERE id=?",
            (question, answer, kind, options, question_id),
        )
        return self.get_question(question_id)

    def delete_question(self, question_id: int) -> bool:
        return self._exec("DELETE FROM questions WHERE id = ?", (question_id,)) > 0

    def count_questions(self, kind: str | None = None) -> int:
        if kind is None:
            row = self._one("SELECT COUNT(*) AS n FROM questions")
        else:
            row = self._one(
                "SELECT COUNT(*) AS n FROM questions WHERE kind = ?", (kind,)
            )
        return int(row["n"]) if row else 0

    # ------------------------------------------------------------- calendars
    def create_calendar(self, name: str, days: list[dict]) -> dict:
        with self.tx() as c:
            cur = c.execute(
                "INSERT INTO calendars(name, created_at) VALUES(?,?)",
                (name, time.time()),
            )
            calendar_id = int(cur.lastrowid)
            c.executemany(
                "INSERT INTO calendar_days(calendar_id, date, kind, note) "
                "VALUES(?,?,?,?)",
                [
                    (calendar_id, d["date"], d["kind"], d.get("note") or None)
                    for d in days
                ],
            )
        return self.get_calendar(calendar_id)  # type: ignore[return-value]

    def list_calendars(self) -> list[dict]:
        return self._all(
            """SELECT c.*,
                      COUNT(d.date) AS day_count,
                      SUM(CASE WHEN d.kind='working' THEN 1 ELSE 0 END) AS working_days,
                      SUM(CASE WHEN d.kind='holiday' THEN 1 ELSE 0 END) AS holiday_days,
                      MIN(d.date) AS first_date,
                      MAX(d.date) AS last_date,
                      (SELECT COUNT(*) FROM alarms a WHERE a.calendar_id = c.id) AS alarms_using
               FROM calendars c
               LEFT JOIN calendar_days d ON d.calendar_id = c.id
               GROUP BY c.id ORDER BY c.id DESC"""
        )

    def get_calendar(self, calendar_id: int) -> dict | None:
        return self._one("SELECT * FROM calendars WHERE id = ?", (calendar_id,))

    def calendar_day_map(self, calendar_id: int | None) -> dict[str, str]:
        if not calendar_id:
            return {}
        rows = self._all(
            "SELECT date, kind FROM calendar_days WHERE calendar_id = ?",
            (calendar_id,),
        )
        return {r["date"]: r["kind"] for r in rows}

    def delete_calendar(self, calendar_id: int) -> bool:
        with self.tx() as c:
            c.execute(
                "UPDATE alarms SET calendar_id=NULL WHERE calendar_id=?", (calendar_id,)
            )
            cur = c.execute("DELETE FROM calendars WHERE id = ?", (calendar_id,))
            return cur.rowcount > 0

    # ---------------------------------------------------------------- alarms
    def list_alarms(self) -> list[dict]:
        return self._all(
            """SELECT a.*,
                      (SELECT COUNT(*) FROM alarm_users au WHERE au.alarm_id = a.id)
                          AS participant_count
               FROM alarms a ORDER BY a.time, a.id"""
        )

    def get_alarm(self, alarm_id: int) -> dict | None:
        return self._one(
            """SELECT a.*,
                      (SELECT COUNT(*) FROM alarm_users au WHERE au.alarm_id = a.id)
                          AS participant_count
               FROM alarms a WHERE a.id = ?""",
            (alarm_id,),
        )

    def get_alarm_by_slug(self, slug: str) -> dict | None:
        return self._one(
            "SELECT * FROM alarms WHERE slug = ? COLLATE NOCASE", (slug,)
        )

    def slug_taken(self, slug: str, exclude_id: int | None = None) -> bool:
        if exclude_id:
            row = self._one(
                "SELECT 1 FROM alarms WHERE slug = ? COLLATE NOCASE AND id != ?",
                (slug, exclude_id),
            )
        else:
            row = self._one(
                "SELECT 1 FROM alarms WHERE slug = ? COLLATE NOCASE", (slug,)
            )
        return row is not None

    def alarm_participants(self, alarm_id: int) -> list[dict]:
        return self._all(
            """SELECT u.id, u.name, u.active, u.created_at
               FROM alarm_users au JOIN users u ON u.id = au.user_id
               WHERE au.alarm_id = ? ORDER BY u.id""",
            (alarm_id,),
        )

    def _set_participants(self, conn, alarm_id: int, user_ids: list[int]) -> None:
        conn.execute("DELETE FROM alarm_users WHERE alarm_id = ?", (alarm_id,))
        conn.executemany(
            "INSERT OR IGNORE INTO alarm_users(alarm_id, user_id) VALUES(?,?)",
            [(alarm_id, uid) for uid in user_ids],
        )

    def create_alarm(self, a: dict) -> dict:
        now = time.time()
        with self.tx() as c:
            cur = c.execute(
                """INSERT INTO alarms
                   (label, time, days_mask, once_date, enabled, mode, difficulty,
                    snooze_minutes, max_snoozes, max_ring_minutes, next_fire,
                    created_at, slug, completion_mode, target_count, challenge_count,
                    question_source, challenge_type, music_id, calendar_id)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    a["label"], a["time"], a["days_mask"], a["once_date"],
                    1 if a["enabled"] else 0, a["mode"], a["difficulty"],
                    a["snooze_minutes"], a["max_snoozes"], a["max_ring_minutes"],
                    a.get("next_fire"), now, a.get("slug"),
                    a.get("completion_mode", "all"), a.get("target_count", 1),
                    a.get("challenge_count", 1),
                    a.get("question_source", "auto"), a.get("challenge_type", "math"),
                    a.get("music_id"), a.get("calendar_id"),
                ),
            )
            alarm_id = int(cur.lastrowid)
            self._set_participants(c, alarm_id, a.get("participants") or [])
        return self.get_alarm(alarm_id)  # type: ignore[return-value]

    def update_alarm(self, alarm_id: int, a: dict) -> dict | None:
        with self.tx() as c:
            c.execute(
                """UPDATE alarms SET label=?, time=?, days_mask=?, once_date=?,
                   enabled=?, mode=?, difficulty=?, snooze_minutes=?, max_snoozes=?,
                   max_ring_minutes=?, next_fire=?, slug=?, completion_mode=?,
                   target_count=?, challenge_count=?, question_source=?,
                   challenge_type=?, music_id=?, calendar_id=? WHERE id=?""",
                (
                    a["label"], a["time"], a["days_mask"], a["once_date"],
                    1 if a["enabled"] else 0, a["mode"], a["difficulty"],
                    a["snooze_minutes"], a["max_snoozes"], a["max_ring_minutes"],
                    a.get("next_fire"), a.get("slug"),
                    a.get("completion_mode", "all"), a.get("target_count", 1),
                    a.get("challenge_count", 1),
                    a.get("question_source", "auto"), a.get("challenge_type", "math"),
                    a.get("music_id"), a.get("calendar_id"), alarm_id,
                ),
            )
            self._set_participants(c, alarm_id, a.get("participants") or [])
        return self.get_alarm(alarm_id)

    def set_alarm_enabled(
        self, alarm_id: int, enabled: bool, next_fire: float | None
    ) -> None:
        self._exec(
            "UPDATE alarms SET enabled=?, next_fire=? WHERE id=?",
            (1 if enabled else 0, next_fire, alarm_id),
        )

    def set_next_fire(self, alarm_id: int, next_fire: float | None) -> None:
        self._exec("UPDATE alarms SET next_fire=? WHERE id=?", (next_fire, alarm_id))

    def mark_alarm_fired(self, alarm_id: int, when: float) -> None:
        self._exec("UPDATE alarms SET last_fired_at=? WHERE id=?", (when, alarm_id))

    def set_alarm_skip(self, alarm_id: int, skip: bool) -> None:
        self._exec(
            "UPDATE alarms SET skip_next=? WHERE id=?", (1 if skip else 0, alarm_id)
        )

    def set_alarm_link_expiry(self, alarm_id: int, expires_at: float | None) -> None:
        self._exec(
            "UPDATE alarms SET link_expires_at=? WHERE id=?", (expires_at, alarm_id)
        )

    def set_alarm_link(self, alarm_id: int, slug: str, expires_at: float | None) -> None:
        self._exec(
            "UPDATE alarms SET slug=?, link_expires_at=? WHERE id=?",
            (slug, expires_at, alarm_id),
        )

    def retire_link(self, slug: str, label: str, expires_at: float) -> None:
        with self.tx() as c:
            c.execute(
                "INSERT INTO retired_links(slug, label, expires_at) VALUES(?,?,?) "
                "ON CONFLICT(slug) DO UPDATE SET label=excluded.label, expires_at=excluded.expires_at",
                (slug, label, expires_at),
            )

    def get_retired_link(self, slug: str) -> dict | None:
        return self._one(
            "SELECT * FROM retired_links WHERE slug = ? COLLATE NOCASE", (slug,)
        )

    def delete_alarm(self, alarm_id: int) -> bool:
        return self._exec("DELETE FROM alarms WHERE id = ?", (alarm_id,)) > 0

    def due_alarms(self, now: float) -> list[dict]:
        return self._all(
            "SELECT * FROM alarms WHERE enabled=1 AND next_fire IS NOT NULL "
            "AND next_fire <= ? ORDER BY next_fire",
            (now,),
        )

    # ---------------------------------------------------------------- events
    def create_event(
        self,
        *,
        alarm_id: int | None,
        alarm_label: str,
        mode: str,
        difficulty: str,
        fired_at: float,
        ends_at: float | None,
        max_snoozes: int = 2,
        snooze_minutes: int = 9,
        max_ring_minutes: int = 15,
        state: str = "ringing",
        stop_reason: str | None = None,
        stopped_at: float | None = None,
        manual: bool = False,
        completion_mode: str = "all",
        target_count: int = 1,
        challenge_count: int = 1,
        question_source: str = "auto",
        challenge_type: str = "math",
        shared_questions: str | None = None,
        music_id: int | None = None,
        music_name: str | None = None,
    ) -> dict:
        with self.tx() as c:
            cur = c.execute(
                """INSERT INTO events
                   (alarm_id, alarm_label, mode, difficulty, state, fired_at, ends_at,
                    stop_reason, stopped_at, max_snoozes, snooze_minutes,
                    max_ring_minutes, manual, completion_mode, target_count,
                    challenge_count, question_source, challenge_type,
                    shared_questions, music_id, music_name)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    alarm_id, alarm_label, mode, difficulty, state, fired_at, ends_at,
                    stop_reason, stopped_at, max_snoozes, snooze_minutes,
                    max_ring_minutes, 1 if manual else 0, completion_mode,
                    target_count, challenge_count, question_source, challenge_type,
                    shared_questions, music_id, music_name,
                ),
            )
            event_id = int(cur.lastrowid)
        return self.get_event(event_id)  # type: ignore[return-value]

    def get_event(self, event_id: int) -> dict | None:
        return self._one("SELECT * FROM events WHERE id = ?", (event_id,))

    def set_event_challenge_type(self, event_id: int, challenge_type: str) -> None:
        self._exec(
            "UPDATE events SET challenge_type=? WHERE id=?",
            (challenge_type, event_id),
        )

    def list_events(self, limit: int = 20, states: tuple[str, ...] | None = None) -> list[dict]:
        if states:
            marks = ",".join("?" for _ in states)
            return self._all(
                f"SELECT * FROM events WHERE state IN ({marks}) "
                "ORDER BY fired_at DESC LIMIT ?",
                (*states, limit),
            )
        return self._all(
            "SELECT * FROM events ORDER BY fired_at DESC LIMIT ?", (limit,)
        )

    def list_events_with_counts(self, limit: int = 20) -> list[dict]:
        return self._all(
            """SELECT e.*,
                      (SELECT COUNT(*) FROM challenges c WHERE c.event_id = e.id) AS total,
                      (SELECT COUNT(*) FROM challenges c
                        WHERE c.event_id = e.id AND c.answered_at IS NOT NULL) AS answered
               FROM events e ORDER BY e.fired_at DESC LIMIT ?""",
            (limit,),
        )

    def active_events(self) -> list[dict]:
        return self._all(
            """SELECT e.*,
                      (SELECT COUNT(*) FROM challenges c WHERE c.event_id = e.id) AS total,
                      (SELECT COUNT(*) FROM challenges c
                        WHERE c.event_id = e.id AND c.answered_at IS NOT NULL) AS answered
               FROM events e WHERE e.state IN ('ringing','snoozed')
               ORDER BY e.fired_at DESC LIMIT 20"""
        )

    def refire_event(self, event_id: int, ends_at: float) -> None:
        self._exec(
            "UPDATE events SET state='ringing', ends_at=?, snooze_until=NULL, "
            "stopped_at=NULL WHERE id=? AND state='snoozed'",
            (ends_at, event_id),
        )

    def snoozed_events(self) -> list[dict]:
        return self._all(
            "SELECT * FROM events WHERE state='snoozed' ORDER BY snooze_until"
        )

    def active_event_for_alarm(self, alarm_id: int) -> dict | None:
        return self._one(
            "SELECT * FROM events WHERE alarm_id = ? AND state IN ('ringing','snoozed') "
            "ORDER BY fired_at DESC LIMIT 1",
            (alarm_id,),
        )

    def latest_event_for_alarm(self, alarm_id: int) -> dict | None:
        return self._one(
            "SELECT * FROM events WHERE alarm_id = ? ORDER BY fired_at DESC LIMIT 1",
            (alarm_id,),
        )

    def set_event_state(
        self,
        event_id: int,
        state: str,
        *,
        stopped_at: float | None = None,
        stop_reason: str | None = None,
        ends_at: float | None = None,
        snooze_until: float | None = None,
        snooze_count: int | None = None,
    ) -> None:
        sets = ["state = ?"]
        params: list = [state]
        if stopped_at is not None:
            sets.append("stopped_at = ?")
            params.append(stopped_at)
        if stop_reason is not None:
            sets.append("stop_reason = ?")
            params.append(stop_reason)
        if ends_at is not None:
            sets.append("ends_at = ?")
            params.append(ends_at)
        if snooze_until is not None:
            sets.append("snooze_until = ?")
            params.append(snooze_until)
        if snooze_count is not None:
            sets.append("snooze_count = ?")
            params.append(snooze_count)
        params.append(event_id)
        self._exec(f"UPDATE events SET {', '.join(sets)} WHERE id = ?", params)

    def finish_event(self, event_id: int, state: str, reason: str) -> None:
        self._exec(
            "UPDATE events SET state=?, stopped_at=?, stop_reason=? WHERE id=? "
            "AND state IN ('ringing','snoozed')",
            (state, time.time(), reason, event_id),
        )

    def interrupt_stale_events(self) -> int:
        return self._exec(
            "UPDATE events SET state='interrupted', stopped_at=?, "
            "stop_reason='server restarted while ringing' "
            "WHERE state='ringing'",
            (time.time(),),
        )

    # ------------------------------------------------------------ challenges
    def add_challenge(
        self,
        event_id: int,
        user_id: int | None,
        user_name: str,
        token: str,
        question: str,
        answer: str,
        answer_type: str = "number",
        question_id: int | None = None,
        challenge_type: str = "math",
        payload: str | None = None,
    ) -> None:
        self._exec(
            """INSERT INTO challenges
               (event_id, user_id, user_name, token, question, answer,
                answer_type, challenge_type, payload, question_id, created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (
                event_id, user_id, user_name, token, question, answer,
                answer_type, challenge_type, payload, question_id, time.time(),
            ),
        )

    def list_challenges(self, event_id: int) -> list[dict]:
        return self._all(
            "SELECT * FROM challenges WHERE event_id = ? ORDER BY id", (event_id,)
        )

    def get_challenge_by_token(self, token: str) -> dict | None:
        return self._one("SELECT * FROM challenges WHERE token = ?", (token,))

    def get_challenge_for_user(self, event_id: int, user_id: int) -> dict | None:
        return self._one(
            "SELECT * FROM challenges WHERE event_id = ? AND user_id = ?",
            (event_id, user_id),
        )

    def count_unanswered(self, event_id: int) -> int:
        row = self._one(
            "SELECT COUNT(*) AS n FROM challenges "
            "WHERE event_id = ? AND answered_at IS NULL",
            (event_id,),
        )
        return int(row["n"]) if row else 0

    def count_answered(self, event_id: int) -> int:
        row = self._one(
            "SELECT COUNT(*) AS n FROM challenges "
            "WHERE event_id = ? AND answered_at IS NOT NULL",
            (event_id,),
        )
        return int(row["n"]) if row else 0

    def count_challenges(self, event_id: int) -> int:
        row = self._one(
            "SELECT COUNT(*) AS n FROM challenges WHERE event_id = ?", (event_id,)
        )
        return int(row["n"]) if row else 0

    def advance_challenge(
        self, challenge_id: int, question: str, answer: str,
        answer_type: str, question_id: int | None,
        challenge_type: str = "math", payload: str | None = None,
    ) -> None:
        self._exec(
            "UPDATE challenges SET solved = solved + 1, question=?, answer=?, "
            "answer_type=?, challenge_type=?, payload=?, question_id=? WHERE id=?",
            (question, answer, answer_type, challenge_type, payload, question_id, challenge_id),
        )

    def mark_challenge_answered(self, challenge_id: int) -> bool:
        return (
            self._exec(
                "UPDATE challenges SET answered_at=? WHERE id=? AND answered_at IS NULL",
                (time.time(), challenge_id),
            )
            > 0
        )

    def wrong_challenge_answer(
        self,
        challenge_id: int,
        question: str,
        answer: str,
        answer_type: str = "number",
        question_id: int | None = None,
        challenge_type: str = "math",
        payload: str | None = None,
    ) -> None:
        self._exec(
            "UPDATE challenges SET attempts = attempts + 1, question=?, answer=?, "
            "answer_type=?, challenge_type=?, payload=?, question_id=? WHERE id=?",
            (question, answer, answer_type, challenge_type, payload, question_id, challenge_id),
        )

    # --------------------------------------------------------------- sessions
    def add_session(self, token_hash: str, expires_at: float, user_agent: str) -> None:
        self._exec(
            "INSERT INTO sessions(token_hash, created_at, expires_at, user_agent) "
            "VALUES(?,?,?,?)",
            (token_hash, time.time(), expires_at, user_agent[:200]),
        )

    def get_session(self, token_hash: str) -> dict | None:
        return self._one(
            "SELECT * FROM sessions WHERE token_hash = ? AND expires_at > ?",
            (token_hash, time.time()),
        )

    def delete_session(self, token_hash: str) -> None:
        self._exec("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))

    def delete_other_sessions(self, keep_hash: str | None) -> None:
        if keep_hash:
            self._exec("DELETE FROM sessions WHERE token_hash != ?", (keep_hash,))
        else:
            self._exec("DELETE FROM sessions")

    def purge_expired_sessions(self) -> None:
        self._exec("DELETE FROM sessions WHERE expires_at <= ?", (time.time(),))

    # ------------------------------------------------------------ maintenance
    def prune_history(self, keep: int = 500) -> int:
        with self.tx() as c:
            cur = c.execute(
                "DELETE FROM events WHERE id NOT IN "
                "(SELECT id FROM events ORDER BY fired_at DESC LIMIT ?)",
                (keep,),
            )
            return cur.rowcount
