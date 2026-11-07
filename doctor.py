#!/usr/bin/env python3
"""Collect non-privileged launcher integration diagnostics without opening UI."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent


def probe(label, command):
    print(f"\n## {label}", flush=True)
    if not shutil.which(command[0]):
        print(f"Unavailable: {command[0]}")
        return ""
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        output = (result.stdout + result.stderr).strip()
        print(output or f"Exit status: {result.returncode}")
        return result.stdout.strip() if result.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired) as error:
        print(error)
        return ""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="Same config path passed to the installer")
    parser.add_argument("--fingers", type=int, choices=[3, 4], default=4)
    args = parser.parse_args()
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    probe("Hyprland version", ["hyprctl", "version"])
    probe("Configuration errors", ["hyprctl", "configerrors"])
    probe("Lua gesture API", ["hyprctl", "eval", 'assert(type(hl.gesture) == "function", "Lua gestures unavailable")'])
    probe("Input devices (presence does NOT prove pinch capability)", ["hyprctl", "devices", "-j"])
    # udev classification requires neither root nor access to raw input events.
    for event in sorted(Path("/sys/class/input").glob("event*")):
        if shutil.which("udevadm"):
            result = subprocess.run(["udevadm", "info", "--query=property", f"--path={event}"],
                                    capture_output=True, text=True, timeout=5)
            if "ID_INPUT_TOUCHPAD=1" in result.stdout:
                print(f"\nTouchpad: {event.resolve()}")
                print("\n".join(line for line in result.stdout.splitlines()
                                if line.startswith(("ID_INPUT", "ID_MODEL=", "ID_VENDOR="))))
    probe("Plugin registry", ["omarchy", "plugin", "list", "--json"])
    status = probe("Launchpad status (expected open or closed)", ["omarchy-shell", "shell", "call", "okuma.dev_launchpad4omarchy", "status", ""])
    if status not in {"open", "closed"}:
        print("FAIL: Launchpad plugin is not responding. Fix installation/loading before investigating touchpad hardware.")
    dock = probe("OkumarchyDock status", ["omarchy-shell", "shell", "call", "okuma.dev_dock4omarchy", "status", ""])
    try:
        if "launcherPlugin" not in json.loads(dock):
            print("Dock predates automatic Launchpad integration; update OkumarchyDock too.")
    except (ValueError, TypeError):
        print("Dock is not responding or is not installed.")
    probe("Built-in Dock Launchpad adapter (expected okuma-launchpad-v1)",
          ["omarchy-shell", "omarchy.dock", "launchpadIntegration"])
    data_home = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    desktop = data_home / "applications/okuma-launchpad.desktop"
    print("Launchpad desktop entry:", desktop, "present:", desktop.is_file())
    print("For other docks, pin this entry or configure the installed activate-launchpad.py helper; icon names alone do not select a launcher.")
    path = args.config or config_home / "hypr/input.lua"
    print(f"\n## Gesture config: {path}")
    text = path.read_text() if path.is_file() else ""
    spec = importlib.util.spec_from_file_location("gestures", ROOT / "setup-gestures.py")
    setup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(setup)
    _, digest = setup.gesture_source(args.fingers)
    print("Managed pinch bindings present:", setup.BEGIN in text)
    probe("Exact managed pinch block loaded (expected ok)", ["hyprctl", "eval",
          f'assert(_G.okuma_launchpad_gestures == "{digest}", "Managed gesture block missing, outdated or not loaded")'])
    print("\n## Four-finger horizontal workspace integration")
    workspace, workspace_digest = setup.workspace_source()
    managed_workspaces = setup.WORKSPACE_BEGIN in text
    print("Managed workspace bindings present:", managed_workspaces)
    if managed_workspaces:
        probe("Exact workspace block loaded (expected ok)", ["hyprctl", "eval",
              f'assert(_G.okuma_launchpad_workspaces == "{workspace_digest}", "Workspace block missing, outdated or not loaded")'])
    else:
        print("No managed workspace swipe installed. Pinch support alone does NOT enable workspace switching.")
        print("For a fresh config: setup-gestures.py install --workspaces; review existing bindings first.")
    try:
        setup.configure_workspaces(text, workspace)
    except ValueError as error:
        print("Manual workspace binding/conflict:", error)
        print("Do not add a duplicate. Inspect the existing action, finger count, modifiers and includes.")
    for candidate in sorted((config_home / "hypr").rglob("*.lua")):
        try:
            active = setup.active_lua(candidate.read_text())
            if "gesture" in active and any(word in active for word in ('"workspace"', "'workspace'", '"horizontal"', "'horizontal'", '"swipe"', "'swipe'")):
                print(f"Workspace/swipe config candidate (not proof of loading): {candidate}")
        except OSError:
            pass
    for option in ("workspace_swipe_use_r", "workspace_swipe_create_new", "workspace_swipe_distance",
                   "workspace_swipe_cancel_ratio", "workspace_swipe_invert"):
        probe(f"Live gestures:{option}", ["hyprctl", "getoption", f"gestures:{option}"])
    probe("Existing workspaces (one workspace with create_new=false can look unresponsive)", ["hyprctl", "workspaces", "-j"])
    probe("Focused workspace", ["hyprctl", "activeworkspace", "-j"])
    autostart = config_home / "hypr/autostart.lua"
    autostart_text = autostart.read_text() if autostart.is_file() else ""
    if "/.local/bin/launchpad" in text or 'qs -c launchpad' in autostart_text:
        print("LEGACY: old independent Launchpad integration detected; it is not included in this plugin.")
        print("Back up and remove old pinch bindings/autostart before installing managed bindings; do not run both implementations.")
    elif (config_home / "quickshell/launchpad/shell.qml").is_file():
        print("Legacy standalone files remain on disk; their presence alone does not mean that implementation is active.")
    shell_path = config_home / "omarchy/shell.json"
    try:
        config = json.loads(shell_path.read_text())
        for plugin in config.get("plugins", []):
            if plugin.get("id") == "okuma.dev_dock4omarchy":
                for pin in plugin.get("pinned", []):
                    command = pin.get("command", [])
                    if command and Path(command[0]).name == "launchpad":
                        print(f"Legacy Dock pin: {pin.get('key')}; updated Dock routes this to public plugin IPC.")
    except (OSError, ValueError, TypeError):
        pass
    print("\nA real pinch test is required. Four-finger support varies by touchpad/driver.")
    print("If the plugin opens via IPC but not pinch: check loaded bindings, conflicts in includes, libinput classification and typing suppression.")
    print("Try --fingers 3 only if required; three-finger dragging can take precedence. No raw input permissions are required.")
    print("Review output for device names and local paths before sharing.")


if __name__ == "__main__":
    main()
