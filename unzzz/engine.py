"""The alarm engine: one scheduler thread and one ring thread per active event."""

from __future__ import annotations

import json
import logging
import secrets
import threading
import time
from pathlib import Path

from .audio import Audio
from .db import Store
from .challenge_types import (
    CUSTOM_TYPES,
    check_answer,
    generate_challenge,
    payload_object,
    spec_payload,
)
from .volume import DEFAULT_TARGET as VOLUME_DEFAULT, VolumeController
from .schedule import (
    detect_system_timezone,
    load_timezone,
    next_occurrence,
    now_local,
    parse_answer,
)

log = logging.getLogger("unzzz.engine")

MISSED_GRACE = 120.0          # seconds late that still counts as "fire now"
SNOOZE_GRACE = 600.0          # seconds late that a snooze may still resume
PRUNE_EVERY = 6 * 3600
HISTORY_KEEP = 500
LINK_RETENTION_DEFAULT = 30       # minutes after a stopped alarm
LINK_RETENTION_MAX = 1440
PUBLIC_LINK_TTL = 6 * 3600       # public link lifetime after stop/disable

_rng = secrets.SystemRandom()


class EngineError(Exception):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


class RingSession:
    def __init__(self, event_id: int) -> None:
        self.event_id = event_id
        self.stop = threading.Event()
        self.thread: threading.Thread | None = None


class Engine:
    def __init__(
        self,
        store: Store,
        data_dir: Path,
        audio_command: str | None = None,
        audio_device: str | None = None,
    ) -> None:
        self.store = store
        self.data_dir = Path(data_dir)
        self.audio = Audio(self.data_dir, command=audio_command)
        self.audio.set_device(
            audio_device if audio_device is not None
            else (store.get_setting("audio_device") or "")
        )
        try:
            target_volume = int(store.get_setting("target_volume") or VOLUME_DEFAULT)
        except (TypeError, ValueError):
            target_volume = VOLUME_DEFAULT
        self.volume = VolumeController(
            device=self.audio.device, target=target_volume, store=store
        )
        self.preview_music_id: int | None = None
        self.rings: dict[int, RingSession] = {}
        self.lock = threading.RLock()
        self._stop = threading.Event()
        self._ticker: threading.Thread | None = None
        self._calendar_cache: dict[int, dict[str, str]] = {}
        tz_name = store.get_setting("timezone") or detect_system_timezone()
        self._tz_name = tz_name
        self._tz = load_timezone(tz_name)
        if not store.get_setting("timezone"):
            store.set_setting("timezone", tz_name)
        self._last_prune = 0.0
        try:
            self.link_retention_minutes = max(
                0,
                min(
                    LINK_RETENTION_MAX,
                    int(store.get_setting("link_retention_minutes") or LINK_RETENTION_DEFAULT),
                ),
            )
        except (TypeError, ValueError):
            self.link_retention_minutes = LINK_RETENTION_DEFAULT

    # ------------------------------------------------------------- lifecycle
    @property
    def tz(self):
        return self._tz

    @property
    def tz_name(self) -> str:
        return self._tz_name

    def set_timezone(self, name: str) -> None:
        self._tz = load_timezone(name)
        self._tz_name = name
        self.store.set_setting("timezone", name)
        self.recompute_schedules()

    def set_audio_device(self, value: str) -> None:
        self.audio.set_device(value)
        self.volume.set_device(value)
        self.store.set_setting("audio_device", value)

    def set_target_volume(self, value: int) -> None:
        self.volume.set_target(value)
        self.store.set_setting("target_volume", str(self.volume.target))

    def set_link_retention(self, minutes: int) -> None:
        self.link_retention_minutes = max(0, min(LINK_RETENTION_MAX, int(minutes)))
        self.store.set_setting("link_retention_minutes", str(self.link_retention_minutes))

    def alarm_link_expired(self, alarm: dict, now: float | None = None) -> bool:
        expires = alarm.get("link_expires_at")
        if not expires:
            return False
        return (time.time() if now is None else now) >= float(expires)

    def expire_alarm_link(self, alarm_id: int, now: float | None = None) -> None:
        alarm = self.store.get_alarm(alarm_id)
        if not alarm or not alarm.get("slug"):
            return
        current = alarm.get("link_expires_at")
        now_ts = time.time() if now is None else now
        if current and float(current) > now_ts:
            # Respect a manually chosen future expiry.
            return
        self.store.set_alarm_link_expiry(alarm_id, now_ts + PUBLIC_LINK_TTL)

    def clear_alarm_link_expiry(self, alarm_id: int) -> None:
        self.store.set_alarm_link_expiry(alarm_id, None)

    def link_expired(self, event: dict, now: float | None = None) -> bool:
        """True once a finished event's challenge links have been retired."""
        if event.get("state") in ("ringing", "snoozed"):
            return False
        stopped = event.get("stopped_at") or event.get("fired_at")
        if not stopped:
            return False
        return (time.time() if now is None else now) >= (
            float(stopped) + self.link_retention_minutes * 60
        )

    def calendar_map(self, calendar_id: int | None) -> dict[str, str]:
        if not calendar_id:
            return {}
        calendar_id = int(calendar_id)
        cached = self._calendar_cache.get(calendar_id)
        if cached is None:
            cached = self.store.calendar_day_map(calendar_id)
            self._calendar_cache[calendar_id] = cached
        return cached

    def invalidate_calendars(self) -> None:
        self._calendar_cache.clear()

    def next_fire_for(self, alarm: dict, after_ts: float | None = None) -> float | None:
        return next_occurrence(
            hhmm=alarm["time"],
            days_mask=alarm["days_mask"],
            once_date=alarm["once_date"],
            tz=self._tz,
            after_ts=after_ts,
            calendar=self.calendar_map(alarm.get("calendar_id")),
        )

    def recompute_schedules(self) -> None:
        now = time.time()
        for alarm in self.store.list_alarms():
            if not alarm["enabled"]:
                continue
            nf = self.next_fire_for(alarm, after_ts=now)
            self.store.set_next_fire(alarm["id"], nf)
            if nf is None:
                log.warning(
                    "alarm %s has no future active day with its calendar", alarm["id"]
                )

    def start(self) -> None:
        self.store.interrupt_stale_events()
        self.volume.restore_persisted()
        for alarm in self.store.list_alarms():
            if alarm["enabled"] and alarm["next_fire"] is None:
                nf = self.next_fire_for(alarm)
                self.store.set_next_fire(alarm["id"], nf)
        self._ticker = threading.Thread(
            target=self._tick_loop, name="unzzz-ticker", daemon=True
        )
        self._ticker.start()
        log.info(
            "engine started (tz=%s, audio=%s, %d alarm(s))",
            self._tz_name,
            self.audio.backend,
            len(self.store.list_alarms()),
        )

    def stop(self) -> None:
        self._stop.set()
        self.audio.stop_preview()
        self.preview_music_id = None
        self.volume.end_all()
        with self.lock:
            sessions = list(self.rings.values())
        for session in sessions:
            session.stop.set()
        self.audio.stop_current()
        if self._ticker and self._ticker.is_alive():
            self._ticker.join(timeout=3)
        for session in sessions:
            if session.thread and session.thread.is_alive():
                session.thread.join(timeout=2)

    # ---------------------------------------------------------------- ticker
    def _tick_loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:  # keep the alarm server alive no matter what
                log.exception("scheduler tick failed")
            self._stop.wait(1.0)

    def tick(self, now: float | None = None) -> None:
        now = time.time() if now is None else now

        # Resume or abandon snoozed events.
        for event in self.store.snoozed_events():
            due = event.get("snooze_until") or 0
            if due > now:
                continue
            if now - due > SNOOZE_GRACE:
                self.store.finish_event(
                    event["id"], "missed", "snooze expired while server was down"
                )
                continue
            ends_at = now + event["max_ring_minutes"] * 60
            self.store.refire_event(event["id"], ends_at)
            self._start_ring(event["id"])
            log.info("event %s ringing again after snooze", event["id"])

        # Fire due alarms, or record them as missed if the clock ran away.
        busy_alarm_ids = {
            e["alarm_id"] for e in self.store.active_events() if e.get("alarm_id")
        }
        for alarm in self.store.due_alarms(now):
            if alarm.get("skip_next"):
                self._skip_occurrence(alarm, now)
                continue
            if alarm["id"] in busy_alarm_ids:
                self._advance_alarm(alarm, now)
                continue
            late = now - (alarm["next_fire"] or now)
            if late > MISSED_GRACE:
                self._record_missed(alarm, now, late)
            else:
                try:
                    self.fire_alarm(alarm["id"], manual=False)
                except EngineError as exc:
                    log.warning("could not fire alarm %s: %s", alarm["id"], exc.message)
                    self._advance_alarm(alarm, now)
                except Exception:
                    log.exception("unexpected failure firing alarm %s", alarm["id"])
                    self._advance_alarm(alarm, now)

        # Enforce maximum ring time / recover dead ring threads.
        for event in self.store.list_events(20, ("ringing",)):
            if event.get("ends_at") and now >= event["ends_at"]:
                self.stop_event(event["id"], "timed out", state="expired")
                continue
            with self.lock:
                has_session = event["id"] in self.rings
            if not has_session:
                self._start_ring(event["id"])

        if now - self._last_prune > PRUNE_EVERY:
            self._last_prune = now
            try:
                removed = self.store.prune_history(HISTORY_KEEP)
                if removed:
                    log.info("pruned %d old events", removed)
                self.store.purge_expired_sessions()
            except Exception:
                log.exception("maintenance failed")

    def _record_missed(self, alarm: dict, now: float, late: float) -> None:
        self.store.create_event(
            alarm_id=alarm["id"],
            alarm_label=alarm["label"],
            mode=alarm["mode"],
            difficulty=alarm["difficulty"],
            fired_at=alarm["next_fire"] or now,
            ends_at=None,
            max_snoozes=alarm["max_snoozes"],
            snooze_minutes=alarm["snooze_minutes"],
            max_ring_minutes=alarm["max_ring_minutes"],
            state="missed",
            stop_reason=f"missed: server was not running ({int(late)}s late)",
            stopped_at=now,
            completion_mode=alarm.get("completion_mode", "all"),
            target_count=alarm.get("target_count", 1),
            question_source=alarm.get("question_source", "auto"),
            challenge_type=alarm.get("challenge_type", "math"),
            music_id=alarm.get("music_id"),
            music_name=self.music_name(alarm.get("music_id")),
        )
        self._advance_alarm(alarm, now)
        log.warning("alarm %s was missed (%ds late)", alarm["id"], int(late))

    def _skip_occurrence(self, alarm: dict, now: float) -> None:
        self.store.set_alarm_skip(alarm["id"], False)
        self.store.create_event(
            alarm_id=alarm["id"],
            alarm_label=alarm["label"],
            mode=alarm["mode"],
            difficulty=alarm["difficulty"],
            fired_at=alarm.get("next_fire") or now,
            ends_at=None,
            max_snoozes=alarm["max_snoozes"],
            snooze_minutes=alarm["snooze_minutes"],
            max_ring_minutes=alarm["max_ring_minutes"],
            state="skipped",
            stop_reason="next occurrence skipped",
            stopped_at=now,
            completion_mode=alarm.get("completion_mode", "all"),
            target_count=alarm.get("target_count", 1),
            question_source=alarm.get("question_source", "auto"),
            challenge_type=alarm.get("challenge_type", "math"),
            music_id=alarm.get("music_id"),
            music_name=self.music_name(alarm.get("music_id")),
        )
        self._advance_alarm(alarm, now)
        log.info("alarm %s skipped its next occurrence", alarm["id"])

    def _advance_alarm(self, alarm: dict, now: float | None = None) -> None:
        now = time.time() if now is None else now
        if not alarm["days_mask"]:
            self.store.set_alarm_enabled(alarm["id"], False, None)
            return
        nf = self.next_fire_for(alarm, after_ts=now)
        self.store.set_next_fire(alarm["id"], nf)

    # ------------------------------------------------------------------ music
    def music_name(self, music_id: int | None) -> str | None:
        if not music_id:
            return None
        row = self.store.get_music(int(music_id))
        return row["name"] if row else None

    def music_path(self, music_id: int | None) -> Path | None:
        if not music_id:
            return None
        row = self.store.get_music(int(music_id))
        if not row:
            return None
        path = self.data_dir / "music" / row["stored_name"]
        return path if path.is_file() else None

    def _event_audio_path(self, event: dict) -> Path | None:
        return self.music_path(event.get("music_id"))

    # ------------------------------------------------------------------ fire
    def _selected_active_users(self, alarm_id: int) -> list[dict]:
        return [
            u for u in self.store.alarm_participants(alarm_id)
            if u.get("active")
        ][:6]

    def fire_alarm(self, alarm_id: int, manual: bool = False) -> dict:
        now = time.time()
        with self.lock:
            alarm = self.store.get_alarm(alarm_id)
            if not alarm:
                raise EngineError("Alarm not found", 404)
            for active in self.store.active_events():
                if active["alarm_id"] == alarm_id and active["state"] in ("ringing", "snoozed"):
                    raise EngineError("This alarm is already ringing or snoozed", 409)

            participants = self._selected_active_users(alarm_id)
            mode = alarm["mode"]
            if mode == "challenge" and not participants:
                mode = "standard"
                log.warning(
                    "challenge alarm %s degraded to standard: no active selected users",
                    alarm_id,
                )

            completion_mode = "all"
            target_count = 1
            challenge_type = "math"
            challenge_count = 1
            plan: list[dict] = []
            shared_specs: list[dict | None] = []
            if mode == "challenge":
                completion_mode = alarm.get("completion_mode", "all")
                if completion_mode == "count":
                    target_count = max(
                        1, min(int(alarm.get("target_count", 1)), len(participants))
                    )
                else:
                    target_count = len(participants)
                challenge_type = alarm.get("challenge_type", "math")
                challenge_count = max(1, min(10, int(alarm.get("challenge_count", 1))))
                try:
                    raw_plan = json.loads(alarm.get("challenge_plan") or "[]")
                except (TypeError, ValueError):
                    raw_plan = []
                if not isinstance(raw_plan, list) or len(raw_plan) != challenge_count:
                    raw_plan = [challenge_type] * challenge_count
                pool = self.store.list_questions()
                plan = []
                for item in raw_plan:
                    if isinstance(item, str):
                        item = {"type": item}
                    if not isinstance(item, dict):
                        item = {"type": "math"}
                    kind = str(item.get("type", "math"))
                    pool_kind = "choice" if kind == "random_choice" else kind
                    if kind in CUSTOM_TYPES and not any(
                        (q.get("kind") or "text") == pool_kind for q in pool
                    ):
                        kind = "math"
                        log.warning(
                            "no %s questions left; using generated maths",
                            pool_kind,
                        )
                    step = {"type": kind}
                    if kind == "pattern":
                        try:
                            size = int(item.get("size", 3))
                        except (TypeError, ValueError):
                            size = 3
                        step["size"] = size if size in (3, 6, 9) else 3
                    plan.append(step)
                challenge_type = plan[0]["type"] if plan else "math"
                shared_specs = [None] * challenge_count
                for index, step in enumerate(plan):
                    if step.get("type") == "random_choice":
                        choices = [
                            q for q in pool if (q.get("kind") or "text") == "choice"
                        ]
                        if choices:
                            shared_specs[index] = generate_challenge(
                                "choice", alarm["difficulty"], choices
                            )

            music_id = alarm.get("music_id")
            music_row = self.store.get_music(int(music_id)) if music_id else None
            if music_row is None:
                music_id = None
            ends_at = now + alarm["max_ring_minutes"] * 60
            event = self.store.create_event(
                alarm_id=alarm["id"],
                alarm_label=alarm["label"],
                mode=mode,
                difficulty=alarm["difficulty"],
                fired_at=now,
                ends_at=ends_at,
                max_snoozes=alarm["max_snoozes"],
                snooze_minutes=alarm["snooze_minutes"],
                max_ring_minutes=alarm["max_ring_minutes"],
                manual=manual,
                completion_mode=completion_mode,
                target_count=target_count,
                challenge_count=challenge_count,
                challenge_plan=json.dumps(plan, separators=(",", ":")) if plan else None,
                muted=bool(alarm.get("muted")),
                question_source=(
                    "custom" if any(t in CUSTOM_TYPES for t in
                                    [step.get("type") for step in plan]) else "auto"
                ),
                challenge_type=challenge_type,
                shared_questions=json.dumps(shared_specs, separators=(",", ":"))
                if shared_specs else None,
                music_id=music_id,
                music_name=music_row["name"] if music_row else None,
            )
            if mode == "challenge":
                specs = []
                for _user in participants:
                    first = shared_specs[0] if shared_specs else None
                    specs.append(
                        first if first is not None else self._spec_for_step(
                            plan[0], alarm["difficulty"]
                        )
                    )
                event_type = challenge_type
                if event_type != event.get("challenge_type"):
                    self.store.set_event_challenge_type(event["id"], event_type)
                    event["challenge_type"] = event_type
                for user, spec in zip(participants, specs):
                    self.store.add_challenge(
                        event_id=event["id"],
                        user_id=user["id"],
                        user_name=user["name"],
                        token=secrets.token_urlsafe(18),
                        question=spec["question"],
                        answer=spec["answer"],
                        answer_type=spec["answer_type"],
                        question_id=spec["question_id"],
                        challenge_type=spec["challenge_type"],
                        payload=spec_payload(spec),
                    )
            self.store.mark_alarm_fired(alarm["id"], now)
            if not manual:
                self._advance_alarm(alarm, now)
            self._start_ring(event["id"])

        log.info(
            "event %s fired for '%s' (mode=%s, participants=%d, target=%s/%s, music=%s, manual=%s)",
            event["id"], alarm["label"], mode, len(participants),
            event["target_count"], completion_mode, event.get("music_name"), manual,
        )
        return event

    @staticmethod
    def _event_plan(event: dict) -> list[dict]:
        raw = event.get("challenge_plan")
        if raw:
            try:
                parsed = json.loads(raw)
            except (TypeError, ValueError):
                parsed = []
            if isinstance(parsed, list) and parsed:
                plan = []
                for item in parsed:
                    if isinstance(item, str):
                        item = {"type": item}
                    if not isinstance(item, dict):
                        continue
                    kind = str(item.get("type", "math"))
                    step = {"type": kind}
                    if kind == "pattern":
                        try:
                            step["size"] = int(item.get("size", 3))
                        except (TypeError, ValueError):
                            step["size"] = 3
                        if step["size"] not in (3, 6, 9):
                            step["size"] = 3
                    plan.append(step)
                if plan:
                    return plan
        count = max(1, int(event.get("challenge_count", 1)))
        kind = event.get("challenge_type", "math")
        return [{"type": kind} for _ in range(count)]

    def _spec_for_step(
        self, step: dict, difficulty: str, pool: list[dict] | None = None,
        exclude_question_id: int | None = None,
    ) -> dict:
        kind = str(step.get("type", "math"))
        if kind == "random_choice":
            kind = "choice"
        if kind in CUSTOM_TYPES:
            pool_kind = "choice" if kind == "choice" else kind
            if not any(
                (q.get("kind") or "text") == pool_kind
                for q in (pool if pool is not None else self.store.list_questions())
            ):
                kind = "math"
        return generate_challenge(
            kind,
            difficulty,
            pool if pool is not None else self.store.list_questions(),
            exclude_question_id=exclude_question_id,
            pattern_size=int(step.get("size", 3) or 3),
        )

    def _next_question_for_challenge(self, event: dict, challenge: dict) -> dict:
        kind = challenge.get("challenge_type", "math")
        payload = payload_object(challenge.get("payload"))
        step = {"type": kind, "size": payload.get("size", 3)}
        return self._spec_for_step(
            step,
            event.get("difficulty", "normal"),
            exclude_question_id=challenge.get("question_id"),
        )

    def _random_choice_specs(
        self, count: int, difficulty: str, pool: list[dict] | None = None
    ) -> list[dict]:
        pool = pool if pool is not None else self.store.list_questions()
        choices = [q for q in pool if (q.get("kind") or "text") == "choice"]
        if not choices:
            return []
        return [
            generate_challenge("choice", difficulty, choices)
            for _ in range(max(1, min(10, int(count))))
        ]

    def _challenge_specs(
        self, count: int, kind: str, difficulty: str
    ) -> list[dict]:
        pool = self.store.list_questions()
        if kind in CUSTOM_TYPES and not any(
            (q.get("kind") or "text") == kind for q in pool
        ):
            kind = "math"
        specs = []
        used: set[int] = set()
        for _ in range(count):
            spec = generate_challenge(kind, difficulty, pool)
            if spec["question_id"]:
                if spec["question_id"] in used:
                    spec = generate_challenge(
                        kind, difficulty, pool, exclude_question_id=None
                    )
                used.add(spec["question_id"])
            specs.append(spec)
        return specs

    def _next_question(self, event: dict, current_question_id: int | None = None) -> dict:
        kind = event.get("challenge_type", "math")
        if kind == "random_choice":
            kind = "choice"
        if kind in CUSTOM_TYPES and not any(
            (q.get("kind") or "text") == kind for q in self.store.list_questions()
        ):
            kind = "math"
        return generate_challenge(
            kind,
            event.get("difficulty", "normal"),
            self.store.list_questions(),
            exclude_question_id=current_question_id,
        )

    # ------------------------------------------------------------------- ring
    def _start_ring(self, event_id: int) -> None:
        with self.lock:
            session = self.rings.get(event_id)
            if session and session.thread and session.thread.is_alive():
                return
            event = self.store.get_event(event_id)
            if not event or event["state"] != "ringing":
                return
            if event.get("muted"):
                return
            session = RingSession(event_id)
            self.rings[event_id] = session
            thread = threading.Thread(
                target=self._ring_worker,
                args=(event_id, session),
                name=f"unzzz-ring-{event_id}",
                daemon=True,
            )
            session.thread = thread
        self.audio.stop_preview()
        self.preview_music_id = None
        self.volume.begin(event_id)
        thread.start()

    def _ring_worker(self, event_id: int, session: RingSession) -> None:
        try:
            event = self.store.get_event(event_id) or {}
            audio_path = self._event_audio_path(event)
            self.audio.ring_loop(session.stop, audio_path)
        except Exception:
            log.exception("ring worker %s crashed", event_id)
            try:
                self.stop_event(event_id, "audio failure", state="stopped")
            except Exception:
                log.exception("could not close failed event %s", event_id)
        finally:
            with self.lock:
                self.rings.pop(event_id, None)

    # --------------------------------------------------------------- previews
    def start_music_preview(self, music_id: int) -> dict:
        with self.lock:
            if self.rings:
                raise EngineError("Stop the alarm before testing music", 409)
        row = self.store.get_music(int(music_id))
        if not row:
            raise EngineError("Music not found", 404)
        path = self.data_dir / "music" / row["stored_name"]
        if not path.is_file():
            raise EngineError("Music file is missing", 404)
        ok, error = self.audio.start_preview(path)
        if not ok:
            raise EngineError(error or "Could not start playback", 400)
        with self.lock:
            self.preview_music_id = int(music_id)
        return self.music_preview_status()

    def stop_music_preview(self) -> dict:
        self.audio.stop_preview()
        with self.lock:
            self.preview_music_id = None
        return self.music_preview_status()

    def music_preview_status(self) -> dict:
        status = self.audio.preview_status()
        with self.lock:
            if not status["playing"]:
                self.preview_music_id = None
            return {
                "playing": bool(status["playing"]),
                "music_id": self.preview_music_id,
                "error": status.get("error"),
            }

    def _signal_ring(self, event_id: int) -> None:
        with self.lock:
            session = self.rings.get(event_id)
        if session:
            session.stop.set()

    def stop_event(self, event_id: int, reason: str, state: str = "stopped") -> dict:
        with self.lock:
            event = self.store.get_event(event_id)
            if not event:
                raise EngineError("Alarm event not found", 404)
            if event["state"] in ("ringing", "snoozed"):
                self.store.finish_event(event_id, state, reason)
            self._signal_ring(event_id)
            updated = self.store.get_event(event_id) or event
        self.volume.end(event_id)
        log.info("event %s closed: %s (%s)", event_id, reason, state)
        return updated

    def snooze_event(self, event_id: int) -> dict:
        now = time.time()
        with self.lock:
            event = self.store.get_event(event_id)
            if not event:
                raise EngineError("Alarm event not found", 404)
            if event["state"] != "ringing":
                raise EngineError("This alarm is not ringing", 409)
            total = self.store.count_challenges(event_id)
            if event["mode"] == "challenge" and total > 1:
                raise EngineError(
                    "Alarms for more than one person cannot be snoozed", 409
                )
            if event["snooze_count"] >= event["max_snoozes"]:
                raise EngineError("No snoozes left for this alarm", 409)
            until = now + event["snooze_minutes"] * 60
            self.store.set_event_state(
                event_id,
                "snoozed",
                snooze_until=until,
                snooze_count=event["snooze_count"] + 1,
            )
            self._signal_ring(event_id)
            updated = self.store.get_event(event_id) or event
        self.volume.end(event_id)
        log.info("event %s snoozed until %s", event_id, until)
        return updated

    # -------------------------------------------------------------- answering
    def answer(self, token: str, raw_answer: object) -> dict:
        challenge = self.store.get_challenge_by_token(token)
        if not challenge:
            raise EngineError("This link is not valid", 404)
        event = self.store.get_event(challenge["event_id"])
        if not event:
            raise EngineError("This alarm no longer exists", 404)
        if self.link_expired(event):
            raise EngineError("This challenge link has expired", 410)
        if challenge["answered_at"]:
            return {"status": "already", "answer": self._answer_state(event, challenge)}
        if event["state"] != "ringing":
            return {"status": "closed", "answer": self._answer_state(event, challenge)}

        ctype = challenge.get("challenge_type") or (
            "text" if challenge.get("answer_type") == "text" else "math"
        )
        if ctype == "math":
            if parse_answer(raw_answer) is None:
                raise EngineError("Enter a whole number", 400)
        elif ctype == "text":
            if not isinstance(raw_answer, (str, int, float)) or isinstance(raw_answer, bool):
                raise EngineError("Enter an answer", 400)
            if not str(raw_answer).strip():
                raise EngineError("Enter an answer", 400)
        elif ctype == "choice":
            if not isinstance(raw_answer, str) or not raw_answer.strip():
                raise EngineError("Choose an option", 400)
        elif ctype == "color":
            if not isinstance(raw_answer, str) or not raw_answer.strip():
                raise EngineError("Choose a color", 400)
        elif ctype == "pattern":
            if not isinstance(raw_answer, list) or not raw_answer:
                raise EngineError("Paint at least one cell", 400)
        elif ctype == "hold":
            if raw_answer not in ("held", "Held"):
                raise EngineError("Hold the button first", 400)
        elif ctype == "typing":
            if not isinstance(raw_answer, str) or not raw_answer.strip():
                raise EngineError("Type the phrase", 400)
        elif ctype == "dice":
            try:
                int(raw_answer)
            except (TypeError, ValueError):
                raise EngineError("Roll the dice first", 400)
        else:
            raise EngineError("Unknown challenge type", 400)

        with self.lock:
            challenge = self.store.get_challenge_by_token(token)
            if not challenge:
                raise EngineError("This link is not valid", 404)
            event = self.store.get_event(challenge["event_id"])
            if not event:
                raise EngineError("This alarm no longer exists", 404)
            if self.link_expired(event):
                raise EngineError("This challenge link has expired", 410)
            if challenge["answered_at"]:
                return {"status": "already", "answer": self._answer_state(event, challenge)}
            if event["state"] != "ringing":
                return {"status": "closed", "answer": self._answer_state(event, challenge)}

            correct = check_answer(
                challenge.get("challenge_type", "math"),
                challenge["answer"],
                raw_answer,
            )
            if correct:
                required = max(1, int(event.get("challenge_count", 1)))
                solved = int(challenge.get("solved", 0)) + 1
                if solved >= required:
                    # Final required challenge for this participant.
                    self.store.advance_challenge(
                        challenge["id"], challenge["question"], challenge["answer"],
                        challenge.get("answer_type", "number"), challenge.get("question_id"),
                        challenge.get("challenge_type", "math"), challenge.get("payload"),
                    )
                    self.store.mark_challenge_answered(challenge["id"])
                else:
                    spec = self._next_session_question(event, challenge, solved)
                    self.store.advance_challenge(
                        challenge["id"], spec["question"], spec["answer"],
                        spec.get("answer_type", "choice"), spec.get("question_id"),
                        spec.get("challenge_type", "choice"), spec_payload(spec),
                    )
                total = self.store.count_challenges(event["id"])
                answered = self.store.count_answered(event["id"])
                target = (
                    total if event.get("completion_mode", "all") == "all"
                    else min(int(event.get("target_count", 1)), total)
                )
                all_done = answered >= target
                reason = (
                    "answered by all users" if event.get("completion_mode", "all") == "all"
                    else f"answered by {target} of {total} users"
                )
                if all_done:
                    self.store.finish_event(event["id"], "completed", reason)
            else:
                spec = self._next_question_for_challenge(event, challenge)
                self.store.wrong_challenge_answer(
                    challenge["id"],
                    spec["question"],
                    spec["answer"],
                    spec["answer_type"],
                    spec["question_id"],
                    spec["challenge_type"],
                    spec_payload(spec),
                )
                challenge = self.store.get_challenge_by_token(token) or challenge
                event = self.store.get_event(event["id"]) or event
                return {
                    "status": "wrong",
                    "answer": self._answer_state(event, challenge),
                    "message": "Not right. Here is a new question.",
                }
            challenge = self.store.get_challenge_by_token(token) or challenge
            event = self.store.get_event(event["id"]) or event
        if all_done:
            self._signal_ring(event["id"])
            self.volume.end(event["id"])
            log.info(
                "event %s completed: %s/%s answered (%s)",
                event["id"], answered, total, reason,
            )
        return {
            "status": "correct",
            "all_done": all_done,
            "answer": self._answer_state(event, challenge),
            "message": "Alarm silenced. Good morning." if all_done
            else (
                f"Correct. {solved}/{required} challenges passed."
                if required > 1 else "Correct. Waiting for the others."
            ),
        }

    def _next_session_question(self, event: dict, challenge: dict, solved: int) -> dict:
        plan = self._event_plan(event)
        if 0 <= solved < len(plan):
            step = plan[solved]
            if step.get("type") == "random_choice":
                try:
                    shared = json.loads(event.get("shared_questions") or "[]")
                except (TypeError, ValueError):
                    shared = []
                if isinstance(shared, list) and solved < len(shared):
                    spec = shared[solved]
                    if isinstance(spec, dict) and "question" in spec:
                        spec.setdefault("answer_type", "choice")
                        spec.setdefault("challenge_type", "choice")
                        spec.setdefault("payload", {"options": []})
                        spec.setdefault("question_id", None)
                        return spec
            return self._spec_for_step(step, event.get("difficulty", "normal"))
        return self._next_question_for_challenge(event, challenge)

    def _answer_state(self, event: dict, challenge: dict) -> dict:
        participants = self.store.list_challenges(event["id"])
        return {
            "event_id": event["id"],
            "alarm_label": event["alarm_label"],
            "mode": event["mode"],
            "state": event["state"],
            "fired_at": event["fired_at"],
            "ends_at": event["ends_at"],
            "user_name": challenge["user_name"],
            "answered": bool(challenge["answered_at"]),
            "answered_at": challenge["answered_at"],
            "attempts": challenge["attempts"],
            "solved": int(challenge.get("solved", 0)),
            "required": max(1, int(event.get("challenge_count", 1))),
            "answer_type": challenge.get("answer_type", "number"),
            "challenge_type": challenge.get("challenge_type", "math"),
            "challenge_plan": self._event_plan(event),
            "alarm_slug": (
                self.store.get_alarm(int(event["alarm_id"]))["slug"]
                if event.get("alarm_id") else None
            ),
            "payload": payload_object(challenge.get("payload")),
            "completion_mode": event.get("completion_mode", "all"),
            "target_count": event.get("target_count", 1),
            "question": None
            if challenge["answered_at"] or event["state"] != "ringing"
            else challenge["question"],
            "participants": [
                {
                    "name": p["user_name"],
                    "answered": bool(p["answered_at"]),
                    "answered_at": p["answered_at"],
                    "attempts": p["attempts"],
                    "solved": int(p.get("solved", 0)),
                    "required": max(1, int(event.get("challenge_count", 1))),
                    "you": p["id"] == challenge["id"],
                }
                for p in participants
            ],
            "answered_count": sum(1 for p in participants if p["answered_at"]),
            "total": len(participants),
            "server_time": time.time(),
            "timezone": self._tz_name,
            "music_name": event.get("music_name"),
            "stop_reason": event.get("stop_reason"),
        }

    def token_state(self, token: str) -> dict | None:
        challenge = self.store.get_challenge_by_token(token)
        if not challenge:
            return None
        event = self.store.get_event(challenge["event_id"])
        if not event:
            return None
        if self.link_expired(event):
            raise EngineError("This challenge link has expired", 410)
        return self._answer_state(event, challenge)

    # ------------------------------------------------------------------ views
    def alarm_view(self, alarm: dict) -> dict:
        from .schedule import format_days, human_next, iso_local, mask_to_days

        participants = self.store.alarm_participants(alarm["id"])
        nf = alarm.get("next_fire")
        music_name = self.music_name(alarm.get("music_id"))
        calendar = (
            self.store.get_calendar(alarm["calendar_id"])
            if alarm.get("calendar_id") else None
        )
        target = alarm.get("target_count", 1)
        if alarm.get("completion_mode", "all") == "all":
            target = max(1, len(participants))
        return {
            "id": alarm["id"],
            "label": alarm["label"],
            "time": alarm["time"],
            "days": mask_to_days(alarm["days_mask"]),
            "days_text": format_days(alarm["days_mask"], alarm["once_date"]),
            "once_date": alarm["once_date"],
            "enabled": bool(alarm["enabled"]),
            "mode": alarm["mode"],
            "difficulty": alarm["difficulty"],
            "snooze_minutes": alarm["snooze_minutes"],
            "max_snoozes": alarm["max_snoozes"],
            "max_ring_minutes": alarm["max_ring_minutes"],
            "next_fire": nf,
            "next_local": iso_local(nf, self._tz),
            "next_human": human_next(nf, self._tz),
            "last_fired_at": alarm.get("last_fired_at"),
            "created_at": alarm.get("created_at"),
            "slug": alarm.get("slug"),
            "completion_mode": alarm.get("completion_mode", "all"),
            "target_count": target,
            "challenge_count": alarm.get("challenge_count", 1),
            "challenge_plan": (
                json.loads(alarm["challenge_plan"])
                if alarm.get("challenge_plan") else None
            ),
            "muted": bool(alarm.get("muted", 0)),
            "question_source": alarm.get("question_source", "auto"),
            "challenge_type": alarm.get("challenge_type", "math"),
            "skip_next": bool(alarm.get("skip_next")),
            "link_expires_at": alarm.get("link_expires_at"),
            "music_id": alarm.get("music_id"),
            "music_name": music_name,
            "calendar_id": alarm.get("calendar_id"),
            "calendar_name": calendar["name"] if calendar else None,
            "participants": [
                {"id": u["id"], "name": u["name"], "active": bool(u["active"])}
                for u in participants
            ],
            "participant_ids": [u["id"] for u in participants],
        }

    def event_view(self, event: dict, *, include_tokens: bool = True) -> dict:
        from .schedule import iso_local

        challenges = self.store.list_challenges(event["id"])
        data = {
            "id": event["id"],
            "alarm_id": event.get("alarm_id"),
            "alarm_label": event["alarm_label"],
            "mode": event["mode"],
            "difficulty": event["difficulty"],
            "state": event["state"],
            "fired_at": event["fired_at"],
            "fired_local": iso_local(event["fired_at"], self._tz),
            "ends_at": event.get("ends_at"),
            "stopped_at": event.get("stopped_at"),
            "stop_reason": event.get("stop_reason"),
            "link_expires_at": (
                (event.get("stopped_at") or event.get("fired_at")) + self.link_retention_minutes * 60
                if event.get("state") not in ("ringing", "snoozed")
                and (event.get("stopped_at") or event.get("fired_at"))
                else None
            ),
            "snooze_until": event.get("snooze_until"),
            "snooze_count": event.get("snooze_count", 0),
            "max_snoozes": event.get("max_snoozes", 0),
            "snooze_minutes": event.get("snooze_minutes", 0),
            "max_ring_minutes": event.get("max_ring_minutes", 0),
            "manual": bool(event.get("manual")),
            "completion_mode": event.get("completion_mode", "all"),
            "target_count": event.get("target_count", 1),
            "challenge_count": event.get("challenge_count", 1),
            "challenge_plan": self._event_plan(event),
            "muted": bool(event.get("muted", 0)),
            "question_source": event.get("question_source", "auto"),
            "challenge_type": event.get("challenge_type", "math"),
            "music_id": event.get("music_id"),
            "music_name": event.get("music_name"),
            "total": len(challenges),
            "answered": sum(1 for c in challenges if c["answered_at"]),
            "snooze_allowed": (
                event["mode"] != "challenge" or len(challenges) <= 1
            ),
            "challenges": [
                {
                    "user_id": c["user_id"],
                    "user_name": c["user_name"],
                    "answered": bool(c["answered_at"]),
                    "answered_at": c["answered_at"],
                    "attempts": c["attempts"],
                    "solved": int(c.get("solved", 0)),
                    "required": event.get("challenge_count", 1),
                    "answer_type": c.get("answer_type", "number"),
                    **({"token": c["token"]} if include_tokens else {}),
                }
                for c in challenges
            ],
        }
        if "answered" in event and "total" in event:
            data["answered"] = event["answered"]
            data["total"] = event["total"]
        return data

    def next_alarm(self) -> dict | None:
        candidates = [
            a for a in self.store.list_alarms() if a["enabled"] and a["next_fire"]
        ]
        if not candidates:
            return None
        alarm = min(candidates, key=lambda a: a["next_fire"])
        return self.alarm_view(alarm)

    def now_iso(self) -> str:
        return now_local(self._tz).isoformat(timespec="seconds")
