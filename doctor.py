#!/usr/bin/env python3
"""Collect non-privileged launcher integration diagnostics without opening UI."""
import os
from pathlib import Path
import shutil
import subprocess


def probe(label, command):
    print(f"\n## {label}", flush=True)
    if not shutil.which(command[0]):
        print(f"Unavailable: {command[0]}")
        return
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        print((result.stdout + result.stderr).strip() or f"Exit status: {result.returncode}")
    except subprocess.TimeoutExpired:
        print("Timed out")


def main():
    probe("Hyprland version", ["hyprctl", "version"])
    probe("Configuration errors", ["hyprctl", "configerrors"])
    probe("Input devices and capabilities", ["hyprctl", "devices", "-j"])
    probe("Plugin registry", ["omarchy", "plugin", "list", "--json"])
    probe("Plugin status (expected open or closed)", ["omarchy-shell", "shell", "call", "okuma.dev_launchpad4omarchy", "status", ""])
    path = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "hypr/input.lua"
    print(f"\n## Gesture config: {path}")
    text = path.read_text() if path.is_file() else ""
    print("Managed bindings present:", "-- BEGIN OkumarchyLaunchpad managed gestures" in text)
    print("Launchpad plugin reference present:", "okuma.dev_launchpad4omarchy" in text)
    print("Inspect manually included files if bindings are stored elsewhere.")
    print("A real touchpad pinch test is required. Device presence alone does not prove pinch support.")
    print("Review output for device names and local paths before sharing.")


if __name__ == "__main__":
    main()
