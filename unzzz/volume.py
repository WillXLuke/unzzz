"""Best-effort system volume control for alarm playback.

The server changes the system mixer before an alarm rings and restores the
previous level afterwards.  ALSA uses amixer, PulseAudio/PipeWire uses pactl.
Everything is best-effort: if no mixer is available the alarm still plays at
the current system volume.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import threading
import time

log = logging.getLogger("unzzz.volume")

MAX_VOLUME = 100
DEFAULT_TARGET = 80
_CONTROLS = (
    "Master", "PCM", "Speaker", "Headphone", "Digital", "Playback",
    "Playback Volume", "PCM Playback Volume", "Speaker Playback Volume",
    "Headphone Playback Volume", "Master Playback Volume",
)
_PERCENT = re.compile(r"\[(\d+)%\]")
_PACTL_PERCENT = re.compile(r"(\d+)%")


def _clamp(value: int | str | None, default: int = DEFAULT_TARGET) -> int:
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return max(0, min(MAX_VOLUME, number))


class VolumeController:
    def __init__(self, device: str = "", target: int = DEFAULT_TARGET, store=None) -> None:
        self.device = (device or "").strip()
        self.target = _clamp(target)
        self.store = store
        self._lock = threading.RLock()
        self._saved: int | None = None
        self._active: set[int] = set()
        self._control: str | None = None
        self._discovered: list[str] | None = None
        self._cache: int | None = None
        self._cache_at = 0.0
        self._error: str | None = None
        self.backend = "none"

    def set_device(self, device: str) -> None:
        with self._lock:
            self.device = (device or "").strip()
            self._control = None
            self._discovered = None
            self._cache = None
            self._cache_at = 0.0

    def set_target(self, target: int | str) -> None:
        self.target = _clamp(target)

    def _kind(self) -> str:
        if self.device.startswith("pulse:"):
            self.backend = "pulse"
        elif self.device.startswith("alsa:"):
            self.backend = "alsa"
        elif shutil.which("amixer"):
            self.backend = "alsa"
        elif shutil.which("pactl"):
            self.backend = "pulse"
        else:
            self.backend = "none"
        return self.backend

    def _card(self) -> tuple[str, ...]:
        match = re.search(r"CARD=([^,]+)", self.device)
        return ("-c", match.group(1)) if match else ()

    def _discover_controls(self) -> list[str]:
        """Return mixer control names, preferring playback volume controls.

        USB DACs often name their simple controls things like
        ``Playback Volume Playback Volume`` instead of Master/PCM, so a fixed
        list of names is not enough.
        """
        if self._discovered is not None:
            return self._discovered
        names: list[str] = []
        if shutil.which("amixer"):
            code, out, _err = self._run(
                ["amixer", *self._card(), "controls"]
            )
            if code == 0:
                names = re.findall(r"name='([^']+)'", out)

        def rank(name: str) -> int:
            low = name.lower()
            if "playback" in low and "volume" in low and "switch" not in low:
                return 0
            if "playback" in low and "switch" in low:
                return 1
            if "volume" in low and "switch" not in low:
                return 2
            return 3

        seen: set[str] = set()
        ordered: list[str] = []
        for name in sorted(names, key=rank):
            if name not in seen:
                seen.add(name)
                ordered.append(name)
        self._discovered = ordered
        return ordered

    def _controls(self) -> list[str]:
        if self._control:
            return [self._control]
        controls = self._discover_controls() + list(_CONTROLS)
        seen: set[str] = set()
        return [c for c in controls if not (c in seen or seen.add(c))]

    def _pulse_sink(self) -> str:
        return self.device.split(":", 1)[1] if self.device.startswith("pulse:") else "@DEFAULT_SINK@"

    @staticmethod
    def _run(argv: list[str]) -> tuple[int, str, str]:
        try:
            proc = subprocess.run(
                argv, capture_output=True, text=True, timeout=2.0,
            )
            return proc.returncode, proc.stdout or "", proc.stderr or ""
        except (OSError, subprocess.SubprocessError) as exc:
            return 127, "", str(exc)

    def _read_alsa(self) -> tuple[int | None, str | None]:
        if not shutil.which("amixer"):
            return None, "amixer is not installed"
        controls = self._controls()
        last_error = None
        for control in controls:
            if not control:
                continue
            code, out, err = self._run(
                ["amixer", *self._card(), "sget", control]
            )
            if code != 0:
                last_error = (err.strip() or out.strip() or f"amixer exited {code}")[:200]
                continue
            match = _PERCENT.search(out)
            if match:
                self._control = control
                return int(match.group(1)), None
            last_error = "amixer did not report a percentage"
        return None, last_error or "no ALSA mixer control found"

    def _write_alsa(self, percent: int) -> tuple[bool, str | None]:
        if not shutil.which("amixer"):
            return False, "amixer is not installed"
        controls = self._controls()
        last_error = None
        for control in controls:
            if not control:
                continue
            code, _out, err = self._run(
                ["amixer", *self._card(), "sset", control, f"{percent}%"]
            )
            if code == 0:
                self._control = control
                return True, None
            last_error = (err.strip() or f"amixer exited {code}")[:200]
        return False, last_error or "could not set ALSA volume"

    def _read_pulse(self) -> tuple[int | None, str | None]:
        if not shutil.which("pactl"):
            return None, "pactl is not installed"
        code, out, err = self._run(
            ["pactl", "get-sink-volume", self._pulse_sink()]
        )
        if code != 0:
            return None, (err.strip() or out.strip() or f"pactl exited {code}")[:200]
        match = _PACTL_PERCENT.search(out)
        if not match:
            return None, "pactl did not report a percentage"
        return int(match.group(1)), None

    def _write_pulse(self, percent: int) -> tuple[bool, str | None]:
        if not shutil.which("pactl"):
            return False, "pactl is not installed"
        code, _out, err = self._run(
            ["pactl", "set-sink-volume", self._pulse_sink(), f"{percent}%"]
        )
        if code == 0:
            return True, None
        return False, (err.strip() or f"pactl exited {code}")[:200]

    def current(self, force: bool = False) -> tuple[int | None, str | None]:
        with self._lock:
            now = time.monotonic()
            if not force and self._cache is not None and now - self._cache_at < 3.0:
                return self._cache, self._error
            kind = self._kind()
            if kind == "alsa":
                value, error = self._read_alsa()
            elif kind == "pulse":
                value, error = self._read_pulse()
            else:
                value, error = None, "No amixer or pactl found"
            self._cache = value
            self._cache_at = now
            self._error = error
            return value, error

    def set_percent(self, percent: int) -> tuple[bool, str | None]:
        percent = _clamp(percent)
        with self._lock:
            kind = self._kind()
            if kind == "alsa":
                ok, error = self._write_alsa(percent)
            elif kind == "pulse":
                ok, error = self._write_pulse(percent)
            else:
                ok, error = False, "No amixer or pactl found"
            self._cache = percent if ok else None
            self._cache_at = time.monotonic()
            self._error = error
            if not ok:
                log.warning("volume set failed: %s", error)
            return ok, error

    def _save_setting(self, value: int | None) -> None:
        if self.store is None:
            return
        try:
            self.store.set_setting("volume_saved", "" if value is None else str(value))
        except Exception:
            log.exception("could not persist saved volume")

    def _read_saved_setting(self) -> int | None:
        if self.store is None:
            return None
        try:
            raw = self.store.get_setting("volume_saved")
            if raw is None or str(raw).strip() == "":
                return None
            value = int(str(raw).strip())
            return value if 0 <= value <= MAX_VOLUME else None
        except Exception:
            return None

    def begin(self, event_id: int) -> bool:
        """Set the target volume before an event starts ringing."""
        with self._lock:
            if event_id in self._active:
                return True
            if not self._active:
                current, error = self.current(force=True)
                if current is None:
                    log.info("cannot read current volume: %s", error)
                    return False
                self._saved = current
                # Persist before changing the mixer so a crash between the two
                # calls can still be repaired on the next start.
                self._save_setting(current)
                if not self.set_percent(self.target)[0]:
                    self._saved = None
                    self._save_setting(None)
                    return False
                log.info("alarm volume %s%% (was %s%%)", self.target, current)
            self._active.add(event_id)
            return True

    def end(self, event_id: int) -> None:
        """Restore the saved volume when the last ringing event stops."""
        with self._lock:
            self._active.discard(event_id)
            if self._active:
                return
            saved = self._saved
            if saved is None:
                saved = self._read_saved_setting()
            if saved is not None:
                ok, error = self.set_percent(saved)
                if not ok:
                    log.warning("could not restore volume %s%%: %s", saved, error)
                    self._saved = saved
                    return
                log.info("restored volume %s%%", saved)
            self._saved = None
            self._save_setting(None)

    def end_all(self) -> None:
        with self._lock:
            self._active.clear()
            saved = self._saved if self._saved is not None else self._read_saved_setting()
            if saved is not None:
                ok, error = self.set_percent(saved)
                if not ok:
                    log.warning("could not restore volume %s%%: %s", saved, error)
                    self._saved = saved
                    return
            self._saved = None
            self._save_setting(None)

    def restore_persisted(self) -> None:
        """After a crash, put back the volume saved by a previous ring."""
        with self._lock:
            if self._active:
                return
            saved = self._read_saved_setting()
            if saved is not None:
                ok, error = self.set_percent(saved)
                if not ok:
                    log.warning("could not restore persisted volume %s%%: %s", saved, error)
                    return
                log.info("restored persisted volume %s%%", saved)
            self._save_setting(None)

    def status(self) -> dict:
        with self._lock:
            current, error = self.current()
            return {
                "available": current is not None,
                "current": current,
                "target": self.target,
                "backend": self._kind(),
                "error": error,
            }
