"""Localisation assets and default data locations."""

from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from unzzz import __main__ as cli

ASSETS = Path(__file__).resolve().parents[1] / "unzzz" / "assets"


class I18nAssetTests(unittest.TestCase):
    def test_i18n_asset_has_all_languages(self) -> None:
        text = (ASSETS / "i18n.js").read_text()
        for marker in ('"zh"', '"ja"', '"fr"', '"de"', "unzzz.lang", "data-lang-select"):
            self.assertIn(marker, text)
        html = (ASSETS / "index.html").read_text()
        for native in ("中文", "日本語", "Français", "Deutsch"):
            self.assertIn(native, html)

    def test_every_page_loads_i18n(self) -> None:
        for name in ("index.html", "challenge.html", "alarm.html"):
            text = (ASSETS / name).read_text()
            self.assertIn('/i18n.js', text)
            self.assertLess(text.index('/i18n.js'), text.index('/app.js' if name == "index.html" else '/challenge.js' if name == "challenge.html" else '/alarm.js'))


class DefaultsTests(unittest.TestCase):
    def test_default_bind_and_port(self) -> None:
        env = {k: v for k, v in os.environ.items() if k not in {"UNZZZ_PORT", "UNZZZ_BIND"}}
        with mock.patch.dict(os.environ, env, clear=True):
            args = cli.build_parser().parse_args(["serve"])
            self.assertEqual(args.bind, "0.0.0.0")
            self.assertEqual(args.port, 8888)


class DataDirTests(unittest.TestCase):
    def test_env_override(self) -> None:
        with mock.patch.dict(os.environ, {"UNZZZ_DATA_DIR": "/srv/custom"}, clear=False):
            with mock.patch.object(cli.os, "geteuid", return_value=0):
                self.assertEqual(cli.default_data_dir(), Path("/srv/custom"))

    def test_system_root(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "UNZZZ_DATA_DIR"}
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch.object(cli.os, "geteuid", return_value=0):
                self.assertEqual(cli.default_data_dir(), Path("/var/lib/unzzz"))

    def test_private_mode_for_created_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "nested" / "unzzz"
            cli.ensure_data_dir(target)
            self.assertTrue(target.is_dir())
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o750)

    def test_xdg_user(self) -> None:
        env = {
            k: v for k, v in os.environ.items()
            if k not in {"UNZZZ_DATA_DIR", "XDG_DATA_HOME"}
        }
        env["HOME"] = "/home/alice"
        env["XDG_DATA_HOME"] = "/home/alice/.local/share"
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch.object(cli.os, "geteuid", return_value=1000):
                self.assertEqual(
                    cli.default_data_dir(),
                    Path("/home/alice/.local/share/unzzz"),
                )


if __name__ == "__main__":
    unittest.main()


class NewUIAssetTests(unittest.TestCase):
    def test_english_card_templates_present(self) -> None:
        text = (ASSETS / "i18n.js").read_text()
        for key in ("card.each", "card.count", "card.all", "card.music"):
            self.assertIn(f'"{key}"', text)
        self.assertIn('"card.each": " · {n} each"', text)

    def test_ordered_plan_and_new_challenge_controls(self) -> None:
        html = (ASSETS / "index.html").read_text()
        for marker in (
            "challenge-plan-list", "alarm-muted", "Pattern paint 6×6",
            "Pattern paint 9×9", "Button hold", "Typing test", "Roll dice",
        ):
            self.assertIn(marker, html)
        challenge = (ASSETS / "challenge.html").read_text()
        self.assertIn('id="back-link"', challenge)
        js = (ASSETS / "challenge.js").read_text()
        for marker in ("bindHold", "bindDice", "typing-phrase", "requestSubmit"):
            self.assertIn(marker, js)
        self.assertNotIn('style="grid-template-columns', js)
        self.assertIn("paint-size-${size}", js)
        css = (ASSETS / "style.css").read_text()
        self.assertIn(".paint-grid.paint-size-6", css)
        self.assertIn(".paint-grid.paint-size-9", css)
