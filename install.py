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


def wait_for_registry():
    # rescanPlugins starts asynchronous discovery; returning from IPC is not completion.
    for _ in range(40):
        result = subprocess.run(["omarchy", "plugin", "list", "--json"],
                                capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            try:
                if any(plugin.get("id") == PLUGIN_ID for plugin in json.loads(result.stdout)):
                    return
            except (ValueError, TypeError, AttributeError):
                pass
        time.sleep(0.25)
    raise RuntimeError("Plugin discovery did not complete after rescan; inspect shell logs")


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
    if target.is_symlink():
        raise RuntimeError(f"Refusing symlink installation target: {target}")
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
        source, _ = setup.gesture_source(args.fingers)
        updated = setup.configure(config.read_text(), source)
        if not args.no_workspaces:
            workspace, _ = setup.workspace_source()
            setup.configure_workspaces(updated, workspace)
        setup.preflight()
    if not args.no_dock_integration:
        if target.exists() and not (target / "activate-launchpad.py").is_file():
            raise RuntimeError("Installed plugin predates Dock integration; update its source first (existing targets are not overwritten)")
        run(sys.executable, ROOT / "setup-docks.py", "check", "--target", target)
    print(f"Plugin target: {target}", flush=True)
    print("Gestures: " + ("skipped" if args.no_gestures else f"enabled by default; backup and edit {config}"), flush=True)
    if not args.no_gestures:
        print("Workspace swipes: " + ("preserve existing bindings" if args.no_workspaces else "install native four-finger horizontal swipe; allow empty numeric neighbors"), flush=True)
    print("Dock integration: " + ("skipped" if args.no_dock_integration else "user-owned built-in Dock adapter, Launchpad for eligible OkumaDock pins, desktop entry"), flush=True)
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
    try:
        run("omarchy-shell", "shell", "rescanPlugins")
    except subprocess.SubprocessError:
        print("Rescan IPC was interrupted; waiting for the live registry.", flush=True)
    wait_for_registry()
    try:
        run("omarchy", "plugin", "enable", PLUGIN_ID)
    except subprocess.SubprocessError:
        # Loading a panel can transiently interrupt the enable IPC reply after the
        # setting was saved. Only accept that case if the plugin really responds.
        verify_plugin()
        print("Enable IPC was interrupted, but the live plugin is responding.", flush=True)
    else:
        verify_plugin()
    if not args.no_gestures:
        options = [] if args.no_workspaces else ["--workspaces"]
        run(sys.executable, ROOT / "setup-gestures.py", "install", "--config", config, "--fingers", args.fingers, *options)
    if not args.no_dock_integration:
        run(sys.executable, ROOT / "setup-docks.py", "install", "--target", target)
    print("Installation complete: plugin responds" + ("; gestures skipped." if args.no_gestures else "; gesture configuration validated."))
    if not args.no_dock_integration:
        print("Managed Dock entries require Launchpad; explicit alternative preferences/custom pins are preserved.")
        print("Update old OkumaDock installations too. Other docks can pin Okuma Launchpad or run activate-launchpad.py.")
    print("Test physical pinch and workspace swipes on each device. Configuration validation does not prove hardware support.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-gestures", action="store_true", help="Do not change Hyprland gesture configuration")
    parser.add_argument("--no-workspaces", action="store_true", help="Install pinch only; preserve existing workspace bindings and settings")
    parser.add_argument("--no-dock-integration", action="store_true", help="Do not install Dock adapters, desktop entry or launcher preference")
    parser.add_argument("--yes", action="store_true", help="Confirm installation without an interactive prompt")
    parser.add_argument("--config", type=Path, help="Loaded user input.lua path for gesture setup")
    parser.add_argument("--fingers", type=int, choices=[3, 4], default=4, help="Opening pinch finger count (default: 4)")
    args = parser.parse_args()
    try:
        install(args)
    except (RuntimeError, ValueError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Installation failed: {error}\nCompleted steps are retained; fix the error and rerun. Gesture validation failures restore the original config.\n")


if __name__ == "__main__":
    main()
