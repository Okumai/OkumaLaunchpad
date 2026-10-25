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
        self.assertEqual(manifest["id"], "launchpad.okuma.dev")
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
