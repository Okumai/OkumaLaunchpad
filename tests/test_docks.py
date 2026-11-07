"""Portable Dock adapter, ownership and strict activation regression checks."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


docks = load("docks", "setup-docks.py")
activation = load("activation", "activate-launchpad.py")


class ActivationTests(unittest.TestCase):
    def test_open_close_and_idempotent_show(self):
        for before, action, expected in (("closed", "toggle", "open"), ("open", "toggle", "closed"), ("closed", "show", "open")):
            with self.subTest(action=action, before=before), patch.object(activation, "ipc", side_effect=[before, "ok", expected]) as ipc:
                self.assertEqual(activation.activate(action), activation.PLUGIN)
                self.assertIn(ipc.call_args_list[1].args[0], {"summon", "hide"})
        with patch.object(activation, "ipc", return_value="open") as ipc:
            activation.activate("show")
            self.assertEqual(ipc.call_count, 1)

    def test_unknown_transport_and_noop_never_fall_back(self):
        for reply in ("unknown", "error", ""):
            with patch.object(activation, "ipc", return_value=reply) as ipc:
                with self.assertRaises(RuntimeError):
                    activation.activate()
                self.assertEqual(ipc.call_count, 1)
        with patch.object(activation, "ipc", return_value="closed"), patch.object(activation.time, "sleep"):
            with self.assertRaises(RuntimeError):
                activation.activate()


class DockConfigTests(unittest.TestCase):
    def test_patch_only_apps_entries_and_reject_unknown_source(self):
        original = "// existing\n" + docks.OPEN + "\n" + docks.APPS + "\n// unchanged"
        patched = docks.patch_dock(original)
        self.assertIn(docks.BRIDGE, patched)
        self.assertIn(docks.BRIDGE_APPS, patched)
        self.assertTrue(patched.endswith("// unchanged"))
        for source in ("unknown", original + docks.OPEN):
            with self.assertRaises(ValueError):
                docks.patch_dock(source)

    def test_config_roundtrip_preserves_preferences_pins_and_other_plugins(self):
        for disabled in ([], ["omarchy.dock", "other"]):
            for preference in ({}, {"launcherPlugin": "auto"}):
                original = {"bar": {"id": "custom.bar"}, "dock": {"pinned": ["browser"]},
                            "disabledPlugins": disabled, "plugins": [{"id": docks.DOCK, "pinned": [{"key": "browser"}], **preference}, {"id": "other.plugin"}]}
                integrated, state = docks.integrate_config(original)
                repeated, state = docks.integrate_config(integrated, state)
                self.assertEqual(integrated, repeated)
                self.assertEqual(integrated["plugins"][0]["launcherPlugin"], docks.LAUNCHPAD)
                self.assertEqual(docks.restore_config(integrated, state), original)
                integrated["plugins"][0]["launcherPlugin"] = "new.preference"
                self.assertEqual(docks.restore_config(integrated, state)["plugins"][0]["launcherPlugin"], "new.preference")

    def test_explicit_alternative_launcher_preference_is_preserved(self):
        original = {"plugins": [{"id": docks.DOCK, "launcherPlugin": "omarchy.menu"}]}
        integrated, state = docks.integrate_config(original)
        self.assertEqual(integrated["plugins"][0], original["plugins"][0])
        self.assertEqual(state["dockPreference"], [])

    def test_desktop_entry_quoting(self):
        entry = docks.desktop_entry(Path('/home/user with space/a%$"`\\/activate-launchpad.py'))
        self.assertIn("%%", entry)
        self.assertNotIn("omarchy.menu", entry)
        if shutil.which("desktop-file-validate"):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / docks.DESKTOP
                path.write_text(entry)
                subprocess.run(["desktop-file-validate", path], check=True)
        with self.assertRaises(ValueError):
            docks.desktop_entry(Path("bad\npath"))


class DockInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.config = self.base / "config"
        self.data = self.base / "data"
        self.state = self.base / "state"
        env = patch.dict(os.environ, XDG_CONFIG_HOME=str(self.config), XDG_DATA_HOME=str(self.data), XDG_STATE_HOME=str(self.state))
        env.start()
        self.addCleanup(env.stop)
        self.stock = self.base / "packaged-dock"
        self.stock.mkdir()
        self.manifest = {"schemaVersion": 1, "id": "omarchy.dock", "name": "Dock", "version": "1.0.0", "author": "Omarchy", "kinds": ["service"], "entryPoints": {"service": "Dock.qml"}}
        (self.stock / "manifest.json").write_text(json.dumps(self.manifest))
        (self.stock / "Dock.qml").write_text(docks.OPEN + "\n" + docks.APPS)
        self.original = {"plugins": [{"id": docks.DOCK, "pinned": ["keep"]}], "bar": {"id": "my.bar"}}
        self.shell = self.config / "omarchy/shell.json"
        self.shell.parent.mkdir(parents=True)
        self.shell.write_text(json.dumps(self.original))
        self.target = self.config / "omarchy/plugins" / docks.LAUNCHPAD
        self.target.mkdir(parents=True)
        shutil.copy2(ROOT / "activate-launchpad.py", self.target / "activate-launchpad.py")
        self.catalog = [{"id": "omarchy.dock", "firstParty": True, "sourceDir": str(self.stock), "manifestPath": str(self.stock / "manifest.json")}]
        def command(*args):
            if args == ("omarchy", "plugin", "catalog"):
                return json.dumps(self.catalog)
            if args[-1] == "launchpadIntegration":
                return "okuma-launchpad-v1"
            return "ok"
        mock = patch.object(docks, "command", side_effect=command)
        self.command = mock.start()
        self.addCleanup(mock.stop)

    def test_install_repeat_remove_and_keep_packaged_source_untouched(self):
        stock = (self.stock / "Dock.qml").read_text()
        docks.install(self.target)
        docks.install(self.target)
        self.assertEqual((self.stock / "Dock.qml").read_text(), stock)
        self.assertTrue((self.data / "applications" / docks.DESKTOP).is_file())
        modified = json.loads(self.shell.read_text())
        modified["newSetting"] = "preserved"
        self.shell.write_text(json.dumps(modified))
        docks.remove()
        restored = json.loads(self.shell.read_text())
        self.assertEqual(restored.pop("newSetting"), "preserved")
        restored.pop("disabledPlugins")
        self.assertEqual(restored, self.original)
        self.assertFalse((self.data / "applications" / docks.DESKTOP).exists())

    def test_disabled_stock_dock_stays_disabled(self):
        original = dict(self.original, disabledPlugins=["omarchy.dock"])
        self.shell.write_text(json.dumps(original))
        docks.install(self.target)
        installed = json.loads(self.shell.read_text())
        self.assertIn(docks.ADAPTER, installed["disabledPlugins"])
        self.assertFalse(any(c.args[-1] == "launchpadIntegration" for c in self.command.call_args_list))
        docks.remove()
        self.assertEqual(json.loads(self.shell.read_text()), original)

    def test_live_validation_failure_is_visible_and_removable(self):
        original = self.command.side_effect
        def missing(*args):
            if args[-1] == "launchpadIntegration":
                return "unknown"
            return original(*args)
        self.command.side_effect = missing
        with patch.object(docks.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "live adapter is not responding"):
                docks.install(self.target)
        self.assertTrue((self.state / "okuma-launchpad/dock-integration.json").is_file())
        docks.remove()
        self.assertFalse((self.data / "applications" / docks.DESKTOP).exists())

    def test_existing_or_modified_adapter_is_not_overwritten(self):
        docks.install(self.target)
        adapter = self.config / "omarchy/plugins" / docks.ADAPTER
        (adapter / "Dock.qml").write_text("personal edits")
        for action in (lambda: docks.install(self.target), docks.remove):
            with self.assertRaisesRegex(ValueError, "local edits"):
                action()
        self.assertEqual((adapter / "Dock.qml").read_text(), "personal edits")

    def test_publication_failure_rolls_back(self):
        docks.install(self.target)
        before = self.shell.read_bytes()
        adapter = self.config / "omarchy/plugins" / docks.ADAPTER
        files = docks.owned_files(adapter)
        state_path = self.state / "okuma-launchpad/dock-integration.json"
        before_state = state_path.read_bytes()
        save = docks.save_json
        def fail_shell(path, value):
            if path == self.shell:
                raise OSError("test write failure")
            save(path, value)
        with patch.object(docks, "save_json", side_effect=fail_shell):
            with self.assertRaisesRegex(OSError, "test write failure"):
                docks.install(self.target)
        self.assertEqual(self.shell.read_bytes(), before)
        self.assertEqual(docks.owned_files(adapter), files)
        self.assertEqual(state_path.read_bytes(), before_state)

    def test_interrupted_rescan_still_verifies_live_adapter(self):
        original = self.command.side_effect
        def interrupted(*args):
            if args[-1] == "rescanPlugins":
                raise RuntimeError("interrupted")
            return original(*args)
        self.command.side_effect = interrupted
        docks.install(self.target)
        self.assertTrue((self.data / "applications" / docks.DESKTOP).exists())

    def test_enabled_custom_clone_is_refused(self):
        clone = self.base / "clone.json"
        clone.write_text(json.dumps({"omarchy": {"clonedFrom": "omarchy.dock"}}))
        self.catalog.append({"id": "custom.dock", "manifestPath": str(clone)})
        self.shell.write_text(json.dumps({"plugins": [{"id": "custom.dock"}]}))
        with self.assertRaisesRegex(ValueError, "custom Dock clone"):
            docks.prepare(self.target)


if __name__ == "__main__":
    unittest.main()
