"""HTTP API, static assets and the tiny routing layer."""

from __future__ import annotations

import html
import json
import logging
import mimetypes
import os
import re
import threading
import time
import uuid
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import __version__
from .audio import list_audio_devices, parse_device
from .auth import (
    MAX_PASSWORD_LEN,
    MIN_PASSWORD_LEN,
    SESSION_COOKIE,
    SESSION_TTL,
    Auth,
    session_hash,
)
from .db import Store
from .engine import LINK_RETENTION_MAX, Engine, EngineError
from .qrcodegen import QrCode
from .challenge_types import CUSTOM_TYPES, parse_choice_options
from .question_csv import QuestionCsvError, parse_choice_csv
from .schedule import (
    MAX_ALARM_USERS,
    QUESTION_KINDS,
    RESERVED_SLUGS,
    SLUG_RE,
    detect_system_timezone,
    mask_to_days,
    random_slug,
    validate_alarm_payload,
)
from .special_days import CalendarParseError, parse_calendar_csv

log = logging.getLogger("unzzz.http")

MAX_USERS = 200
MAX_BODY = 2 * 1024 * 1024
MAX_MUSIC_BYTES = 25 * 1024 * 1024
MAX_QUESTIONS = 500
MAX_MUSIC_FILES = 200
MAX_CALENDARS = 50
ASSET_DIR = Path(__file__).resolve().parent / "assets"
MUSIC_EXTENSIONS = {".wav", ".wave", ".mp3", ".ogg", ".oga", ".flac", ".m4a", ".aac", ".opus"}
_TOKEN_IN_PATH = re.compile(r"(/s/)[A-Za-z0-9_-]{10,80}")


def redact_path(value: str) -> str:
    """Keep capability tokens out of access logs."""
    return _TOKEN_IN_PATH.sub(r"\1<token>", value)


def make_qr_svg(text: str, border: int = 4) -> str:
    """Render a QR code as a standalone SVG string."""
    qr = QrCode.encode_text(text, QrCode.Ecc.MEDIUM)
    size = qr.get_size()
    dim = size + border * 2
    runs: list[str] = []
    for y in range(size):
        x = 0
        while x < size:
            if not qr.get_module(x, y):
                x += 1
                continue
            start = x
            while x < size and qr.get_module(x, y):
                x += 1
            runs.append(f"M{start + border} {y + border}h{x - start}v1h-{x - start}z")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" '
        f'viewBox="0 0 {dim} {dim}" shape-rendering="crispEdges">'
        f'<rect width="{dim}" height="{dim}" fill="#ffffff"/>'
        f'<path fill="#000000" d="{"".join(runs)}"/></svg>'
    )


_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".webmanifest": "application/manifest+json",
}

_SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; media-src 'self'; connect-src 'self'; "
        "font-src 'self'; base-uri 'none'; form-action 'self'; "
        "frame-ancestors 'none'"
    ),
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


class ApiError(Exception):
    def __init__(self, status: int, message: str, **extra) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.extra = extra


class App:
    def __init__(
        self,
        store: Store,
        engine: Engine,
        auth: Auth,
        data_dir: Path,
    ) -> None:
        self.store = store
        self.engine = engine
        self.auth = auth
        self.data_dir = Path(data_dir)
        self.music_dir = self.data_dir / "music"
        self.music_dir.mkdir(parents=True, exist_ok=True)
        self.started_at = time.time()
        self.setup_lock = threading.Lock()
        self.secure_cookie = os.environ.get("UNZZZ_SECURE_COOKIE") == "1"
        if not store.get_setting("timezone"):
            store.set_setting("timezone", detect_system_timezone())
        self.trust_proxy = False

    # ------------------------------------------------------------------ state
    def external_base(self, handler: "Handler") -> tuple[str, bool]:
        configured = (self.store.get_setting("base_url") or "").strip().rstrip("/")
        if configured:
            return configured, True
        host = handler.headers.get("Host") or "localhost"
        if not re.fullmatch(r"[A-Za-z0-9.\-:\[\]]{1,120}", host):
            host = "localhost"
        scheme = "http"
        if self.trust_proxy:
            proto = (handler.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip()
            if proto in ("http", "https"):
                scheme = proto
        return f"{scheme}://{host}", False

    def decorate_alarm(self, alarm: dict, base: str) -> dict:
        view = self.engine.alarm_view(alarm)
        slug = view.get("slug")
        if slug:
            view["link"] = f"{base}/{slug}"
            view["qr_url"] = f"/qr/{slug}.svg"
        return view

    def question_view(self, row: dict) -> dict:
        try:
            options = json.loads(row.get("options") or "[]")
        except (TypeError, ValueError):
            options = []
        return {
            "id": row["id"],
            "question": row["question"],
            "answer": row["answer"],
            "kind": row.get("kind") or "text",
            "options": options if isinstance(options, list) else [],
            "created_at": row["created_at"],
        }

    def music_view(self, row: dict) -> dict:
        return {
            "id": row["id"],
            "name": row["name"],
            "mime": row["mime"],
            "size": row["size"],
            "created_at": row["created_at"],
            "file_url": f"/api/music/{row['id']}/file",
        }

    def all_link_slug(self) -> str:
        return (self.store.get_setting("all_link_slug") or "").strip()

    def all_link_expires_at(self) -> float | None:
        raw = self.store.get_setting("all_link_expires_at") or ""
        try:
            return float(raw) if str(raw).strip() else None
        except (TypeError, ValueError):
            return None

    def all_link_expired(self) -> bool:
        expires = self.all_link_expires_at()
        return bool(expires and time.time() >= expires)

    def link_items(self, base: str) -> list[dict]:
        items = []
        for alarm in self.store.list_alarms():
            if not alarm.get("enabled") or not alarm.get("slug"):
                continue
            items.append({
                "kind": "alarm",
                "id": alarm["id"],
                "label": alarm["label"],
                "mode": alarm["mode"],
                "slug": alarm["slug"],
                "url": f"{base}/{alarm['slug']}",
                "qr_url": f"/qr/{alarm['slug']}.svg",
                "expires_at": alarm.get("link_expires_at"),
            })
        slug = self.all_link_slug()
        if slug:
            items.append({
                "kind": "all",
                "id": None,
                "label": "All-in-one",
                "mode": "all",
                "slug": slug,
                "url": f"{base}/{slug}",
                "qr_url": f"/qr/{slug}.svg",
                "expires_at": self.all_link_expires_at(),
            })
        return items

    def build_state(self, handler: "Handler", base: str) -> dict:
        alarms = [self.decorate_alarm(a, base) for a in self.store.list_alarms()]
        users = [
            {
                "id": u["id"],
                "name": u["name"],
                "active": bool(u["active"]),
                "created_at": u["created_at"],
            }
            for u in self.store.list_users()
        ]
        active_events = []
        for event in self.store.active_events():
            view = self.engine.event_view(event)
            for ch in view["challenges"]:
                ch["url"] = f"{base}/s/{ch['token']}"
            if event.get("alarm_id"):
                alarm = self.store.get_alarm(event["alarm_id"])
                if alarm and alarm.get("slug"):
                    view["alarm_slug"] = alarm["slug"]
                    view["alarm_link"] = f"{base}/{alarm['slug']}"
                    view["alarm_qr"] = f"/qr/{alarm['slug']}.svg"
            view["snooze_allowed"] = (
                view["mode"] != "challenge" or view["total"] <= 1
            )
            active_events.append(view)
        history = []
        for event in self.store.list_events_with_counts(30):
            history.append(
                {
                    "id": event["id"],
                    "alarm_label": event["alarm_label"],
                    "mode": event["mode"],
                    "state": event["state"],
                    "fired_at": event["fired_at"],
                    "stopped_at": event.get("stopped_at"),
                    "stop_reason": event.get("stop_reason"),
                    "answered": event.get("answered", 0),
                    "total": event.get("total", 0),
                    "completion_mode": event.get("completion_mode", "all"),
                    "target_count": event.get("target_count", 1),
                    "music_name": event.get("music_name"),
                }
            )
        configured_base = (self.store.get_setting("base_url") or "").strip()
        questions = [self.question_view(q) for q in self.store.list_questions()]
        music = [self.music_view(m) for m in self.store.list_music()]
        calendars = self.store.list_calendars()
        return {
            "ok": True,
            "needs_setup": not self.auth.configured,
            "authenticated": True,
            "version": __version__,
            "server_time": time.time(),
            "now_local": self.engine.now_iso(),
            "timezone": self.engine.tz_name,
            "uptime": int(time.time() - self.started_at),
            "alarms": alarms,
            "users": users,
            "active_events": active_events,
            "history": history,
            "questions": questions,
            "music": music,
            "calendars": calendars,
            "next_alarm": self.engine.next_alarm(),
            "audio": self.engine.audio.describe(),
            "volume": self.engine.volume.status(),
            "music_preview": self.engine.music_preview_status(),
            "links": self.link_items(base),
            "settings": {
                "timezone": self.engine.tz_name,
                "base_url": configured_base,
                "effective_base_url": base,
                "audio_device": self.store.get_setting("audio_device") or "",
                "link_retention_minutes": self.engine.link_retention_minutes,
            },
            "limits": {
                "max_users": MAX_USERS,
                "max_alarm_users": MAX_ALARM_USERS,
                "max_music_bytes": MAX_MUSIC_BYTES,
            },
            "system": {
                "version": __version__,
                "data_dir": str(self.data_dir),
            },
        }

    def validate_alarm(self, body: dict, alarm_id: int | None = None) -> tuple[dict | None, str | None]:
        existing = self.store.get_alarm(alarm_id) if alarm_id else None
        if existing:
            data = {
                "label": existing["label"],
                "time": existing["time"],
                "days": mask_to_days(existing["days_mask"]),
                "once_date": existing["once_date"],
                "enabled": bool(existing["enabled"]),
                "mode": existing["mode"],
                "difficulty": existing["difficulty"],
                "snooze_minutes": existing["snooze_minutes"],
                "max_snoozes": existing["max_snoozes"],
                "max_ring_minutes": existing["max_ring_minutes"],
                "participants": [
                    u["id"] for u in self.store.alarm_participants(alarm_id)
                ],
                "completion_mode": existing.get("completion_mode", "all"),
                "target_count": existing.get("target_count", 1),
                "challenge_count": existing.get("challenge_count", 1),
                "challenge_plan": (
                    json.loads(existing["challenge_plan"])
                    if existing.get("challenge_plan") else None
                ),
                "pattern_size": 3,
                "muted": bool(existing.get("muted", 0)),
                "question_source": existing.get("question_source", "auto"),
                "challenge_type": existing.get("challenge_type", "math"),
                "music_id": existing.get("music_id"),
                "calendar_id": existing.get("calendar_id"),
                "slug": existing.get("slug"),
            }
            data.update(body)
        else:
            data = dict(body)

        mode = str(data.get("mode", "standard"))
        calendar_map: dict[str, str] = {}
        raw_calendar = data.get("calendar_id")
        if raw_calendar in (None, "", 0, "0"):
            data["calendar_id"] = None
        else:
            try:
                calendar_id = int(raw_calendar)
            except (TypeError, ValueError):
                return None, "calendar_id must be a number"
            if not self.store.get_calendar(calendar_id):
                return None, "Special-days calendar not found"
            data["calendar_id"] = calendar_id
            calendar_map = self.store.calendar_day_map(calendar_id)

        raw_music = data.get("music_id")
        if raw_music in (None, "", 0, "0"):
            data["music_id"] = None
        else:
            try:
                music_id = int(raw_music)
            except (TypeError, ValueError):
                return None, "music_id must be a number"
            if not self.store.get_music(music_id):
                return None, "Music file not found"
            data["music_id"] = music_id

        raw_slug = str(data.get("slug") or "").strip().lower()
        if raw_slug:
            data["slug"] = raw_slug
        else:
            for _ in range(40):
                candidate = random_slug()
                retired = self.store.get_retired_link(candidate)
                if (
                    not self.store.slug_taken(candidate, alarm_id)
                    and candidate != self.all_link_slug()
                    and not (retired and float(retired["expires_at"]) > time.time())
                ):
                    data["slug"] = candidate
                    break

        clean, error = validate_alarm_payload(
            data,
            tz=self.engine.tz,
            users=self.store.list_users(),
            question_counts={
                kind: self.store.count_questions(kind) for kind in QUESTION_KINDS
            },
            calendar=calendar_map,
        )
        if error:
            return None, error
        if clean["slug"] and self.store.slug_taken(clean["slug"], alarm_id):
            return None, "That shortlink is already in use"
        if clean["slug"] and clean["slug"] == self.all_link_slug():
            return None, "That shortlink is already in use"
        if clean["slug"]:
            retired = self.store.get_retired_link(clean["slug"])
            if retired and float(retired["expires_at"]) > time.time():
                return None, "That shortlink is already in use"
        return clean, None

    # ------------------------------------------------------------------ mount
    def make_server(self, bind: str, port: int) -> "Server":
        app = self

        class _Handler(Handler):
            application = app

        server = Server((bind, port), _Handler)
        server.app = self
        return server


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 32

    def __init__(self, address, handler) -> None:
        super().__init__(address, handler)
        self.app: App | None = None

    def handle_error(self, request, client_address) -> None:
        log.exception("unhandled error while serving %s", client_address)


class Handler(BaseHTTPRequestHandler):
    application: App
    protocol_version = "HTTP/1.1"
    server_version = f"unzzz/{__version__}"
    sys_version = ""
    timeout = 20

    ROUTES = [
        ("GET", re.compile(r"^/$"), "static_index"),
        ("GET", re.compile(r"^/app\.js$"), "static_appjs"),
        ("GET", re.compile(r"^/i18n\.js$"), "static_i18njs"),
        ("GET", re.compile(r"^/style\.css$"), "static_css"),
        ("GET", re.compile(r"^/challenge\.js$"), "static_challengejs"),
        ("GET", re.compile(r"^/alarm\.js$"), "static_alarmjs"),
        ("GET", re.compile(r"^/favicon\.svg$"), "static_favicon"),
        ("GET", re.compile(r"^/s/[A-Za-z0-9_-]{10,80}$"), "challenge_page"),
        ("GET", re.compile(r"^/healthz$"), "healthz"),
        ("GET", re.compile(r"^/qr/(?P<slug>[A-Za-z0-9][A-Za-z0-9_-]{2,39})\.svg$"), "qr_svg"),
        ("GET", re.compile(r"^/api/alarm/(?P<slug>[A-Za-z0-9][A-Za-z0-9_-]{2,39})$"), "public_alarm_state"),
        ("POST", re.compile(r"^/api/alarm/(?P<slug>[A-Za-z0-9][A-Za-z0-9_-]{2,39})/claim$"), "public_claim"),
        ("POST", re.compile(r"^/api/alarm/(?P<slug>[A-Za-z0-9][A-Za-z0-9_-]{2,39})/stop$"), "public_stop"),
        ("POST", re.compile(r"^/api/alarm/(?P<slug>[A-Za-z0-9][A-Za-z0-9_-]{2,39})/snooze$"), "public_snooze"),
        ("PUT", re.compile(r"^/api/links/alarm/(?P<id>\d+)$"), "link_alarm_update"),
        ("POST", re.compile(r"^/api/links/all$"), "link_all_create"),
        ("PUT", re.compile(r"^/api/links/all$"), "link_all_update"),
        ("DELETE", re.compile(r"^/api/links/all$"), "link_all_delete"),
        ("GET", re.compile(r"^/api/state$"), "state"),
        ("POST", re.compile(r"^/api/setup$"), "api_setup"),
        ("POST", re.compile(r"^/api/login$"), "login"),
        ("POST", re.compile(r"^/api/logout$"), "logout"),
        ("POST", re.compile(r"^/api/password$"), "password"),
        ("POST", re.compile(r"^/api/settings$"), "settings"),
        ("GET", re.compile(r"^/api/audio/devices$"), "audio_devices"),
        ("POST", re.compile(r"^/api/audio/test$"), "audio_test"),
        ("GET", re.compile(r"^/api/questions$"), "questions_list"),
        ("POST", re.compile(r"^/api/questions$"), "question_create"),
        ("POST", re.compile(r"^/api/questions/import$"), "question_import"),
        ("PUT", re.compile(r"^/api/questions/(?P<id>\d+)$"), "question_update"),
        ("DELETE", re.compile(r"^/api/questions/(?P<id>\d+)$"), "question_delete"),
        ("GET", re.compile(r"^/api/music$"), "music_list"),
        ("POST", re.compile(r"^/api/music$"), "music_upload"),
        ("POST", re.compile(r"^/api/music/(?P<id>\d+)/test$"), "music_preview"),
        ("POST", re.compile(r"^/api/music/(?P<id>\d+)/stop$"), "music_preview_stop"),
        ("DELETE", re.compile(r"^/api/music/(?P<id>\d+)$"), "music_delete"),
        ("GET", re.compile(r"^/api/music/(?P<id>\d+)/file$"), "music_file"),
        ("GET", re.compile(r"^/api/calendars$"), "calendars_list"),
        ("POST", re.compile(r"^/api/calendars$"), "calendar_import"),
        ("DELETE", re.compile(r"^/api/calendars/(?P<id>\d+)$"), "calendar_delete"),
        ("POST", re.compile(r"^/api/alarms$"), "alarm_create"),
        ("PUT", re.compile(r"^/api/alarms/(?P<id>\d+)$"), "alarm_update"),
        ("DELETE", re.compile(r"^/api/alarms/(?P<id>\d+)$"), "alarm_delete"),
        ("POST", re.compile(r"^/api/alarms/(?P<id>\d+)/toggle$"), "alarm_toggle"),
        ("POST", re.compile(r"^/api/alarms/(?P<id>\d+)/skip$"), "alarm_skip"),
        ("POST", re.compile(r"^/api/alarms/(?P<id>\d+)/ring$"), "alarm_ring"),
        ("POST", re.compile(r"^/api/users$"), "user_create"),
        ("PUT", re.compile(r"^/api/users/(?P<id>\d+)$"), "user_update"),
        ("DELETE", re.compile(r"^/api/users/(?P<id>\d+)$"), "user_delete"),
        ("POST", re.compile(r"^/api/events/(?P<id>\d+)/stop$"), "event_stop"),
        ("POST", re.compile(r"^/api/events/(?P<id>\d+)/snooze$"), "event_snooze"),
        ("GET", re.compile(r"^/api/s/(?P<token>[A-Za-z0-9_-]{10,80})$"), "challenge_state"),
        ("POST", re.compile(r"^/api/s/(?P<token>[A-Za-z0-9_-]{10,80})/answer$"), "challenge_answer"),
        ("GET", re.compile(r"^/(?P<slug>[A-Za-z0-9][A-Za-z0-9_-]{2,39})$"), "alarm_page"),
    ]

    # ------------------------------------------------------------- plumbing
    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

    def do_PUT(self) -> None:  # noqa: N802
        self._dispatch("PUT")

    def do_DELETE(self) -> None:  # noqa: N802
        self._dispatch("DELETE")

    def do_HEAD(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def _dispatch(self, method: str) -> None:
        parsed = urlsplit(self.path)
        path = parsed.path
        match = None
        name = None
        for route_method, pattern, route_name in self.ROUTES:
            if route_method != method:
                continue
            m = pattern.match(path)
            if m:
                match, name = m, route_name
                break
        if match is None or name is None:
            self._send_json({"ok": False, "error": "Not found"}, 404)
            return
        try:
            body: dict = {}
            if method in ("POST", "PUT", "DELETE") and name != "music_upload":
                body = self._read_json() if method != "DELETE" else self._read_json(optional=True)
            getattr(self, name)(match, body)
        except ApiError as exc:
            headers = {}
            if exc.status == 429 and "retry_after" in exc.extra:
                headers["Retry-After"] = str(exc.extra.pop("retry_after"))
            payload = {"ok": False, "error": exc.message, **exc.extra}
            self._send_json(payload, exc.status, headers=headers)
        except EngineError as exc:
            self._send_json({"ok": False, "error": exc.message}, exc.status)
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception:
            log.exception("request failed: %s %s", method, redact_path(path))
            self._send_json({"ok": False, "error": "Internal server error"}, 500)

    def _read_json(self, optional: bool = False) -> dict:
        length_raw = self.headers.get("Content-Length") or "0"
        try:
            length = int(length_raw)
        except ValueError:
            raise ApiError(400, "Invalid Content-Length")
        if length <= 0:
            if optional:
                return {}
            raise ApiError(400, "Request body required")
        if length > MAX_BODY:
            raise ApiError(413, "Request body too large")
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            raise ApiError(415, "Expected application/json")
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ApiError(400, "Invalid JSON")
        if not isinstance(data, dict):
            raise ApiError(400, "Expected a JSON object")
        return data

    def _receive_file(self, destination: Path, limit: int) -> int:
        length_raw = self.headers.get("Content-Length") or "0"
        try:
            length = int(length_raw)
        except ValueError:
            raise ApiError(400, "Invalid Content-Length")
        if length <= 0:
            raise ApiError(400, "Empty upload")
        if length > limit:
            raise ApiError(413, f"File is too large (maximum {limit // (1024 * 1024)} MB)")
        destination.parent.mkdir(parents=True, exist_ok=True)
        received = 0
        try:
            with destination.open("wb") as fh:
                while received < length:
                    chunk = self.rfile.read(min(64 * 1024, length - received))
                    if not chunk:
                        raise ApiError(400, "Upload ended early")
                    fh.write(chunk)
                    received += len(chunk)
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
        return received

    def _send(self, status: int, body: bytes, ctype: str, *, cache: str = "no-store", headers=None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        for key, value in _SECURITY_HEADERS.items():
            self.send_header(key, value)
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _send_json(self, data: dict, status: int = 200, headers=None) -> None:
        body = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8", headers=headers)

    def _send_page(self, filename: str) -> None:
        path = ASSET_DIR / filename
        try:
            body = path.read_bytes()
        except OSError:
            self._send_json({"ok": False, "error": "Asset missing"}, 500)
            return
        ctype = _CONTENT_TYPES.get(path.suffix, "application/octet-stream")
        self._send(200, body, ctype, cache="no-cache")

    def _send_file(self, path: Path, ctype: str) -> None:
        try:
            size = path.stat().st_size
            fh = path.open("rb")
        except OSError:
            self._send_json({"ok": False, "error": "File missing"}, 404)
            return
        start, end = 0, size - 1
        status = 200
        range_header = self.headers.get("Range") or ""
        if range_header.startswith("bytes=") and size > 0:
            spec = range_header[6:].split(",")[0].strip()
            try:
                if spec.startswith("-"):
                    suffix = int(spec[1:])
                    start = max(0, size - suffix)
                else:
                    left, _, right = spec.partition("-")
                    start = int(left)
                    if right:
                        end = min(size - 1, int(right))
                if start > end or start >= size:
                    raise ValueError
                status = 206
            except ValueError:
                self._send_json(
                    {"ok": False, "error": "Invalid range"},
                    416,
                    headers={"Content-Range": f"bytes */{size}"},
                )
                fh.close()
                return
        length = end - start + 1
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "private, max-age=0")
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        for key, value in _SECURITY_HEADERS.items():
            self.send_header(key, value)
        self.end_headers()
        if self.command == "HEAD":
            fh.close()
            return
        try:
            fh.seek(start)
            remaining = length
            while remaining > 0:
                chunk = fh.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            fh.close()

    # ---------------------------------------------------------------- helpers
    @property
    def app(self) -> App:
        return self.application

    def client_ip(self) -> str:
        if self.app.trust_proxy:
            forwarded = (self.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
            if forwarded:
                return forwarded
        return self.client_address[0]

    def _cookie(self) -> str | None:
        raw = self.headers.get("Cookie")
        if not raw:
            return None
        try:
            jar = SimpleCookie(raw)
        except Exception:
            return None
        morsel = jar.get(SESSION_COOKIE)
        return morsel.value if morsel else None

    def _session_ok(self) -> bool:
        return self.app.auth.session_valid(self._cookie())

    def _require_login(self) -> None:
        if not self._session_ok():
            raise ApiError(401, "Please sign in")

    def _require_admin(self) -> None:
        self._require_login()
        self._require_csrf()

    def _require_csrf(self) -> None:
        if self.headers.get("X-Unzzz-Csrf") != "1":
            raise ApiError(403, "Missing CSRF header")
        self._check_origin()

    def _check_origin(self) -> None:
        origin = self.headers.get("Origin")
        if not origin:
            return
        host = self.headers.get("Host")
        try:
            parsed = urlsplit(origin)
        except ValueError:
            raise ApiError(403, "Bad origin")
        if parsed.netloc != host:
            raise ApiError(403, "Cross-origin request blocked")

    def _session_cookie(self, value: str, max_age: int) -> str:
        secure = (
            self.app.secure_cookie
            or (self.headers.get("X-Forwarded-Proto") or "") == "https"
        )
        parts = [
            f"{SESSION_COOKIE}={value}",
            "Path=/",
            "HttpOnly",
            "SameSite=Lax",
            f"Max-Age={max_age}",
        ]
        if secure:
            parts.append("Secure")
        return "; ".join(parts)

    def _base(self) -> str:
        base, _ = self.app.external_base(self)
        return base

    def _int_id(self, match) -> int:
        try:
            return int(match.group("id"))
        except (ValueError, IndexError):
            raise ApiError(400, "Invalid id")

    def _url_query(self) -> dict[str, list[str]]:
        return parse_qs(urlsplit(self.path).query)

    # ---------------------------------------------------------------- pages
    def static_index(self, match, body) -> None:
        self._send_page("index.html")

    def static_appjs(self, match, body) -> None:
        self._send_page("app.js")

    def static_i18njs(self, match, body) -> None:
        self._send_page("i18n.js")

    def static_css(self, match, body) -> None:
        self._send_page("style.css")

    def static_challengejs(self, match, body) -> None:
        self._send_page("challenge.js")

    def static_alarmjs(self, match, body) -> None:
        self._send_page("alarm.js")

    def static_favicon(self, match, body) -> None:
        self._send_page("favicon.svg")

    def challenge_page(self, match, body) -> None:
        self._send_page("challenge.html")

    def alarm_page(self, match, body) -> None:
        slug = match.group("slug")
        if not self.app.store.get_alarm_by_slug(slug):
            retired = self.app.store.get_retired_link(slug)
            if retired:
                if time.time() >= float(retired["expires_at"]):
                    self._send(410, b"<h1>This link has expired</h1>", "text/html; charset=utf-8")
                    return
                when = time.strftime(
                    "%Y-%m-%d %H:%M", time.localtime(float(retired["expires_at"]))
                )
                body = (
                    "<!doctype html><meta charset=utf-8><title>Alarm removed · unzzz</title>"
                    "<body style=\"font-family:system-ui,sans-serif;max-width:36rem;margin:3rem auto;padding:0 1rem\">"
                    f"<h1>{html.escape(retired['label'])} was removed</h1>"
                    f"<p>This shortlink expires at {html.escape(when)}.</p>"
                    "</body>"
                ).encode("utf-8")
                self._send(200, body, "text/html; charset=utf-8", cache="no-cache")
                return
        if not self.app.store.get_alarm_by_slug(slug) and slug == self.app.all_link_slug():
            if self.app.all_link_expired():
                self._send(410, b"<h1>This link has expired</h1>", "text/html; charset=utf-8")
                return
            target = self._all_link_target()
            if not target:
                self._send(404, b"<h1>No alarm link is available</h1>", "text/html; charset=utf-8")
                return
            self._send(302, b"", "text/plain; charset=utf-8", headers={"Location": f"/{target}"})
            return
        self._send_page("alarm.html")

    def healthz(self, match, body) -> None:
        self._send_json({"ok": True, "version": __version__, "time": time.time()})

    def log_message(self, fmt: str, *args) -> None:
        message = "%s - %s" % (self.address_string(), redact_path(fmt % args))
        if self.path.startswith(("/api/state", "/healthz", "/api/s/", "/api/alarm/")):
            log.debug(message)
        else:
            log.info(message)

    # ---------------------------------------------------------------- public
    def _client_ip(self) -> str:
        return str(self.client_address[0])

    def _ip_pass_payload(self, event_id: int) -> dict | None:
        row = self.app.store.get_ip_pass(event_id, self._client_ip())
        if not row:
            return None
        challenges = self.app.store.list_challenges(event_id)
        remaining = [
            c["user_name"] for c in challenges
            if not c["answered_at"]
        ]
        return {
            "user_name": row["user_name"],
            "passed_at": row["passed_at"],
            "remaining": len(remaining),
            "remaining_users": remaining,
        }

    def _public_alarm(self, slug: str) -> dict:
        alarm = self.app.store.get_alarm_by_slug(slug)
        if not alarm:
            raise ApiError(404, "This alarm link was not found")
        if self.app.engine.alarm_link_expired(alarm):
            raise ApiError(410, "This alarm link has expired")
        return alarm

    def public_alarm_state(self, match, body) -> None:
        slug = match.group("slug")
        try:
            alarm = self._public_alarm(slug)
        except ApiError as exc:
            self._send_json({"ok": False, "error": exc.message}, exc.status)
            return
        active = self.app.store.active_event_for_alarm(alarm["id"])
        latest = self.app.store.latest_event_for_alarm(alarm["id"])
        participants = self.app.store.alarm_participants(alarm["id"])
        event_view = None
        if active:
            event_view = self.app.engine.event_view(active, include_tokens=False)
        latest_view = None
        if latest and not active and not self.app.engine.link_expired(latest):
            latest_view = self.app.engine.event_view(latest, include_tokens=False)
        ip_passed = (
            self._ip_pass_payload(active["id"]) if active
            else (self._ip_pass_payload(latest["id"]) if latest_view else None)
        )
        self._send_json(
            {
                "ok": True,
                "slug": alarm["slug"],
                "link": f"{self._base()}/{alarm['slug']}",
                "server_time": time.time(),
                "timezone": self.app.engine.tz_name,
                "alarm": {
                    "id": alarm["id"],
                    "label": alarm["label"],
                    "time": alarm["time"],
                    "days_text": self.app.engine.alarm_view(alarm)["days_text"],
                    "next_fire": alarm.get("next_fire"),
                    "next_human": self.app.engine.alarm_view(alarm)["next_human"],
                    "enabled": bool(alarm["enabled"]),
                    "mode": alarm["mode"],
                },
                "participants": [
                    {"id": u["id"], "name": u["name"], "active": bool(u["active"])}
                    for u in participants
                ],
                "event": event_view,
                "last_event": latest_view,
                "ip_passed": ip_passed,
                "state": active["state"] if active else "idle",
            }
        )

    def public_claim(self, match, body) -> None:
        self._check_origin()
        alarm = self._public_alarm(match.group("slug"))
        event = self.app.store.active_event_for_alarm(alarm["id"])
        if not event:
            raise ApiError(409, "This alarm is not ringing right now")
        if event["state"] != "ringing":
            raise ApiError(409, "This alarm is snoozed; try again when it rings")
        try:
            user_id = int(body.get("user_id"))
        except (TypeError, ValueError):
            raise ApiError(400, "Choose who you are")
        ip_pass = self.app.store.get_ip_pass(event["id"], self._client_ip())
        if ip_pass:
            remaining = sum(
                1 for c in self.app.store.list_challenges(event["id"])
                if not c["answered_at"]
            )
            raise ApiError(
                409,
                f"{ip_pass['user_name']}, you have already passed this challenge. "
                f"{remaining} other person(s) still need to answer.",
            )
        challenge = self.app.store.get_challenge_for_user(event["id"], user_id)
        if not challenge:
            raise ApiError(404, "That person is not part of this alarm")
        if challenge["answered_at"]:
            raise ApiError(409, "This question has already been answered")
        self._send_json(
            {"ok": True, "url": f"/s/{challenge['token']}", "user_name": challenge["user_name"]}
        )

    def public_stop(self, match, body) -> None:
        self._check_origin()
        alarm = self._public_alarm(match.group("slug"))
        event = self.app.store.active_event_for_alarm(alarm["id"])
        if not event:
            raise ApiError(409, "This alarm is not ringing right now")
        if event["mode"] != "standard":
            raise ApiError(409, "Challenge alarms must be answered")
        updated = self.app.engine.stop_event(event["id"], "stopped from shortlink")
        self._send_json({"ok": True, "event": self.app.engine.event_view(updated)})

    def public_snooze(self, match, body) -> None:
        self._check_origin()
        alarm = self._public_alarm(match.group("slug"))
        event = self.app.store.active_event_for_alarm(alarm["id"])
        if not event:
            raise ApiError(409, "This alarm is not ringing right now")
        if event["mode"] != "standard":
            raise ApiError(409, "Challenge alarms must be answered")
        updated = self.app.engine.snooze_event(event["id"])
        self._send_json({"ok": True, "event": self.app.engine.event_view(updated)})

    # --------------------------------------------------------------- links
    def _link_slug(self, raw: object, *, ignore_alarm: int | None = None) -> str:
        slug = str(raw or "").strip().lower()
        if not SLUG_RE.match(slug):
            raise ApiError(400, "Shortlink must be 3-40 characters: a-z, 0-9, - or _")
        if slug in RESERVED_SLUGS:
            raise ApiError(400, "That shortlink is reserved")
        if self.app.store.slug_taken(slug, ignore_alarm):
            raise ApiError(409, "That shortlink is already in use")
        retired = self.app.store.get_retired_link(slug)
        if retired and float(retired["expires_at"]) > time.time():
            raise ApiError(409, "That shortlink is already in use")
        if slug == self.app.all_link_slug() and ignore_alarm is not None:
            raise ApiError(409, "That shortlink is already in use")
        return slug

    def _link_expiry(self, raw: object) -> float | None:
        if raw in (None, ""):
            return None
        try:
            value = float(raw)
        except (TypeError, ValueError):
            raise ApiError(400, "Expiration must be a timestamp or empty")
        if value < 0:
            raise ApiError(400, "Expiration must be a timestamp or empty")
        return value

    def _find_link(self, base: str, kind: str, alarm_id: int | None = None) -> dict | None:
        for item in self.app.link_items(base):
            if item["kind"] == kind and (alarm_id is None or item["id"] == alarm_id):
                return item
        return None

    def link_alarm_update(self, match, body) -> None:
        self._require_admin()
        alarm_id = self._int_id(match)
        alarm = self.app.store.get_alarm(alarm_id)
        if not alarm:
            raise ApiError(404, "Alarm not found")
        slug = self._link_slug(body.get("slug"), ignore_alarm=alarm_id)
        expires = self._link_expiry(body.get("expires_at"))
        self.app.store.set_alarm_link(alarm_id, slug, expires)
        updated = self.app.store.get_alarm(alarm_id)
        self._send_json({"ok": True, "link": self._find_link(self._base(), "alarm", alarm_id),
                         "alarm": self.app.engine.alarm_view(updated)})

    def link_all_create(self, match, body) -> None:
        self._require_admin()
        if self.app.all_link_slug():
            raise ApiError(409, "An all-in-one link already exists")
        raw = str(body.get("slug") or "all").strip().lower()
        try:
            slug = self._link_slug(raw)
        except ApiError:
            slug = random_slug()
            while True:
                retired = self.app.store.get_retired_link(slug)
                if (
                    not self.app.store.slug_taken(slug)
                    and slug != self.app.all_link_slug()
                    and not (retired and float(retired["expires_at"]) > time.time())
                ):
                    break
                slug = random_slug()
        expires = self._link_expiry(body.get("expires_at"))
        self.app.store.set_setting("all_link_slug", slug)
        self.app.store.set_setting("all_link_expires_at", "" if expires is None else str(expires))
        self._send_json({"ok": True, "link": self._find_link(self._base(), "all")}, 201)

    def link_all_update(self, match, body) -> None:
        self._require_admin()
        if not self.app.all_link_slug():
            raise ApiError(404, "All-in-one link not found")
        slug = self._link_slug(body.get("slug"))
        expires = self._link_expiry(body.get("expires_at"))
        self.app.store.set_setting("all_link_slug", slug)
        self.app.store.set_setting("all_link_expires_at", "" if expires is None else str(expires))
        self._send_json({"ok": True, "link": self._find_link(self._base(), "all")})

    def link_all_delete(self, match, body) -> None:
        self._require_admin()
        self.app.store.set_setting("all_link_slug", "")
        self.app.store.set_setting("all_link_expires_at", "")
        self._send_json({"ok": True})

    def _all_link_target(self) -> str | None:
        for event in self.app.store.active_events():
            alarm_id = event.get("alarm_id")
            if not alarm_id:
                continue
            alarm = self.app.store.get_alarm(int(alarm_id))
            if (
                alarm and alarm.get("slug")
                and alarm.get("mode") == "challenge"
                and not self.app.engine.alarm_link_expired(alarm)
            ):
                return alarm["slug"]
        for event in self.app.store.list_events(50):
            alarm_id = event.get("alarm_id")
            if not alarm_id:
                continue
            alarm = self.app.store.get_alarm(int(alarm_id))
            if (
                alarm and alarm.get("slug")
                and alarm.get("mode") == "challenge"
                and not self.app.engine.alarm_link_expired(alarm)
            ):
                return alarm["slug"]
        for alarm in self.app.store.list_alarms():
            if (
                alarm.get("enabled") and alarm.get("mode") == "challenge"
                and alarm.get("slug") and not self.app.engine.alarm_link_expired(alarm)
            ):
                return alarm["slug"]
        return None

    def qr_svg(self, match, body) -> None:
        slug = match.group("slug")
        alarm = self.app.store.get_alarm_by_slug(slug)
        if alarm:
            if self.app.engine.alarm_link_expired(alarm):
                raise ApiError(410, "This alarm link has expired")
            url = f"{self._base()}/{alarm['slug']}"
        else:
            retired = self.app.store.get_retired_link(slug)
            if retired:
                if time.time() >= float(retired["expires_at"]):
                    raise ApiError(410, "This alarm link has expired")
                url = f"{self._base()}/{slug}"
            elif slug == self.app.all_link_slug():
                if self.app.all_link_expired():
                    raise ApiError(410, "This link has expired")
                url = f"{self._base()}/{slug}"
            else:
                raise ApiError(404, "This alarm link was not found")
        try:
            svg = make_qr_svg(url)
        except Exception:
            log.exception("QR generation failed")
            raise ApiError(500, "Could not generate QR code")
        self._send(200, svg.encode("utf-8"), "image/svg+xml", cache="no-store")

    # ----------------------------------------------------------------- auth
    def state(self, match, body) -> None:
        if not self.app.auth.configured:
            self._send_json(
                {
                    "ok": True,
                    "needs_setup": True,
                    "authenticated": False,
                    "version": __version__,
                    "limits": {
                        "max_users": MAX_USERS,
                        "max_alarm_users": MAX_ALARM_USERS,
                    },
                }
            )
            return
        if not self._session_ok():
            self._send_json(
                {
                    "ok": False,
                    "needs_setup": False,
                    "authenticated": False,
                    "error": "Please sign in",
                },
                401,
            )
            return
        base = self._base()
        self._send_json(self.app.build_state(self, base))

    def api_setup(self, match, body) -> None:
        self._check_origin()
        password = str(body.get("password") or "")
        if not (MIN_PASSWORD_LEN <= len(password) <= MAX_PASSWORD_LEN):
            raise ApiError(400, f"Password must be {MIN_PASSWORD_LEN}-{MAX_PASSWORD_LEN} characters")
        with self.app.setup_lock:
            if self.app.auth.configured:
                raise ApiError(409, "Admin password is already set")
            self.app.auth.set_password(password)
            token = self.app.auth.new_session(self.headers.get("User-Agent", ""))
        self._send_json(
            {"ok": True},
            headers={"Set-Cookie": self._session_cookie(token, SESSION_TTL)},
        )
        log.info("admin password configured from %s", self.client_ip())

    def login(self, match, body) -> None:
        self._check_origin()
        if not self.app.auth.configured:
            raise ApiError(409, "Set up an admin password first")
        ip = self.client_ip()
        wait = self.app.auth.locked_for(ip)
        if wait:
            raise ApiError(429, f"Too many attempts. Try again in {wait}s.", retry_after=wait)
        password = str(body.get("password") or "")
        if not password or not self.app.auth.check_password(password):
            locked = self.app.auth.note_failure(ip)
            if locked:
                raise ApiError(429, f"Too many attempts. Try again in {locked}s.", retry_after=locked)
            raise ApiError(401, "Wrong password")
        self.app.auth.note_success(ip)
        token = self.app.auth.new_session(self.headers.get("User-Agent", ""))
        self._send_json(
            {"ok": True},
            headers={"Set-Cookie": self._session_cookie(token, SESSION_TTL)},
        )
        log.info("admin signed in from %s", ip)

    def logout(self, match, body) -> None:
        self._check_origin()
        self.app.auth.destroy_session(self._cookie())
        self._send_json(
            {"ok": True},
            headers={"Set-Cookie": self._session_cookie("", 0)},
        )

    def password(self, match, body) -> None:
        self._require_admin()
        current = str(body.get("current") or "")
        new = str(body.get("new") or "")
        if not self.app.auth.check_password(current):
            raise ApiError(403, "Current password is wrong")
        if not (MIN_PASSWORD_LEN <= len(new) <= MAX_PASSWORD_LEN):
            raise ApiError(400, f"New password must be {MIN_PASSWORD_LEN}-{MAX_PASSWORD_LEN} characters")
        token = self._cookie()
        self.app.auth.set_password(
            new, keep_hash=session_hash(token) if token else None
        )
        self._send_json({"ok": True})

    # -------------------------------------------------------------- settings
    def settings(self, match, body) -> None:
        self._require_admin()
        tz_name = str(body.get("timezone") or "").strip()
        base_url = str(body.get("base_url") or "").strip().rstrip("/")
        audio_device = str(body.get("audio_device") or "").strip()
        target_volume = None
        if "target_volume" in body:
            try:
                target_volume = int(body.get("target_volume"))
            except (TypeError, ValueError):
                raise ApiError(400, "Target volume must be 0-100")
            if not (0 <= target_volume <= 100):
                raise ApiError(400, "Target volume must be 0-100")
        retention = None
        if "link_retention_minutes" in body:
            try:
                retention = int(body.get("link_retention_minutes"))
            except (TypeError, ValueError):
                raise ApiError(400, "Link retention must be a number of minutes")
            if not (0 <= retention <= LINK_RETENTION_MAX):
                raise ApiError(400, f"Link retention must be 0-{LINK_RETENTION_MAX} minutes")
        try:
            ZoneInfo(tz_name)
        except (ZoneInfoNotFoundError, ValueError):
            raise ApiError(400, "Unknown timezone")
        if base_url:
            parsed = urlsplit(base_url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
                raise ApiError(400, "Base URL must look like http://host:port")
        if audio_device and parse_device(audio_device) is None:
            raise ApiError(400, "Audio device must be empty or start with alsa:/pulse:")
        self.app.store.set_setting("base_url", base_url)
        self.app.engine.set_timezone(tz_name)
        if "audio_device" in body:
            self.app.engine.set_audio_device(audio_device)
        if retention is not None:
            self.app.engine.set_link_retention(retention)
        if target_volume is not None:
            self.app.engine.set_target_volume(target_volume)
        self._send_json({"ok": True})

    def audio_devices(self, match, body) -> None:
        self._require_login()
        devices = list_audio_devices()
        current = self.app.store.get_setting("audio_device") or ""
        if current and not any(d["value"] == current for d in devices):
            devices.append({"value": current, "label": f"Custom · {current}"})
        self._send_json(
            {
                "ok": True,
                "devices": devices,
                "current": current,
                "audio": self.app.engine.audio.describe(),
            }
        )

    def audio_test(self, match, body) -> None:
        self._require_admin()
        ok, error = self.app.engine.audio.test()
        if not ok:
            self._send_json(
                {"ok": False, "error": error or "No sound", "audio": self.app.engine.audio.describe()},
                400,
            )
            return
        self._send_json({"ok": True, "audio": self.app.engine.audio.describe()})

    # -------------------------------------------------------------- questions
    def _question_payload(self, body: dict) -> tuple[str, str, str, str | None]:
        kind = str(body.get("kind") or "text").strip().lower()
        if kind not in QUESTION_KINDS:
            raise ApiError(400, "Question kind must be text or choice")
        question = str(body.get("question") or "").strip()
        answer = str(body.get("answer") or "").strip()
        if not (1 <= len(question) <= 300):
            raise ApiError(400, "Question must be 1-300 characters")
        if not (1 <= len(answer) <= 200):
            raise ApiError(400, "Answer must be 1-200 characters")
        if any(ord(c) < 32 and c not in "\n\t" for c in question + answer):
            raise ApiError(400, "Question/answer contains control characters")
        options: list[str] = []
        if kind == "choice":
            options, option_error = parse_choice_options(body.get("options"))
            if option_error:
                raise ApiError(400, option_error)
            if answer not in options:
                raise ApiError(400, "Correct answer must exactly match one option")
            options_json = json.dumps(options, ensure_ascii=False)
        else:
            options_json = None
        return question, answer, kind, options_json

    def questions_list(self, match, body) -> None:
        self._require_login()
        self._send_json(
            {
                "ok": True,
                "questions": [
                    self.app.question_view(q) for q in self.app.store.list_questions()
                ],
            }
        )

    def question_create(self, match, body) -> None:
        self._require_admin()
        if self.app.store.count_questions() >= MAX_QUESTIONS:
            raise ApiError(400, f"Maximum of {MAX_QUESTIONS} questions")
        question, answer, kind, options = self._question_payload(body)
        item = self.app.store.add_question(question, answer, kind, options)
        self._send_json({"ok": True, "question": self.app.question_view(item)}, 201)

    def question_import(self, match, body) -> None:
        self._require_admin()
        csv_text = body.get("csv")
        if not isinstance(csv_text, str) or not csv_text.strip():
            raise ApiError(400, "CSV data is required")
        try:
            parsed = parse_choice_csv(csv_text)
        except QuestionCsvError as exc:
            raise ApiError(400, str(exc))
        if self.app.store.count_questions() + len(parsed) > MAX_QUESTIONS:
            raise ApiError(
                400,
                f"Import would exceed the maximum of {MAX_QUESTIONS} questions",
            )
        imported = []
        for item in parsed:
            row = self.app.store.add_question(
                item["question"],
                item["answer"],
                "choice",
                json.dumps(item["options"], ensure_ascii=False),
            )
            imported.append(self.app.question_view(row))
        self._send_json(
            {"ok": True, "imported": len(imported), "questions": imported}, 201
        )

    def question_update(self, match, body) -> None:
        self._require_admin()
        question_id = self._int_id(match)
        if not self.app.store.get_question(question_id):
            raise ApiError(404, "Question not found")
        question, answer, kind, options = self._question_payload(body)
        item = self.app.store.update_question(
            question_id, question, answer, kind, options
        )
        self._send_json({"ok": True, "question": self.app.question_view(item)})

    def question_delete(self, match, body) -> None:
        self._require_admin()
        question_id = self._int_id(match)
        if not self.app.store.delete_question(question_id):
            raise ApiError(404, "Question not found")
        self._send_json({"ok": True})

    # ----------------------------------------------------------------- music
    def music_list(self, match, body) -> None:
        self._require_login()
        self._send_json(
            {"ok": True, "music": [self.app.music_view(m) for m in self.app.store.list_music()]}
        )

    def music_upload(self, match, body) -> None:
        self._require_admin()
        if len(self.app.store.list_music()) >= MAX_MUSIC_FILES:
            raise ApiError(400, f"Maximum of {MAX_MUSIC_FILES} music files")
        query = self._url_query()
        raw_name = (query.get("name") or ["upload.wav"])[0]
        display_q = " ".join((query.get("display") or [""])[0].split())
        filename = Path(str(raw_name)).name
        ext = Path(filename).suffix.lower()
        if ext not in MUSIC_EXTENSIONS:
            raise ApiError(
                400,
                "Unsupported audio type. Use wav, mp3, ogg, oga, flac, m4a, aac or opus.",
            )
        display = (display_q or Path(filename).stem).strip()[:60] or "Music"
        stored = f"{uuid.uuid4().hex}{ext}"
        destination = self.app.music_dir / stored
        size = self._receive_file(destination, MAX_MUSIC_BYTES)
        mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        try:
            row = self.app.store.add_music(display, stored, mime, size)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        log.info("music uploaded: %s (%d bytes)", display, size)
        self._send_json({"ok": True, "music": self.app.music_view(row)}, 201)

    def music_preview(self, match, body) -> None:
        self._require_admin()
        music_id = self._int_id(match)
        preview = self.app.engine.start_music_preview(music_id)
        self._send_json({"ok": True, "music_preview": preview})

    def music_preview_stop(self, match, body) -> None:
        self._require_admin()
        preview = self.app.engine.stop_music_preview()
        self._send_json({"ok": True, "music_preview": preview})

    def music_delete(self, match, body) -> None:
        self._require_admin()
        music_id = self._int_id(match)
        row = self.app.store.get_music(music_id)
        if not row:
            raise ApiError(404, "Music not found")
        used = self.app.store.music_in_use(music_id)
        if used["alarm"] or used["event"]:
            label = (used["alarm"] or used["event"]).get("label") or (
                used["alarm"] or used["event"]
            ).get("alarm_label")
            raise ApiError(
                409,
                f"This track is still used by “{label}”. Pick another sound for that alarm first.",
            )
        self.app.store.delete_music(music_id)
        (self.app.music_dir / row["stored_name"]).unlink(missing_ok=True)
        self._send_json({"ok": True})

    def music_file(self, match, body) -> None:
        self._require_login()
        row = self.app.store.get_music(self._int_id(match))
        if not row:
            raise ApiError(404, "Music not found")
        path = self.app.music_dir / row["stored_name"]
        self._send_file(path, row["mime"] or "application/octet-stream")

    # ------------------------------------------------------------- calendars
    def calendars_list(self, match, body) -> None:
        self._require_login()
        self._send_json({"ok": True, "calendars": self.app.store.list_calendars()})

    def calendar_import(self, match, body) -> None:
        self._require_admin()
        if len(self.app.store.list_calendars()) >= MAX_CALENDARS:
            raise ApiError(400, f"Maximum of {MAX_CALENDARS} calendars")
        name = " ".join(str(body.get("name") or "").split())
        if not (1 <= len(name) <= 40):
            raise ApiError(400, "Calendar name must be 1-40 characters")
        csv_text = body.get("csv")
        if not isinstance(csv_text, str) or not csv_text.strip():
            raise ApiError(400, "CSV data is required")
        if len(csv_text) > MAX_BODY:
            raise ApiError(413, "CSV is too large")
        try:
            days = parse_calendar_csv(csv_text)
        except CalendarParseError as exc:
            raise ApiError(400, str(exc))
        item = self.app.store.create_calendar(name, days)
        rows = [c for c in self.app.store.list_calendars() if c["id"] == item["id"]]
        self._send_json({"ok": True, "calendar": rows[0] if rows else item}, 201)

    def calendar_delete(self, match, body) -> None:
        self._require_admin()
        calendar_id = self._int_id(match)
        if not self.app.store.get_calendar(calendar_id):
            raise ApiError(404, "Calendar not found")
        self.app.store.delete_calendar(calendar_id)
        self.app.engine.invalidate_calendars()
        self.app.engine.recompute_schedules()
        self._send_json({"ok": True})

    # ---------------------------------------------------------------- alarms
    def _alarm_view_response(self, alarm: dict) -> dict:
        return self.app.decorate_alarm(alarm, self._base())

    def alarm_create(self, match, body) -> None:
        self._require_admin()
        clean, error = self.app.validate_alarm(body)
        if error:
            raise ApiError(400, error)
        alarm = self.app.store.create_alarm(clean)
        self._send_json({"ok": True, "alarm": self._alarm_view_response(alarm)}, 201)

    def alarm_update(self, match, body) -> None:
        self._require_admin()
        alarm_id = self._int_id(match)
        existing = self.app.store.get_alarm(alarm_id)
        if not existing:
            raise ApiError(404, "Alarm not found")
        clean, error = self.app.validate_alarm(body, alarm_id)
        if error:
            raise ApiError(400, error)
        alarm = self.app.store.update_alarm(alarm_id, clean)
        if not clean["enabled"]:
            self.app.store.set_alarm_skip(alarm_id, False)
            self.app.engine.expire_alarm_link(alarm_id)
            alarm = self.app.store.get_alarm(alarm_id)
        elif existing and not existing["enabled"]:
            self.app.engine.clear_alarm_link_expiry(alarm_id)
            alarm = self.app.store.get_alarm(alarm_id)
        self._send_json({"ok": True, "alarm": self._alarm_view_response(alarm)})

    def alarm_delete(self, match, body) -> None:
        self._require_admin()
        alarm_id = self._int_id(match)
        active = self.app.store.active_event_for_alarm(alarm_id)
        if active:
            raise ApiError(
                409,
                "This alarm is ringing or snoozed. Stop it before deleting the alarm.",
            )
        alarm = self.app.store.get_alarm(alarm_id)
        if alarm and alarm.get("slug"):
            expires = time.time() + 6 * 3600
            if alarm.get("link_expires_at"):
                expires = max(expires, float(alarm["link_expires_at"]))
            self.app.store.retire_link(alarm["slug"], alarm["label"], expires)
        if not self.app.store.delete_alarm(alarm_id):
            raise ApiError(404, "Alarm not found")
        self._send_json({"ok": True})

    def alarm_toggle(self, match, body) -> None:
        self._require_admin()
        alarm_id = self._int_id(match)
        alarm = self.app.store.get_alarm(alarm_id)
        if not alarm:
            raise ApiError(404, "Alarm not found")
        enable = body.get("enabled")
        if enable is None:
            enable = not bool(alarm["enabled"])
        enable = bool(enable)
        if enable and alarm["mode"] == "challenge":
            active = [
                u for u in self.app.store.alarm_participants(alarm_id) if u["active"]
            ]
            if not active:
                raise ApiError(400, "Select at least one active user for this challenge alarm")
            ctype = alarm.get("challenge_type", "math")
            pool_kind = "choice" if ctype == "random_choice" else ctype
            if ctype in CUSTOM_TYPES and self.app.store.count_questions(pool_kind) < 1:
                raise ApiError(400, f"Add at least one {pool_kind} question first")
        next_fire = None
        if enable:
            next_fire = self.app.engine.next_fire_for(alarm)
            if next_fire is None:
                raise ApiError(
                    400,
                    "No future alarm day. Check the date or the selected special-days calendar.",
                )
        self.app.store.set_alarm_enabled(alarm_id, enable, next_fire)
        if not enable:
            self.app.store.set_alarm_skip(alarm_id, False)
            self.app.engine.expire_alarm_link(alarm_id)
        else:
            self.app.engine.clear_alarm_link_expiry(alarm_id)
        updated = self.app.store.get_alarm(alarm_id)
        self._send_json({"ok": True, "alarm": self._alarm_view_response(updated)})

    def alarm_skip(self, match, body) -> None:
        self._require_admin()
        alarm_id = self._int_id(match)
        alarm = self.app.store.get_alarm(alarm_id)
        if not alarm:
            raise ApiError(404, "Alarm not found")
        skip = bool(body.get("skip", True))
        if skip:
            if not alarm["enabled"] or not alarm.get("next_fire"):
                raise ApiError(400, "This alarm has no next occurrence to skip")
        self.app.store.set_alarm_skip(alarm_id, skip)
        updated = self.app.store.get_alarm(alarm_id)
        self._send_json({"ok": True, "alarm": self._alarm_view_response(updated)})

    def alarm_ring(self, match, body) -> None:
        self._require_admin()
        alarm_id = self._int_id(match)
        event = self.app.engine.fire_alarm(alarm_id, manual=True)
        self._send_json({"ok": True, "event": self.app.engine.event_view(event)}, 201)

    # ----------------------------------------------------------------- users
    def _clean_name(self, raw: object) -> str:
        name = " ".join(str(raw or "").split())
        if not (1 <= len(name) <= 30):
            raise ApiError(400, "Name must be 1-30 characters")
        if any(ord(c) < 32 for c in name):
            raise ApiError(400, "Name contains control characters")
        return name

    def _assert_unique_name(self, name: str, exclude_id: int | None = None) -> None:
        for user in self.app.store.list_users():
            if user["id"] == exclude_id:
                continue
            if user["name"].casefold() == name.casefold():
                raise ApiError(409, "That name is already used")

    def user_create(self, match, body) -> None:
        self._require_admin()
        if self.app.store.count_users() >= MAX_USERS:
            raise ApiError(400, f"Maximum of {MAX_USERS} users")
        name = self._clean_name(body.get("name"))
        self._assert_unique_name(name)
        user = self.app.store.add_user(name, bool(body.get("active", True)))
        self._send_json({"ok": True, "user": user}, 201)

    def user_update(self, match, body) -> None:
        self._require_admin()
        user_id = self._int_id(match)
        if not self.app.store.get_user(user_id):
            raise ApiError(404, "User not found")
        name = None
        if "name" in body:
            name = self._clean_name(body.get("name"))
            self._assert_unique_name(name, exclude_id=user_id)
        active = None
        if "active" in body:
            active = bool(body["active"])
        user = self.app.store.update_user(user_id, name=name, active=active)
        self._send_json({"ok": True, "user": user})

    def user_delete(self, match, body) -> None:
        self._require_admin()
        user_id = self._int_id(match)
        active = self.app.store.user_in_active_event(user_id)
        if active:
            raise ApiError(
                409,
                f"This user is answering “{active['alarm_label']}” right now. "
                "Stop the alarm first, or wait until it ends.",
            )
        if not self.app.store.delete_user(user_id):
            raise ApiError(404, "User not found")
        self._send_json({"ok": True})

    # ---------------------------------------------------------------- events
    def event_stop(self, match, body) -> None:
        self._require_admin()
        event_id = self._int_id(match)
        event = self.app.store.get_event(event_id)
        if not event:
            raise ApiError(404, "Alarm event not found")
        force = bool(body.get("force"))
        if event["mode"] == "challenge" and event["state"] == "ringing" and not force:
            raise ApiError(
                409,
                "Challenge alarm: the selected people have to answer first. "
                "Use the emergency stop if you really must.",
            )
        reason = "emergency stop by admin" if force else "stopped from panel"
        updated = self.app.engine.stop_event(event_id, reason, state="stopped")
        self._send_json({"ok": True, "event": self.app.engine.event_view(updated)})

    def event_snooze(self, match, body) -> None:
        self._require_admin()
        event_id = self._int_id(match)
        event = self.app.engine.snooze_event(event_id)
        self._send_json({"ok": True, "event": self.app.engine.event_view(event)})

    # ------------------------------------------------------------ challenge
    def challenge_state(self, match, body) -> None:
        data = self.app.engine.token_state(match.group("token"))
        if data is None:
            self._send_json({"ok": False, "error": "This link is not valid"}, 404)
            return
        ip_passed = self._ip_pass_payload(data["event_id"])
        if ip_passed and ip_passed["user_name"] != data.get("user_name"):
            data["ip_passed"] = ip_passed
        self._send_json({"ok": True, "challenge": data})

    def challenge_answer(self, match, body) -> None:
        self._check_origin()
        token = match.group("token")
        result = self.app.engine.answer(token, body.get("answer"))
        answer = result.get("answer") or {}
        if result.get("status") == "correct" and answer.get("answered"):
            challenge = self.app.store.get_challenge_by_token(token)
            if challenge:
                self.app.store.record_ip_pass(
                    challenge["event_id"], self._client_ip(),
                    challenge["id"], challenge["user_name"],
                )
        self._send_json({"ok": True, **result})
