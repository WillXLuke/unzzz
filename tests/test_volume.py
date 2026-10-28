"""System volume save/restore for alarms."""

from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from unzzz.db import Store
from unzzz.volume import VolumeController


class VolumeControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="unzzz-volume-"))
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.log = self.tmp / "calls.log"
        self.old_path = os.environ.get("PATH", "")
        self.store = Store(self.tmp / "db.sqlite3")

    def tearDown(self) -> None:
        os.environ["PATH"] = self.old_path
        self.store.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def fake_amixer(self) -> None:
        script = self.bin / "amixer"
        script.write_text(
            "#!/bin/sh\n"
            f'echo "$*" >> "{self.log}"\n'
            "case \"$*\" in\n"
            "  *sget*) echo 'Mono: Playback 40 [40%] [-30.00dB] [on]' ;;\n"
            "  *sset*) exit 0 ;;\n"
            "esac\n"
        )
        script.chmod(0o755)
        os.environ["PATH"] = f"{self.bin}{os.pathsep}{self.old_path}"

    def fake_pactl(self) -> None:
        script = self.bin / "pactl"
        script.write_text(
            "#!/bin/sh\n"
            f'echo "$*" >> "{self.log}"\n'
            "case \"$1\" in\n"
            "  get-sink-volume) echo 'Volume: front-left: 22937 / 35% / -30.00 dB' ;;\n"
            "  set-sink-volume) exit 0 ;;\n"
            "esac\n"
        )
        script.chmod(0o755)
        os.environ["PATH"] = f"{self.bin}{os.pathsep}{self.old_path}"

    def test_alsa_save_and_restore(self) -> None:
        self.fake_amixer()
        volume = VolumeController("alsa:plughw:CARD=Test,DEV=0", target=80, store=self.store)
        self.assertEqual(volume.current(force=True), (40, None))
        self.assertTrue(volume.begin(1))
        self.assertEqual(self.store.get_setting("volume_saved"), "40")
        volume.end(1)
        self.assertFalse(self.store.get_setting("volume_saved"))
        calls = self.log.read_text()
        self.assertIn("sset Master 80%", calls)
        self.assertIn("sset Master 40%", calls)

    def test_pulse_save_and_restore(self) -> None:
        self.fake_pactl()
        volume = VolumeController("pulse:alsa_output.test", target=55, store=self.store)
        self.assertEqual(volume.current(force=True), (35, None))
        self.assertTrue(volume.begin(7))
        volume.end(7)
        calls = self.log.read_text()
        self.assertIn("set-sink-volume alsa_output.test 55%", calls)
        self.assertIn("set-sink-volume alsa_output.test 35%", calls)

    def test_only_last_event_restores(self) -> None:
        self.fake_amixer()
        volume = VolumeController("alsa:plughw:CARD=Test", target=70, store=self.store)
        self.assertTrue(volume.begin(1))
        self.assertTrue(volume.begin(2))
        volume.end(1)
        self.assertEqual(self.store.get_setting("volume_saved"), "40")
        volume.end(2)
        self.assertFalse(self.store.get_setting("volume_saved"))

    def test_persisted_restore_after_crash(self) -> None:
        self.fake_amixer()
        self.store.set_setting("volume_saved", "45")
        volume = VolumeController("alsa:plughw:CARD=Test", target=80, store=self.store)
        volume.restore_persisted()
        self.assertIn("sset Master 45%", self.log.read_text())
        self.assertFalse(self.store.get_setting("volume_saved"))

    def test_no_backend_is_unavailable(self) -> None:
        os.environ["PATH"] = str(self.bin)
        volume = VolumeController("", target=80, store=self.store)
        status = volume.status()
        self.assertFalse(status["available"])
        self.assertIsNone(status["current"])


if __name__ == "__main__":
    unittest.main()


class UsbMixerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="unzzz-usb-mixer-"))
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.log = self.tmp / "calls.log"
        self.old_path = os.environ.get("PATH", "")
        script = self.bin / "amixer"
        script.write_text(
            "#!/bin/sh\n"
            f'echo "$*" >> "{self.log}"\n'
            "case \"$*\" in\n"
            "  *controls*) printf \"numid=5,iface=MIXER,name='Playback Volume Playback Switch'\\nnumid=6,iface=MIXER,name='Playback Volume Playback Volume'\\n\" ;;\n"
            "  *sget*\"Playback Volume Playback Volume\"*) echo 'Mono: Playback 30 [30%] [-20.00dB] [on]' ;;\n"
            "  *) exit 0 ;;\n"
            "esac\n"
        )
        script.chmod(0o755)
        os.environ["PATH"] = f"{self.bin}{os.pathsep}{self.old_path}"

    def tearDown(self) -> None:
        os.environ["PATH"] = self.old_path
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_usb_playback_volume_control_is_discovered(self) -> None:
        volume = VolumeController("alsa:plughw:CARD=Pro0341,DEV=0", target=70)
        self.assertEqual(volume.current(force=True), (30, None))
        self.assertEqual(volume._control, "Playback Volume Playback Volume")
        ok, error = volume.set_percent(70)
        self.assertTrue(ok, error)
        calls = self.log.read_text()
        self.assertIn("sset Playback Volume Playback Volume 70%", calls)
        self.assertNotIn("sset Master", calls)
