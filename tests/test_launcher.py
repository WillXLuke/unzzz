"""The launcher must work through the packaged /usr/bin symlink."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from unzzz import __version__

ROOT = Path(__file__).resolve().parents[1]


class LauncherTests(unittest.TestCase):
    def test_symlinked_launcher_finds_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            link = Path(tmp) / "unzzz"
            link.symlink_to(ROOT / "bin" / "unzzz")
            proc = subprocess.run(
                [str(link), "--version"],
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": ""},
                timeout=15,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn(f"unzzz {__version__}", proc.stdout)


if __name__ == "__main__":
    unittest.main()
