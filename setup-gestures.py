#!/usr/bin/env python3
"""Install opt-in user gesture bindings without changing packaged files."""
import argparse
from datetime import datetime
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
BEGIN = "-- BEGIN OkumarchyLaunchpad managed gestures"
END = "-- END OkumarchyLaunchpad managed gestures"


def configure(text, source, remove=False):
    if text.count(BEGIN) != text.count(END) or text.count(BEGIN) > 1:
        raise ValueError("Malformed managed block; restore or repair the file first")
    if BEGIN in text:
        start = text.index(BEGIN)
        finish = text.index(END) + len(END)
        if finish < start:
            raise ValueError("Invalid managed block order")
        text = text[:start] + text[finish:]
    if remove:
        return text
    # Never silently override the original standalone launcher or other pinches.
    active = "\n".join(line.split("--", 1)[0] for line in text.splitlines())
    if "launchpad" in active.lower() or "pinch" in active.lower():
        raise ValueError("Existing Launchpad/pinch configuration detected. Remove duplicate bindings manually before installing")
    return text.rstrip() + "\n\n" + BEGIN + "\n" + source.rstrip() + "\n" + END + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["install", "remove"])
    parser.add_argument("--config", type=Path, help="User input.lua path (must be loaded by Hyprland)")
    parser.add_argument("--no-reload", action="store_true", help="Edit only; validate manually afterwards")
    args = parser.parse_args()
    path = args.config or Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "hypr/input.lua"
    if not path.is_file():
        parser.error(f"Expected an existing loaded user config: {path}")
    if not args.no_reload and not shutil.which("hyprctl"):
        parser.error("hyprctl is unavailable; use --no-reload only for an offline configuration")
    try:
        original = path.read_text()
        updated = configure(original, (ROOT / "examples/hyprland.lua").read_text(), args.action == "remove")
    except ValueError as error:
        parser.error(str(error))
    if updated == original:
        print("No changes required")
        return
    backup = path.with_name(path.name + ".bak.launchpad." + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    shutil.copy2(path, backup)
    path.write_text(updated)
    print(f"Updated {path}; backup: {backup}")
    if args.no_reload:
        print("Run hyprctl reload and hyprctl configerrors before using gestures")
        return
    reload_result = subprocess.run(["hyprctl", "reload"], capture_output=True, text=True)
    errors = subprocess.run(["hyprctl", "configerrors"], capture_output=True, text=True)
    if reload_result.returncode or errors.returncode or errors.stdout.strip():
        path.write_text(original)
        subprocess.run(["hyprctl", "reload"], check=False)
        subprocess.run(["hyprctl", "configerrors"], check=False)
        raise SystemExit("Validation failed; original config restored. " + reload_result.stderr + errors.stdout + errors.stderr)
    print("Hyprland configuration validated. Confirm that the plugin is enabled and test a real pinch.")


if __name__ == "__main__":
    main()
