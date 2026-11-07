#!/usr/bin/env python3
"""Install opt-in user gesture bindings without changing packaged files."""
import argparse
from datetime import datetime
import hashlib
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
    # Never silently override another launcher or existing pinch bindings.
    active = "\n".join(line.split("--", 1)[0] for line in text.splitlines())
    if "launchpad" in active.lower() or "pinch" in active.lower():
        raise ValueError("Existing Launchpad/pinch configuration detected. Remove duplicate bindings manually before installing")
    return text.rstrip() + "\n\n" + BEGIN + "\n" + source.rstrip() + "\n" + END + "\n"


def gesture_source(fingers=4):
    source = (ROOT / "examples/hyprland.lua").read_text()
    if fingers == 3:
        source = source.split("-- Read the scale rather than", 1)[0]
        source = source.replace("fingers = 4,", "fingers = 3,")
    digest = hashlib.sha256(source.encode()).hexdigest()
    # Validation must prove this exact managed block ran, not just that Lua parsed.
    return source.rstrip() + f'\n_G.okuma_launchpad_gestures = "{digest}"\n', digest


def checked_hyprctl(*args):
    result = subprocess.run(["hyprctl", *args], capture_output=True, text=True, timeout=10)
    output = (result.stdout + result.stderr).strip()
    # hyprctl eval can exit zero while returning an error in stdout.
    if result.returncode or (args[0] == "eval" and output != "ok"):
        raise RuntimeError(output or "hyprctl failed")
    return output


def preflight():
    if checked_hyprctl("configerrors"):
        raise RuntimeError("Resolve existing Hyprland configuration errors before installation")
    checked_hyprctl("eval", 'assert(type(hl.gesture) == "function", "Hyprland Lua gesture API unavailable")')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["install", "remove"])
    parser.add_argument("--config", type=Path, help="User input.lua path (must be loaded by Hyprland)")
    parser.add_argument("--no-reload", action="store_true", help="Edit only; validate manually afterwards")
    parser.add_argument("--fingers", type=int, choices=[3, 4], default=4,
                        help="Opening pinch finger count; use 3 only if the device cannot pinch with 4")
    args = parser.parse_args()
    path = args.config or Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "hypr/input.lua"
    if not path.is_file():
        parser.error(f"Expected an existing loaded user config: {path}")
    if not args.no_reload and not shutil.which("hyprctl"):
        parser.error("hyprctl is unavailable; use --no-reload only for an offline configuration")
    try:
        original = path.read_text()
        source, digest = gesture_source(args.fingers)
        updated = configure(original, source, args.action == "remove")
        if not args.no_reload:
            preflight()
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    if updated != original:
        backup = path.with_name(path.name + ".bak.launchpad." + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
        shutil.copy2(path, backup)
        path.write_text(updated)
        print(f"Updated {path}; backup: {backup}")
    else:
        print("No file changes required; checking the live configuration")
    if args.no_reload:
        print("Run hyprctl reload and hyprctl configerrors before using gestures")
        return
    try:
        if args.action == "install":
            checked_hyprctl("eval", "_G.okuma_launchpad_gestures = nil")
        checked_hyprctl("reload")
        errors = checked_hyprctl("configerrors")
        if errors:
            raise RuntimeError(errors)
        if args.action == "install":
            checked_hyprctl("eval", f'assert(_G.okuma_launchpad_gestures == "{digest}", "Managed gesture file was not loaded; include the selected config in hyprland.lua")')
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        path.write_text(original)
        try:
            subprocess.run(["hyprctl", "reload"], check=False, timeout=10)
            subprocess.run(["hyprctl", "configerrors"], check=False, timeout=10)
        except (OSError, subprocess.SubprocessError):
            pass
        raise SystemExit(f"Validation failed; original config restored. {error}")
    print("Hyprland configuration validated" + ("; managed gestures confirmed loaded." if args.action == "install" else "."))
    print("Test a physical pinch. If 4-finger pinch is unsupported, rerun with --fingers 3 (may conflict with three-finger dragging).")


if __name__ == "__main__":
    main()
