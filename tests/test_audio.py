"""Audio synthesis and the subprocess ring loop."""

from __future__ import annotations

import os
import shutil
import tempfile
import threading
import time
import unittest
import wave
from pathlib import Path

from unzzz.audio import SAMPLE_RATE, Audio, build_beep, list_audio_devices
from unzzz.db import Store
from unzzz.engine import Engine


class AudioTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="unzzz-audio-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_beep_wav_is_valid(self) -> None:
        path = self.tmp / "beep.wav"
        build_beep(path)
        self.assertGreater(path.stat().st_size, 100_000)
        with wave.open(str(path), "rb") as fh:
            self.assertEqual(fh.getnchannels(), 1)
            self.assertEqual(fh.getsampwidth(), 2)
            self.assertEqual(fh.getframerate(), SAMPLE_RATE)
            self.assertGreater(fh.getnframes(), int(SAMPLE_RATE * 5))

    def test_silent_mode(self) -> None:
        audio = Audio(self.tmp, command="none")
        self.assertFalse(audio.describe()["available"])
        ok, error = audio.test()
        self.assertFalse(ok)
        self.assertIn("disabled", error)

    def test_true_player(self) -> None:
        audio = Audio(self.tmp, command="/bin/true")
        self.assertEqual(audio.backend, "custom")
        ok, error = audio.test()
        self.assertTrue(ok, error)
        self.assertTrue((self.tmp / "beep.wav").exists())

    def test_ring_loop_plays_and_stops_promptly(self) -> None:
        log = self.tmp / "calls.log"
        script = self.tmp / "fake-player.sh"
        script.write_text(
            "#!/bin/sh\n"
            f'echo played >> "{log}"\n'
            "sleep 10\n"
        )
        script.chmod(0o755)
        audio = Audio(self.tmp, command=str(script), gap_seconds=0.5)
        stop = threading.Event()
        thread = threading.Thread(target=audio.ring_loop, args=(stop,), daemon=True)
        started = time.time()
        thread.start()

        deadline = time.time() + 5
        while time.time() < deadline and not log.exists():
            time.sleep(0.05)
        self.assertTrue(log.exists(), "fake player was never invoked")

        stop.set()
        thread.join(timeout=3)
        self.assertFalse(thread.is_alive(), "ring loop did not stop")
        self.assertLess(time.time() - started, 8)
        # A stop must not be reported as an audio fault.
        self.assertIsNone(audio._last_error)

    def test_device_discovery_parses_aplay_and_pactl(self) -> None:
        bindir = self.tmp / "bin"
        bindir.mkdir()
        aplay = bindir / "aplay"
        aplay.write_text(
            "#!/bin/sh\n"
            "if [ \"$1\" = \"-L\" ]; then\n"
            "  printf 'default\\n    Default ALSA Output\\nsysdefault:CARD=Headphones\\n    USB Headset\\nnull\\n'\n"
            "fi\n"
        )
        aplay.chmod(0o755)
        pactl = bindir / "pactl"
        pactl.write_text(
            "#!/bin/sh\n"
            "printf '0\\talsa_output.usb-headset\\tmodule-alsa-card\\ts16le\\tRUNNING\\n'\n"
        )
        pactl.chmod(0o755)
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{bindir}{os.pathsep}{old_path}"
        try:
            devices = list_audio_devices()
        finally:
            os.environ["PATH"] = old_path
        values = [d["value"] for d in devices]
        self.assertIn("", values)
        self.assertIn("alsa:default", values)
        self.assertIn("alsa:sysdefault:CARD=Headphones", values)
        self.assertIn("pulse:alsa_output.usb-headset", values)
        self.assertNotIn("alsa:null", values)

    def test_device_selection_arguments(self) -> None:
        audio = Audio(self.tmp, command=None)
        audio.mode = "auto"
        audio.players = {"aplay": "/usr/bin/aplay"}
        wav = self.tmp / "x.wav"
        audio.set_device("alsa:plughw:CARD=Headphones,DEV=0")
        argv = audio.command_for(wav)
        self.assertEqual(argv[0], "/usr/bin/aplay")
        self.assertIn("-D", argv)
        self.assertIn("plughw:CARD=Headphones,DEV=0", argv)

        audio.players = {"mpv": "/usr/bin/mpv"}
        audio.set_device("pulse:alsa_output.usb")
        argv = audio.command_for(wav)
        self.assertIn("--audio-device=pulse/alsa_output.usb", argv)
        self.assertIn(str(wav), argv)

    def test_format_and_device_compatibility(self) -> None:
        audio = Audio(self.tmp, command=None)
        audio.mode = "auto"
        audio.players = {"aplay": "/usr/bin/aplay"}
        audio.set_device("")
        self.assertIsNone(audio.command_for(self.tmp / "song.mp3"))
        audio.players = {"mpv": "/usr/bin/mpv"}
        self.assertIsNotNone(audio.command_for(self.tmp / "song.mp3"))
        audio.set_device("bogus")
        self.assertIsNone(audio.command_for(self.tmp / "song.mp3"))

    def test_preview_starts_and_stops(self) -> None:
        script = self.tmp / "preview-player.sh"
        script.write_text("#!/bin/sh\nsleep 10\n")
        script.chmod(0o755)
        path = self.tmp / "preview.wav"
        build_beep(path)
        audio = Audio(self.tmp, command=str(script))
        ok, error = audio.start_preview(path)
        self.assertTrue(ok, error)
        deadline = time.time() + 2
        while time.time() < deadline and not audio.preview_status()["playing"]:
            time.sleep(0.02)
        self.assertTrue(audio.preview_status()["playing"])
        self.assertTrue(audio.stop_preview())
        deadline = time.time() + 2
        while time.time() < deadline and audio.preview_status()["playing"]:
            time.sleep(0.02)
        self.assertFalse(audio.preview_status()["playing"])

    def test_engine_ring_thread_uses_the_player_and_stops(self) -> None:
        log = self.tmp / "engine-calls.log"
        script = self.tmp / "engine-player.sh"
        script.write_text(
            "#!/bin/sh\n"
            f'echo played >> "{log}"\n'
            "sleep 10\n"
        )
        script.chmod(0o755)
        store = Store(self.tmp / "engine.sqlite3")
        engine = Engine(store, self.tmp, audio_command=str(script))
        try:
            alarm = store.create_alarm(
                {
                    "label": "Engine test",
                    "time": "07:30",
                    "days_mask": 0b1111111,
                    "once_date": None,
                    "enabled": 1,
                    "mode": "standard",
                    "difficulty": "normal",
                    "snooze_minutes": 9,
                    "max_snoozes": 2,
                    "max_ring_minutes": 15,
                    "next_fire": time.time() + 3600,
                }
            )
            event = engine.fire_alarm(alarm["id"], manual=True)
            deadline = time.time() + 5
            while time.time() < deadline and not log.exists():
                time.sleep(0.05)
            self.assertTrue(log.exists(), "engine did not invoke the audio player")
            engine.stop_event(event["id"], "test cleanup")
            deadline = time.time() + 3
            while engine.rings and time.time() < deadline:
                time.sleep(0.05)
            self.assertEqual(engine.rings, {})
            self.assertIsNone(engine.audio._last_error)
            self.assertEqual(store.get_event(event["id"])["state"], "stopped")
        finally:
            engine.stop()
            store.close()


if __name__ == "__main__":
    unittest.main()


class AudioDeviceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="unzzz-audio-device-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_hw_device_is_plug_converted(self) -> None:
        audio = Audio(self.tmp, command=None)
        audio.mode = "auto"
        audio.players = {"aplay": "/usr/bin/aplay"}
        audio.set_device("alsa:hw:CARD=Headphones,DEV=0")
        argv = audio.command_for(self.tmp / "beep.wav")
        self.assertIn("plughw:CARD=Headphones,DEV=0", argv)
        self.assertNotIn("hw:CARD=Headphones,DEV=0", argv)

        audio.players = {"mpv": "/usr/bin/mpv"}
        audio.set_device("alsa:hw:CARD=Headphones,DEV=0")
        argv = audio.command_for(self.tmp / "beep.wav")
        self.assertIn("--audio-device=alsa/plughw:CARD=Headphones,DEV=0", argv)

    def test_failed_player_reports_stderr(self) -> None:
        script = self.tmp / "bad-player.sh"
        script.write_text("#!/bin/sh\necho 'cannot open audio device' >&2\nexit 1\n")
        script.chmod(0o755)
        audio = Audio(self.tmp, command=str(script))
        ok, error = audio.test()
        self.assertFalse(ok)
        self.assertIn("cannot open audio device", error)
