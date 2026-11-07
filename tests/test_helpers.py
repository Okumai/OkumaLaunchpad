"""Portable regression checks without a running desktop."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("icons", ROOT / "index-icons.py")
icons = importlib.util.module_from_spec(spec)
spec.loader.exec_module(icons)


class ProjectTests(unittest.TestCase):
    def test_identity(self):
        manifest = json.loads((ROOT / "manifest.json").read_text())
        example = json.loads((ROOT / "examples/plugin-settings.json").read_text())
        self.assertEqual(manifest["id"], "okuma.dev_launchpad4omarchy")
        self.assertEqual(manifest["author"], "\u014cKUMA")
        self.assertEqual(example["id"], manifest["id"])
        self.assertTrue(manifest["keepLoaded"])
        self.assertTrue((ROOT / manifest["entryPoints"]["panel"]).is_file())
        self.assertIn('pluginId: "' + manifest["id"] + '"', (ROOT / "Launchpad.qml").read_text())

    def test_english_project_text(self):
        for path in ROOT.rglob("*"):
            if not path.is_file() or any(p in {".git", "__pycache__"} for p in path.relative_to(ROOT).parts):
                continue
            with self.subTest(path=path):
                path.read_text(encoding="utf-8").replace("\u014cKUMA", "OKUMA").encode("ascii")


class InstallerTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("installer", ROOT / "install.py")
        self.installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.installer)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config_home = Path(self.temp.name)
        env = patch.dict(os.environ, XDG_CONFIG_HOME=str(self.config_home))
        env.start()
        self.addCleanup(env.stop)
        preflight = patch.object(self.installer.subprocess, "run")
        self.preflight_run = preflight.start()
        self.preflight_run.return_value.returncode = 0
        self.preflight_run.return_value.stdout = ""
        self.preflight_run.return_value.stderr = ""
        self.addCleanup(preflight.stop)
        registry = patch.object(self.installer, "wait_for_registry")
        registry.start()
        self.addCleanup(registry.stop)

    def args(self, no_gestures=False):
        import argparse
        return argparse.Namespace(no_gestures=no_gestures, yes=True, config=None, fingers=4)

    def test_install_default_gestures_and_repeat(self):
        config = self.config_home / "hypr/input.lua"
        config.parent.mkdir()
        config.write_text("-- User settings\n")
        self.preflight_run.side_effect = lambda cmd, **kw: __import__('subprocess').CompletedProcess(cmd, 0, "ok" if cmd[1] == "eval" else "", "")
        with patch.object(self.installer.shutil, "which", return_value="available"), patch.object(self.installer, "run") as run, patch.object(self.installer, "verify_plugin"):
            self.installer.install(self.args())
            target = self.config_home / "omarchy/plugins/okuma.dev_launchpad4omarchy"
            self.assertTrue((target / "manifest.json").is_file())
            self.assertFalse((target / ".git").exists())
            self.assertTrue(any("setup-gestures.py" in str(c) for c in run.call_args_list))
            sentinel = target / "preserve.txt"
            sentinel.write_text("Keep local changes")
            self.installer.install(self.args())
            self.assertTrue(sentinel.exists())

    def test_skip_gestures_needs_no_input_config(self):
        with patch.object(self.installer.shutil, "which", return_value="available"), patch.object(self.installer, "run") as run, patch.object(self.installer, "verify_plugin"):
            self.installer.install(self.args(no_gestures=True))
            self.assertFalse(any("setup-gestures.py" in str(c) for c in run.call_args_list))

    def test_symlink_target_is_refused_before_changes(self):
        outside = self.config_home / "outside"
        outside.mkdir()
        target = self.config_home / "omarchy/plugins/okuma.dev_launchpad4omarchy"
        target.parent.mkdir(parents=True)
        target.symlink_to(outside, target_is_directory=True)
        with patch.object(self.installer.shutil, "which", return_value="available"), patch.object(self.installer, "run") as run:
            with self.assertRaisesRegex(RuntimeError, "symlink"):
                self.installer.install(self.args(no_gestures=True))
            run.assert_not_called()
        self.assertEqual(list(outside.iterdir()), [])

    def test_conflict_prevents_installation(self):
        config = self.config_home / "hypr/input.lua"
        config.parent.mkdir()
        config.write_text('hl.gesture({direction="pinch"})')
        with patch.object(self.installer.shutil, "which", return_value="available"), patch.object(self.installer, "run") as run:
            with self.assertRaises(ValueError):
                self.installer.install(self.args())
            run.assert_not_called()
            self.assertFalse((self.config_home / "omarchy/plugins").exists())


class InstallerReadinessTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("installer_readiness", ROOT / "install.py")
        self.installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.installer)

    def test_registry_waits_for_asynchronous_scan(self):
        import subprocess
        replies = [subprocess.CompletedProcess([], 0, '[]', ''),
                   subprocess.CompletedProcess([], 0, json.dumps([{"id": self.installer.PLUGIN_ID}]), '')]
        with patch.object(self.installer.subprocess, "run", side_effect=replies) as run, patch.object(self.installer.time, "sleep") as sleep:
            self.installer.wait_for_registry()
            self.assertEqual(run.call_count, 2)
            sleep.assert_called_once()

    def test_unknown_status_is_not_a_successful_load(self):
        import subprocess
        with patch.object(self.installer.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "unknown", "")), patch.object(self.installer.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "did not respond"):
                self.installer.verify_plugin()


class GestureSetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("setup", ROOT / "setup-gestures.py")
        cls.setup = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.setup)

    def test_install_update_remove(self):
        original = "-- Personal settings\nhl.config({})\n"
        installed = self.setup.configure(original, "-- Example\nhl.gesture({})")
        self.assertIn(self.setup.BEGIN, installed)
        self.assertEqual(self.setup.configure(installed, "-- Example\nhl.gesture({})"), installed)
        removed = self.setup.configure(installed, "", remove=True)
        self.assertNotIn(self.setup.BEGIN, removed)
        self.assertIn("hl.config({})", removed)

    def test_finger_profiles_have_a_single_open_binding_and_marker(self):
        for fingers in (3, 4):
            source, digest = self.setup.gesture_source(fingers)
            self.assertIn(f'fingers = {fingers},', source)
            self.assertEqual(source.count("shell summon"), 1)
            self.assertIn(digest, source)
        source, _ = self.setup.gesture_source(3)
        self.assertEqual(source.count("hl.gesture({"), 1)

    def test_eval_zero_exit_with_error_is_rejected(self):
        import subprocess
        with patch.object(self.setup.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "error: not loaded", "")):
            with self.assertRaisesRegex(RuntimeError, "not loaded"):
                self.setup.checked_hyprctl("eval", "assert(false)")

    def test_duplicates_and_malformed_blocks(self):
        with self.assertRaises(ValueError):
            self.setup.configure('hl.gesture({direction="pinch"})', "example")
        with self.assertRaises(ValueError):
            self.setup.configure(self.setup.BEGIN, "example")


class IconTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.local = self.home / "data"
        self.system = self.home / "system"
        self.env = patch.dict(os.environ, {"XDG_DATA_HOME": str(self.local), "XDG_DATA_DIRS": str(self.system)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.home_patch = patch.object(Path, "home", return_value=self.home)
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)

    def icon(self, base, relative):
        path = base / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("test")
        return path.absolute().as_uri()

    def test_empty_directories(self):
        self.assertEqual(icons.build_index(), {})

    def test_user_precedence(self):
        local = self.icon(self.local, "icons/hicolor/32x32/apps/example.png")
        self.icon(self.system, "icons/hicolor/scalable/apps/example.svg")
        self.assertEqual(icons.build_index()["example"], local)

    def test_svg_then_larger_png(self):
        svg = self.icon(self.system, "icons/hicolor/scalable/apps/vector.svg")
        self.icon(self.system, "icons/hicolor/256x256/apps/vector.png")
        self.icon(self.system, "icons/hicolor/16x16/apps/raster.png")
        large = self.icon(self.system, "icons/hicolor/256x256/apps/raster.png")
        result = icons.build_index()
        self.assertEqual(result["vector"], svg)
        self.assertEqual(result["raster"], large)

    def test_context_and_pixmaps(self):
        self.icon(self.system, "icons/theme/scalable/actions/zoom.svg")
        device = self.icon(self.system, "icons/theme/scalable/devices/printer.svg")
        pixmap = self.icon(self.system, "pixmaps/legacy.xpm")
        result = icons.build_index()
        self.assertNotIn("zoom", result)
        self.assertEqual(result["printer"], device)
        self.assertEqual(result["legacy"], pixmap)

    def test_uri_encoding_and_broken_links(self):
        uri = self.icon(self.local, "icons/hicolor/scalable/apps/space # icon.svg")
        broken = self.local / "icons/hicolor/scalable/apps/broken.svg"
        broken.symlink_to("absent.svg")
        result = icons.build_index()
        self.assertEqual(result["space # icon"], uri)
        self.assertIn("%23", uri)
        self.assertNotIn("broken", result)


if __name__ == "__main__":
    unittest.main()
