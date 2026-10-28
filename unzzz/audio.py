"""Sound output for the alarm.

No audio library is used.  The built-in two-tone WAV is synthesised with the
standard library; uploaded music is handed to whichever command-line player
exists on the box.  aplay is the lightest choice for WAV on Raspberry Pi OS,
while mpv/ffplay handle MP3, OGG, FLAC and M4A.

Playback devices can be selected from the panel.  Values look like
``alsa:plughw:CARD=Headphones,DEV=0`` or ``pulse:alsa_output.usb-...``.
"""

from __future__ import annotations

import array
import logging
import math
import os
import shlex
import shutil
import subprocess
import threading
import time
import wave
from pathlib import Path

log = logging.getLogger("unzzz.audio")

SAMPLE_RATE = 22_050
BEEP_SECONDS = 5.79

_WAV_SUFFIXES = {".wav", ".wave"}
_PLAYER_ORDER_WAV = ["aplay", "paplay", "mpv", "ffplay", "play"]
_PLAYER_ORDER_OTHER = ["mpv", "ffplay", "paplay", "play"]


def build_beep(path: Path) -> None:
    """Synthesise an alarm pattern once (two tones, short gaps)."""
    if path.exists() and path.stat().st_size > 1024:
        return
    frames = array.array("h")
    pattern = [
        (880.0, 0.26), (0.0, 0.08),
        (1174.7, 0.26), (0.0, 0.08),
        (880.0, 0.26), (0.0, 0.08),
        (1174.7, 0.26), (0.0, 0.65),
    ]
    cycles = 3
    fade = int(SAMPLE_RATE * 0.008)
    for _ in range(cycles):
        for freq, seconds in pattern:
            n = int(SAMPLE_RATE * seconds)
            if freq == 0.0:
                frames.extend([0] * n)
                continue
            for i in range(n):
                env = 1.0
                if i < fade:
                    env = i / fade
                elif i > n - fade:
                    env = max(0.0, (n - i) / fade)
                sample = math.sin(2 * math.pi * freq * i / SAMPLE_RATE)
                frames.append(int(32767 * 0.32 * env * sample))
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with wave.open(str(tmp), "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(SAMPLE_RATE)
        fh.writeframes(frames.tobytes())
    tmp.replace(path)


def parse_device(value: str) -> tuple[str, str] | None:
    value = (value or "").strip()
    if not value or ":" not in value:
        return None
    kind, name = value.split(":", 1)
    if kind not in ("alsa", "pulse") or not name or any(ch.isspace() for ch in name):
        return None
    return kind, name


def list_audio_devices() -> list[dict]:
    """Enumerate ALSA PCMs and PulseAudio sinks.  Never raises."""
    devices: list[dict] = [{"value": "", "label": "System default"}]
    seen = {""}

    def add(value: str, label: str) -> None:
        if value in seen or len(devices) >= 60:
            return
        seen.add(value)
        devices.append({"value": value, "label": label})

    if shutil.which("aplay"):
        try:
            proc = subprocess.run(
                ["aplay", "-L"], capture_output=True, text=True, timeout=3
            )
            lines = (proc.stdout or "").splitlines()
            i = 0
            while i < len(lines):
                line = lines[i]
                if line and not line[0].isspace():
                    name = line.strip()
                    desc = ""
                    if i + 1 < len(lines) and lines[i + 1].startswith((" ", "\t")):
                        desc = lines[i + 1].strip()
                        i += 1
                    if name and not name.startswith("*") and name != "null":
                        label = f"ALSA · {name}"
                        if desc:
                            label += f" — {desc[:55]}"
                        add(f"alsa:{name}", label)
                i += 1
        except (OSError, subprocess.SubprocessError):
            pass

    if shutil.which("pactl"):
        try:
            proc = subprocess.run(
                ["pactl", "list", "short", "sinks"],
                capture_output=True, text=True, timeout=3,
            )
            for line in (proc.stdout or "").splitlines():
                parts = line.split("\t")
                if len(parts) >= 2 and parts[1].strip():
                    name = parts[1].strip()
                    add(f"pulse:{name}", f"Pulse · {name}")
        except (OSError, subprocess.SubprocessError):
            pass

    return devices


class Audio:
    def __init__(
        self,
        data_dir: Path,
        command: str | None = None,
        gap_seconds: float = 2.0,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.beep_path = self.data_dir / "beep.wav"
        self.gap_seconds = max(0.5, float(gap_seconds))
        self._lock = threading.Lock()
        self._last_error: str | None = None
        self._logged_error: str | None = None
        self._stop_current: threading.Event | None = None
        self._current_proc: subprocess.Popen | None = None
        self._preview_lock = threading.RLock()
        self._preview_proc: subprocess.Popen | None = None
        self._preview_thread: threading.Thread | None = None
        self._preview_error: str | None = None
        self.mode = "auto"
        self.backend = "none"
        self.device = ""
        self.custom_argv: list[str] | None = None
        self.players: dict[str, str] = {}
        for name in ("aplay", "paplay", "mpv", "ffplay", "play"):
            found = shutil.which(name)
            if found:
                self.players[name] = found
        self._configure(command)
        self._update_backend()

    # ------------------------------------------------------------- discovery
    def _configure(self, command: str | None) -> None:
        raw = (
            command if command is not None
            else os.environ.get("UNZZZ_AUDIO_CMD", "")
        ).strip()
        if raw.lower() in {"none", "off", "silent", "0", "false"}:
            self.mode = "none"
            self.backend = "none"
            log.info("audio disabled (UNZZZ_AUDIO_CMD=%s)", raw)
            return
        if raw:
            try:
                parts = shlex.split(raw)
            except ValueError as exc:
                log.error("cannot parse UNZZZ_AUDIO_CMD: %s", exc)
                parts = []
            if parts:
                self.mode = "custom"
                self.custom_argv = parts
                log.info("audio command: %s", " ".join(parts))
                return
        if not self.players:
            log.warning(
                "no audio player found; install alsa-utils for aplay, or set UNZZZ_AUDIO_CMD"
            )

    def set_device(self, value: str) -> None:
        self.device = (value or "").strip()
        self._update_backend()

    def _update_backend(self) -> None:
        self.backend = "none" if self.mode == "none" else "custom"
        if self.mode == "auto":
            player = self._pick_player(self.beep_path)
            self.backend = player or "none"

    def _custom_available(self) -> bool:
        if not self.custom_argv:
            return False
        first = self.custom_argv[0]
        return bool(shutil.which(first) or Path(first).is_file())

    def _device_kind_name(self) -> tuple[str, str] | None:
        return parse_device(self.device)

    def _player_supports_device(self, player: str) -> bool:
        parsed = self._device_kind_name()
        if parsed is None:
            return not self.device
        kind, _name = parsed
        if kind == "alsa":
            return player in ("aplay", "mpv")
        if kind == "pulse":
            return player in ("paplay", "mpv")
        return False

    def _pick_player(self, path: Path) -> str | None:
        suffix = path.suffix.lower()
        order = _PLAYER_ORDER_WAV if suffix in _WAV_SUFFIXES else _PLAYER_ORDER_OTHER
        for name in order:
            if name in self.players and self._player_supports_device(name):
                return name
        return None

    def _device_args(self, player: str) -> list[str]:
        parsed = self._device_kind_name()
        if parsed is None:
            return []
        kind, name = parsed
        # A bare "hw:" PCM often accepts only one exact sample rate/format.
        # The generated beep is 22.05 kHz mono; route it through the ALSA
        # plug layer so normal DACs can convert it.  "plughw:" is still the
        # same card/device, just with format conversion.
        if kind == "alsa" and name.startswith("hw:"):
            name = "plughw:" + name[3:]
        if player == "aplay" and kind == "alsa":
            return ["-D", name]
        if player == "paplay" and kind == "pulse":
            return [f"--device={name}"]
        if player == "mpv":
            return [f"--audio-device={kind}/{name}"]
        return []

    def _custom_argv_for(self, path: Path) -> list[str]:
        assert self.custom_argv is not None
        file_path = str(path)
        if any("{file}" in part for part in self.custom_argv):
            return [part.replace("{file}", file_path) for part in self.custom_argv]
        return [*self.custom_argv, file_path]

    def command_for(self, path: Path | str | None = None) -> list[str] | None:
        """Expose the argv that would be used (handy for diagnostics/tests)."""
        path = Path(path) if path else self.beep_path
        if self.mode == "none":
            return None
        if self.mode == "custom":
            return self._custom_argv_for(path) if self.custom_argv else None
        player = self._pick_player(path)
        if not player:
            return None
        if player == "aplay":
            return [self.players[player], "-q", *self._device_args(player), str(path)]
        if player == "paplay":
            return [self.players[player], *self._device_args(player), str(path)]
        if player == "mpv":
            return [
                self.players[player], "--no-video", "--really-quiet",
                "--no-terminal", f"--volume={os.environ.get('UNZZZ_VOLUME', '90')}",
                *self._device_args(player), str(path),
            ]
        if player == "ffplay":
            return [
                self.players[player], "-nodisp", "-autoexit", "-loglevel", "quiet",
                str(path),
            ]
        return [self.players[player], "-q", str(path)]

    def describe(self) -> dict:
        available = self.mode != "none" and (
            self._custom_available() if self.mode == "custom"
            else bool(self._pick_player(self.beep_path))
        )
        if self.mode == "none":
            hint = "Sound is disabled. Remove UNZZZ_AUDIO_CMD=none to enable it."
        elif self.mode == "custom" and not self._custom_available():
            hint = "The custom audio command was not found."
        elif self.mode == "custom":
            hint = "Using a custom player command. Playback device selection is ignored."
        elif not available:
            hint = (
                "No installed player can play this format"
                + (" with the selected playback device" if self.device else "")
                + ". Install alsa-utils/mpv or change the device in Settings."
            )
        else:
            label = self.device or "system default"
            hint = f"Playing through {self.backend} ({label}). Use the test button to verify."
        return {
            "backend": self.backend,
            "available": available,
            "custom": self.mode == "custom",
            "device": self.device,
            "players": sorted(self.players),
            "hint": hint,
            "last_error": self._last_error,
        }

    # ---------------------------------------------------------------- output
    def play_once(
        self,
        stop_event: threading.Event | None = None,
        capture: bool = False,
        path: Path | None = None,
    ) -> tuple[bool, str | None]:
        if self.mode == "none":
            return True, None
        path = Path(path) if path else self.beep_path
        if path == self.beep_path:
            try:
                build_beep(self.beep_path)
            except OSError as exc:
                return False, f"cannot write beep file: {exc}"
        if not path.is_file():
            message = "audio file is missing"
            self._set_error(message)
            return False, message
        argv = self.command_for(path)
        if not argv:
            message = "no audio player available for this file/device"
            self._set_error(message)
            return False, message
        try:
            proc = subprocess.Popen(
                argv,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE if capture else subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
        except OSError as exc:
            self._set_error(str(exc))
            return False, str(exc)
        with self._lock:
            self._current_proc = proc
            self._stop_current = stop_event
        stopped_early = False
        is_beep = path == self.beep_path
        deadline = time.monotonic() + (20.0 if is_beep else 3600.0)
        try:
            while True:
                try:
                    proc.wait(timeout=0.1)
                    break
                except subprocess.TimeoutExpired:
                    if stop_event is not None and stop_event.is_set():
                        stopped_early = True
                        proc.terminate()
                        try:
                            proc.wait(timeout=1.5)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                        break
                    if time.monotonic() > deadline:
                        proc.kill()
                        self._set_error("audio player timed out")
                        return False, "audio player timed out"
            if stopped_early:
                if capture and proc.stderr is not None:
                    proc.stderr.close()
                self._set_error(None)
                return True, None
            stderr = b""
            if capture and proc.stderr is not None:
                stderr = proc.stderr.read() or b""
                proc.stderr.close()
            if proc.returncode not in (0, None):
                text = stderr.decode("utf-8", "replace").strip()[:300]
                message = text or f"{self.backend} exited with {proc.returncode}"
                self._set_error(message)
                return False, message
            self._set_error(None)
            return True, None
        finally:
            with self._lock:
                self._current_proc = None
                self._stop_current = None

    def _set_error(self, message: str | None) -> None:
        self._last_error = message
        if message and message != self._logged_error:
            log.warning("audio error: %s", message)
            self._logged_error = message

    def ring_loop(self, stop_event: threading.Event, path: Path | None = None) -> None:
        """Blocking ring loop; returns soon after stop_event is set."""
        source = Path(path) if path else self.beep_path
        while not stop_event.is_set():
            ok, _err = self.play_once(stop_event, path=source)
            if stop_event.is_set():
                break
            if not ok:
                # Don't hammer a broken player/file; try again a bit later.
                stop_event.wait(5.0)
            else:
                stop_event.wait(self.gap_seconds)

    def stop_current(self) -> None:
        with self._lock:
            proc = self._current_proc
            ev = self._stop_current
        if ev is not None:
            ev.set()
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
            except OSError:
                pass

    def start_preview(self, path: Path | None = None) -> tuple[bool, str | None]:
        """Play one music file on the server until stop_preview()."""
        path = Path(path) if path else None
        if not path or not path.is_file():
            return False, "audio file is missing"
        if self.mode == "none":
            return False, "Sound is disabled"
        argv = self.command_for(path)
        if not argv:
            return False, "no audio player available for this file/device"
        self.stop_preview()
        try:
            proc = subprocess.Popen(
                argv,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
            )
        except OSError as exc:
            return False, str(exc)
        with self._preview_lock:
            self._preview_proc = proc
            self._preview_error = None

        def watch() -> None:
            try:
                proc.wait()
                err = b""
                if proc.stderr is not None:
                    err = proc.stderr.read() or b""
                    proc.stderr.close()
                with self._preview_lock:
                    if self._preview_proc is proc:
                        if proc.returncode not in (0, None):
                            self._preview_error = (
                                err.decode("utf-8", "replace").strip()
                                or f"player exited with {proc.returncode}"
                            )
                        self._preview_proc = None
            except Exception:
                log.exception("music preview watcher failed")

        thread = threading.Thread(target=watch, name="unzzz-preview", daemon=True)
        with self._preview_lock:
            self._preview_thread = thread
        thread.start()
        return True, None

    def stop_preview(self) -> bool:
        with self._preview_lock:
            proc = self._preview_proc
            self._preview_proc = None
            self._preview_error = None
        if proc is None:
            return False
        if proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=1.5)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    proc.kill()
                except OSError:
                    pass
        return True

    def preview_status(self) -> dict:
        with self._preview_lock:
            playing = self._preview_proc is not None and self._preview_proc.poll() is None
            return {
                "playing": playing,
                "error": self._preview_error,
            }

    def test(self, path: Path | None = None) -> tuple[bool, str | None]:
        if self.mode == "none":
            return False, "Sound is disabled"
        if self.mode == "custom" and not self._custom_available():
            return False, "The custom audio command was not found"
        if self.mode == "auto" and not self._pick_player(path or self.beep_path):
            return False, "No audio player can handle this file/device"
        return self.play_once(capture=True, path=path)
