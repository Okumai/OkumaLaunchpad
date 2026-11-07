"""Exercise gesture callbacks and installer rollback without physical hardware."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gestures", ROOT / "setup-gestures.py")
gestures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gestures)


class WorkspaceSetupTests(unittest.TestCase):
    def test_fresh_repeat_update_and_remove_preserve_personal_settings(self):
        personal = '''-- Personal settings
hl.config({input={touchpad={drag_3fg=1}}})
hl.gesture({fingers=4, direction="up", action=function() end})
hl.gesture({fingers=3, direction="horizontal", action="workspace"})
'''
        pinch, _ = gestures.gesture_source()
        workspace, digest = gestures.workspace_source()
        configured = gestures.configure_workspaces(gestures.configure(personal, pinch), workspace)
        self.assertIn(personal, configured)
        self.assertIn(digest, configured)
        self.assertIn('action = "workspace"', configured)
        self.assertIn("workspace_swipe_create_new = true", configured)
        repeated = gestures.configure_workspaces(gestures.configure(configured, pinch), workspace)
        self.assertEqual(configured, repeated)
        removed = gestures.configure_workspaces(gestures.configure(configured, "", remove=True), "", remove=True)
        self.assertEqual(removed.strip(), personal.strip())

    def test_conflicting_horizontal_bindings_are_rejected_in_both_orders(self):
        for direction in ("horizontal", "horiz", "left", "right", "l", "r", "swipe"):
            for binding in (f'hl.gesture({{fingers=4, direction="{direction}", action="workspace"}})',
                            f"hl.gesture ( {{action=function() end, direction='{direction}', fingers=4}} )"):
                with self.subTest(binding=binding), self.assertRaisesRegex(ValueError, "four-finger"):
                    gestures.configure_workspaces(binding, "example")

    def test_comments_strings_pinch_vertical_and_modifiers_are_safe(self):
        source = '''-- hl.gesture({fingers=4, direction="horizontal"})
--[=[
hl.gesture({fingers=4, direction="swipe"})
]=]
local note = "-- hl.gesture({fingers=4, direction='left'})"
hl.gesture({fingers=4, direction="pinch", action={update=function(e) end}})
hl.gesture({fingers=4, direction="down", action=function() end})
'''
        self.assertIn(gestures.WORKSPACE_BEGIN, gestures.configure_workspaces(source, "example"))
        # Refuse rather than guess whether an existing modified/dynamic binding overlaps.
        for source in ('hl.gesture({fingers=n, direction="horizontal"})',
                       'hl.gesture({fingers=4, direction=dir})',
                       'hl.gesture({fingers=4, direction="left", mods="SUPER"})'):
            with self.assertRaises(ValueError):
                gestures.configure_workspaces(source, "example")

    def test_pinch_only_preserves_managed_workspaces(self):
        workspace, _ = gestures.workspace_source()
        original = gestures.configure_workspaces("-- Personal\n", workspace)
        source, _ = gestures.gesture_source(3)
        installed = gestures.configure(original, source)
        self.assertIn(workspace, installed)
        self.assertEqual(installed.count(gestures.WORKSPACE_BEGIN), 1)

    def test_workspace_lua_uses_native_continuous_action_without_input_overrides(self):
        lua = shutil.which("lua")
        if not lua:
            self.skipTest("Lua is required to exercise workspace integration")
        source, digest = gestures.workspace_source()
        harness = '''
local bindings, options = {}, nil
hl = {
  config = function(c) assert(c.input == nil); options = c.gestures end,
  gesture = function(g) table.insert(bindings, g) end,
}
'''
        assertions = f'''
assert(#bindings == 1)
assert(bindings[1].fingers == 4)
assert(bindings[1].direction == "horizontal")
assert(bindings[1].action == "workspace")
assert(options.workspace_swipe_use_r and options.workspace_swipe_create_new)
assert(_G.okuma_launchpad_workspaces == "{digest}")
'''
        subprocess.run([lua, "-"], input=harness + source + assertions, text=True, capture_output=True, check=True)

    def test_malformed_workspace_block_rejected(self):
        with self.assertRaises(ValueError):
            gestures.configure_workspaces(gestures.WORKSPACE_BEGIN, "example")


class GestureIntegrationTests(unittest.TestCase):
    def test_workspace_live_validation_and_rollback(self):
        for failure in (None, "configerrors", "marker", "option", "json"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "input.lua"
                original = "-- Personal settings\n"
                path.write_text(original)
                def check(*args):
                    if args[0] == "configerrors" and failure == "configerrors":
                        return "Gesture overshadowed by a previous gesture in included file"
                    if args[0] == "eval" and args[1].startswith("assert(_G.okuma_launchpad_workspaces") and failure == "marker":
                        raise RuntimeError("Workspace block not loaded")
                    if args[0] == "-j":
                        if failure == "json":
                            return "error"
                        return '{"bool":false}' if failure == "option" else '{"bool":true}'
                    return "ok" if args[0] == "eval" else ""
                with patch.object(sys, "argv", ["setup-gestures.py", "install", "--workspaces", "--config", str(path)]), patch.object(gestures, "preflight"), patch.object(gestures, "checked_hyprctl", side_effect=check) as calls, patch.object(gestures.subprocess, "run"), patch.object(gestures.shutil, "which", return_value="hyprctl"):
                    if failure:
                        with self.assertRaisesRegex(SystemExit, "original config restored"):
                            gestures.main()
                        self.assertEqual(path.read_text(), original)
                    else:
                        gestures.main()
                        gestures.main()
                        self.assertEqual(path.read_text().count(gestures.WORKSPACE_BEGIN), 1)
                        self.assertTrue(any(c.args[0] == "-j" for c in calls.call_args_list))
                        with patch.object(sys, "argv", ["setup-gestures.py", "remove", "--config", str(path)]):
                            gestures.main()
                        self.assertNotIn(gestures.WORKSPACE_BEGIN, path.read_text())

    def test_unloaded_file_rolls_back_and_repeat_still_validates(self):
        for installed in (False, True):
            with self.subTest(installed=installed), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "not-loaded.lua"
                source, _ = gestures.gesture_source()
                original = gestures.configure("-- Personal settings\n", source) if installed else "-- Personal settings\n"
                path.write_text(original)
                def check(*args):
                    if args[0] == "eval" and args[1].startswith("assert(_G."):
                        raise RuntimeError("Managed gesture file was not loaded")
                    return ""
                with patch.object(sys, "argv", ["setup-gestures.py", "install", "--config", str(path)]), patch.object(gestures, "preflight"), patch.object(gestures, "checked_hyprctl", side_effect=check), patch.object(gestures.subprocess, "run"), patch.object(gestures.shutil, "which", return_value="hyprctl"):
                    with self.assertRaisesRegex(SystemExit, "original config restored"):
                        gestures.main()
                self.assertEqual(path.read_text(), original)

    def test_callbacks_fire_once_and_never_on_release(self):
        lua = shutil.which("lua")
        if not lua:
            self.skipTest("Lua is required to exercise native gesture callbacks")
        source, _ = gestures.gesture_source()
        harness = '''
local bindings, commands = {}, {}
hl = {
  layer_rule = function(_) end,
  gesture = function(g) bindings[g.fingers] = g.action end,
  exec_cmd = function(c) table.insert(commands, c) end,
}
'''
        assertions = '''
local four, three = bindings[4], bindings[3]
four.start({scale=1}); four.update({scale=0.95})
assert(#commands == 0)
four.update({scale=0.89}); four.update({scale=1.2}); four.finish({scale=1.2})
assert(#commands == 1 and commands[1]:find("summon", 1, true))
four.start({scale=1.11}); four.update({scale=0.8}); four.finish({})
assert(#commands == 2 and commands[2]:find("hide", 1, true))
three.start({scale=0.8}); three.update({scale=0.7}); three.finish({})
assert(#commands == 2)
three.start({scale=1.12}); three.update({scale=1.3}); three.finish({})
assert(#commands == 3 and commands[3]:find("hide", 1, true))
'''
        subprocess.run([lua, "-"], input=harness + source + assertions, text=True, capture_output=True, check=True)


if __name__ == "__main__":
    unittest.main()
