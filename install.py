#!/usr/bin/env python3
"""Install and enable OkumarchyLaunchpad, including gestures by default."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
PLUGIN_ID = "okuma.dev_launchpad4omarchy"


def run(*args):
    subprocess.run(list(map(str, args)), check=True, timeout=60)


def verify_plugin():
    for _ in range(20):
        result = subprocess.run(["omarchy-shell", "shell", "call", PLUGIN_ID, "status", ""],
                                capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip() in {"open", "closed"}:
            return
        time.sleep(0.25)
    raise RuntimeError("Plugin did not respond. Run doctor.py and inspect shell logs; no shell restart was forced")


def install(args):
    for executable in ("omarchy", "omarchy-shell", "hyprctl"):
        if not shutil.which(executable):
            raise RuntimeError(f"Required command not found: {executable}")
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    target = config_home / "omarchy/plugins" / PLUGIN_ID
    source_manifest = json.loads((ROOT / "manifest.json").read_text())
    if source_manifest.get("id") != PLUGIN_ID:
        raise RuntimeError("Unexpected source plugin identity")
    if not args.no_gestures:
        config = args.config or config_home / "hypr/input.lua"
        if not config.is_file():
            raise RuntimeError(f"Expected an existing loaded user config: {config}")
        # Check conflicts before enabling any code or changing the installation.
        import importlib.util
        spec = importlib.util.spec_from_file_location("gesture_setup", ROOT / "setup-gestures.py")
        setup = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(setup)
        setup.configure(config.read_text(), (ROOT / "examples/hyprland.lua").read_text())
    print(f"Plugin target: {target}", flush=True)
    print("Gestures: " + ("skipped" if args.no_gestures else f"enabled by default; backup and edit {config}"), flush=True)
    print("Plugins run unsandboxed. Existing installations are reused, not overwritten.", flush=True)
    if not args.yes:
        if not sys.stdin.isatty():
            raise RuntimeError("Interactive confirmation required; review the source and pass --yes for unattended installation")
        if input("Continue? [y/N] ").strip().lower() not in {"y", "yes"}:
            raise RuntimeError("Installation cancelled")
    run("omarchy", "plugin", "validate", ROOT)
    if target.exists() or target.is_symlink():
        if not target.is_dir() or json.loads((target / "manifest.json").read_text()).get("id") != PLUGIN_ID:
            raise RuntimeError(f"Invalid existing target: {target}")
        run("omarchy", "plugin", "validate", target)
        print("Reusing installed plugin. To update its code, use omarchy plugin update first.", flush=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", "*.bak", "*.bak.*"))
        print("Installed local snapshot. This copy is not git-managed; see README for managed installations.", flush=True)
    run("omarchy-shell", "shell", "rescanPlugins")
    run("omarchy", "plugin", "enable", PLUGIN_ID)
    verify_plugin()
    if not args.no_gestures:
        run(sys.executable, ROOT / "setup-gestures.py", "install", "--config", config)
    print("Installation complete: plugin responds" + ("; gestures skipped." if args.no_gestures else "; gesture configuration validated."))
    print("Test a physical four-finger pinch. Hardware pinch support is not guaranteed by configuration validation.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-gestures", action="store_true", help="Do not change Hyprland gesture configuration")
    parser.add_argument("--yes", action="store_true", help="Confirm installation without an interactive prompt")
    parser.add_argument("--config", type=Path, help="Loaded user input.lua path for gesture setup")
    args = parser.parse_args()
    try:
        install(args)
    except (RuntimeError, ValueError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Installation failed: {error}\nCompleted steps are retained; fix the error and rerun. Gesture validation failures restore the original config.\n")


if __name__ == "__main__":
    main()
