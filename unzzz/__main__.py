"""Command line entry point: python3 -m unzzz ..."""

from __future__ import annotations

import argparse
import getpass
import json
import logging
import os
import signal
import socket
import sys
import threading
from pathlib import Path

from . import __version__
from .auth import MIN_PASSWORD_LEN, Auth
from .db import Store
from .engine import Engine
from .schedule import detect_system_timezone
from .web import App


def default_data_dir() -> Path:
    """Return the conventional writable data directory for this installation.

    A system service uses /var/lib/unzzz.  A normal user run follows the XDG
    Base Directory specification so the database, music and generated beep do
    not end up in whatever directory happened to be current.
    """
    env = os.environ.get("UNZZZ_DATA_DIR")
    if env:
        return Path(env).expanduser()
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        return Path("/var/lib/unzzz")
    base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return Path(base) / "unzzz"


def ensure_data_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, 0o750)
    except OSError:
        pass


def lan_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("192.0.2.1", 9))
            return sock.getsockname()[0]
        finally:
            sock.close()
    except OSError:
        return "127.0.0.1"


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def bootstrap_password(store: Store, auth: Auth) -> None:
    """Seed the admin password from UNZZZ_PASSWORD on a brand-new install."""
    env_password = os.environ.get("UNZZZ_PASSWORD")
    if env_password and not auth.configured:
        if len(env_password) < MIN_PASSWORD_LEN:
            logging.getLogger("unzzz").error(
                "UNZZZ_PASSWORD is shorter than %d characters; ignoring it", MIN_PASSWORD_LEN
            )
            return
        auth.set_password(env_password)
        logging.getLogger("unzzz").info("initial admin password set from UNZZZ_PASSWORD")


def cmd_serve(args: argparse.Namespace) -> int:
    setup_logging(args.log_level)
    log = logging.getLogger("unzzz")
    data_dir = Path(args.data_dir).expanduser().resolve()
    ensure_data_dir(data_dir)
    store = Store(data_dir / "unzzz.sqlite3")
    auth = Auth(store)
    bootstrap_password(store, auth)
    audio_cmd = "none" if args.no_audio else args.audio_cmd
    engine = Engine(store, data_dir, audio_command=audio_cmd)
    app = App(store, engine, auth, data_dir)
    app.trust_proxy = bool(os.environ.get("UNZZZ_TRUST_PROXY") == "1")

    httpd = app.make_server(args.bind, args.port)
    engine.start()
    stop = threading.Event()

    def on_signal(signum, _frame):
        log.info("received signal %s, shutting down", signum)
        stop.set()

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)

    thread = threading.Thread(
        target=httpd.serve_forever,
        kwargs={"poll_interval": 0.4},
        name="unzzz-http",
        daemon=True,
    )
    thread.start()

    host = "127.0.0.1" if args.bind in ("127.0.0.1", "localhost") else lan_ip()
    log.info("unzzz %s listening on http://%s:%d", __version__, host, args.port)
    log.info("data directory: %s", data_dir)
    log.info("timezone: %s | audio: %s", engine.tz_name, engine.audio.backend)
    if not auth.configured:
        log.warning(
            "no admin password yet - open http://%s:%d/ and finish setup", host, args.port
        )

    try:
        while not stop.wait(0.5):
            pass
    except KeyboardInterrupt:
        stop.set()

    log.info("stopping")
    httpd.shutdown()
    httpd.server_close()
    engine.stop()
    store.close()
    return 0


def cmd_passwd(args: argparse.Namespace) -> int:
    data_dir = Path(args.data_dir).expanduser().resolve()
    ensure_data_dir(data_dir)
    store = Store(data_dir / "unzzz.sqlite3")
    auth = Auth(store)
    password = args.password
    if not password:
        if sys.stdin.isatty():
            first = getpass.getpass("New admin password: ")
            second = getpass.getpass("Repeat password: ")
            if first != second:
                print("Passwords do not match.", file=sys.stderr)
                return 1
            password = first
        else:
            password = sys.stdin.readline().rstrip("\n")
    if len(password) < MIN_PASSWORD_LEN:
        print(f"Password must be at least {MIN_PASSWORD_LEN} characters.", file=sys.stderr)
        return 1
    auth.set_password(password)
    print("Admin password updated.")
    store.close()
    return 0


def cmd_audio_test(args: argparse.Namespace) -> int:
    from .audio import Audio

    data_dir = Path(args.data_dir).expanduser().resolve()
    ensure_data_dir(data_dir)
    audio = Audio(data_dir, command="none" if args.no_audio else args.audio_cmd)
    print(json.dumps(audio.describe(), indent=2))
    ok, error = audio.test()
    if ok:
        print("Audio OK.")
        return 0
    print(f"Audio failed: {error}", file=sys.stderr)
    return 1


def cmd_doctor(args: argparse.Namespace) -> int:
    setup_logging("INFO")
    data_dir = Path(args.data_dir).expanduser().resolve()
    ensure_data_dir(data_dir)
    print(f"unzzz {__version__}")
    print(f"python {sys.version.split()[0]}  ({sys.executable})")
    print(f"data dir: {data_dir}")
    print(f"system timezone: {detect_system_timezone()}")
    print(f"user: {getpass.getuser()}")
    store = Store(data_dir / "unzzz.sqlite3")
    print(f"database: {store.path} ({store.path.stat().st_size} bytes)")
    print(f"users: {store.count_users()} / 200")
    print(f"alarms: {len(store.list_alarms())}")
    from .audio import Audio

    audio = Audio(data_dir, command="none" if args.no_audio else args.audio_cmd)
    audio.set_device(store.get_setting("audio_device") or "")
    print("audio: " + json.dumps(audio.describe()))
    print(f"beep file: {audio.beep_path}")
    print("audio test: ", end="", flush=True)
    ok, error = audio.test()
    print("ok" if ok else f"FAILED ({error})")
    store.close()
    return 0 if ok else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="unzzz",
        description="A lightweight server-side alarm clock with wake-up challenges.",
    )
    parser.add_argument("--version", action="version", version=f"unzzz {__version__}")
    sub = parser.add_subparsers(dest="command")

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--data-dir",
            default=str(default_data_dir()),
            help="runtime data directory (default: $UNZZZ_DATA_DIR, /var/lib/unzzz as root, or $XDG_DATA_HOME/unzzz)",
        )
        p.add_argument("--audio-cmd", default=os.environ.get("UNZZZ_AUDIO_CMD"),
                       help="custom player command; {file} is replaced with the wav path")
        p.add_argument("--no-audio", action="store_true", help="disable sound")

    serve = sub.add_parser("serve", help="run the web server")
    common(serve)
    serve.add_argument("--bind", default=os.environ.get("UNZZZ_BIND", "0.0.0.0"))
    serve.add_argument("--port", type=int, default=int(os.environ.get("UNZZZ_PORT", "8888")))
    serve.add_argument(
        "--log-level", default=os.environ.get("UNZZZ_LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "debug", "info", "warning", "error"],
    )
    serve.set_defaults(func=cmd_serve)

    passwd = sub.add_parser("passwd", help="set or reset the admin password")
    common(passwd)
    passwd.add_argument("--password", help="new password (otherwise prompt / stdin)")
    passwd.set_defaults(func=cmd_passwd)

    audio = sub.add_parser("audio-test", help="detect the player and play one beep")
    common(audio)
    audio.set_defaults(func=cmd_audio_test)

    doctor = sub.add_parser("doctor", help="print diagnostics for Raspberry Pi setups")
    common(doctor)
    doctor.set_defaults(func=cmd_doctor)

    sub.add_parser("version", help="print the version")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command in (None, "version"):
        print(f"unzzz {__version__}")
        if args.command is None:
            parser.print_help()
        return 0
    os.umask(0o077)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
