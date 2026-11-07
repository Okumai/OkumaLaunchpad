#!/usr/bin/env python3
"""Install opt-in user gesture bindings without changing packaged files."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
BEGIN = "-- BEGIN OkumarchyLaunchpad managed gestures"
END = "-- END OkumarchyLaunchpad managed gestures"
WORKSPACE_BEGIN = "-- BEGIN OkumarchyLaunchpad managed workspaces"
WORKSPACE_END = "-- END OkumarchyLaunchpad managed workspaces"


def strip_block(text, begin, end):
    if text.count(begin) != text.count(end) or text.count(begin) > 1:
        raise ValueError("Malformed managed block; restore or repair the file first")
    if begin in text:
        start = text.index(begin)
        finish = text.index(end) + len(end)
        if finish < start:
            raise ValueError("Invalid managed block order")
        text = text[:start].rstrip("\n") + "\n\n" + text[finish:].lstrip("\n")
    return text


# Tokenize rather than splitting on '--': Lua strings and long comments can contain it.
LUA_TOKENS = re.compile(r'''--\[(=*)\[.*?\]\1\]|--[^\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\[(=*)\[.*?\]\2\]|[A-Za-z_][A-Za-z_0-9]*|\d+|[^\s]''', re.S)


def active_lua(text):
    return " ".join(m.group() for m in LUA_TOKENS.finditer(text) if not m.group().startswith("--"))


def workspace_source():
    source = (ROOT / "examples/workspaces.lua").read_text()
    digest = hashlib.sha256(source.encode()).hexdigest()
    return source.rstrip() + f'\n_G.okuma_launchpad_workspaces = "{digest}"\n', digest


def configure_workspaces(text, source, remove=False):
    text = strip_block(text, WORKSPACE_BEGIN, WORKSPACE_END)
    if remove:
        return text
    tokens = [m.group() for m in LUA_TOKENS.finditer(text) if not m.group().startswith("--")]
    # Conservative preflight for the selected file. Runtime validation also catches
    # conflicts in included files; arbitrary/dynamic Lua still needs manual review.
    for index in range(len(tokens) - 4):
        if tokens[index:index + 5] != ["hl", ".", "gesture", "(", "{"]:
            continue
        depth, fields = 1, {}
        for pos in range(index + 5, len(tokens)):
            token = tokens[pos]
            if token == "{":
                depth += 1
            elif token == "}":
                depth -= 1
                if depth == 0:
                    break
            if depth == 1 and token in {"fingers", "direction"} and tokens[pos + 1:pos + 2] == ["="]:
                # Only trust a single literal followed by a field delimiter.
                if tokens[pos + 3:pos + 4] in ([","], [";"], ["}"]):
                    fields[token] = tokens[pos + 2]
        fingers = fields.get("fingers", "")
        if fingers.isdecimal() and int(fingers) != 4:
            continue
        direction = fields.get("direction", "")
        literal = len(direction) >= 2 and direction[0] in "\"'" and direction[-1] == direction[0]
        if not literal or direction[1:-1].lower() in {"horizontal", "horiz", "left", "l", "right", "r", "swipe"}:
            raise ValueError("Existing four-finger horizontal/swipe binding detected. Review it and migrate it manually, or use --no-workspaces to preserve it")
    return text.rstrip() + "\n\n" + WORKSPACE_BEGIN + "\n" + source.rstrip() + "\n" + WORKSPACE_END + "\n"


def configure(text, source, remove=False):
    text = strip_block(text, BEGIN, END)
    if remove:
        return text
    # Never silently override another launcher or existing pinch bindings.
    active = active_lua(strip_block(text, WORKSPACE_BEGIN, WORKSPACE_END))
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
    parser.add_argument("--workspaces", action="store_true", help="Also install native four-finger horizontal workspace swipes (pinch-only by default)")
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
        workspace, workspace_digest = workspace_source()
        if args.workspaces or args.action == "remove":
            updated = configure_workspaces(updated, workspace, args.action == "remove")
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
            checked_hyprctl("eval", "_G.okuma_launchpad_gestures = nil; _G.okuma_launchpad_workspaces = nil")
        checked_hyprctl("reload")
        errors = checked_hyprctl("configerrors")
        if errors:
            raise RuntimeError(errors)
        if args.action == "install":
            checked_hyprctl("eval", f'assert(_G.okuma_launchpad_gestures == "{digest}", "Managed gesture file was not loaded; include the selected config in hyprland.lua")')
            if args.workspaces:
                checked_hyprctl("eval", f'assert(_G.okuma_launchpad_workspaces == "{workspace_digest}", "Managed workspace bindings missing or not loaded")')
                for option in ("workspace_swipe_use_r", "workspace_swipe_create_new"):
                    value = json.loads(checked_hyprctl("-j", "getoption", f"gestures:{option}"))
                    if not isinstance(value, dict) or value.get("bool") is not True:
                        raise RuntimeError(f"Workspace swipe option overridden: {option}")
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        path.write_text(original)
        try:
            subprocess.run(["hyprctl", "reload"], check=False, timeout=10)
            subprocess.run(["hyprctl", "configerrors"], check=False, timeout=10)
        except (OSError, subprocess.SubprocessError):
            pass
        raise SystemExit(f"Validation failed; original config restored. {error}")
    print("Hyprland configuration validated" + ("; managed gestures confirmed loaded." if args.action == "install" else "."))
    if args.action == "install":
        print("Test a physical pinch and, if selected, a four-finger horizontal workspace swipe on the desktop.")
        print("--fingers 3 changes pinch only, not workspace swipes; three-finger dragging can conflict with three-finger pinch.")


if __name__ == "__main__":
    main()
