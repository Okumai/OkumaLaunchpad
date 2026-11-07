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


class GestureIntegrationTests(unittest.TestCase):
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
