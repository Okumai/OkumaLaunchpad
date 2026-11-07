#!/usr/bin/env python3
"""Install reversible user-owned Dock adapters without modifying packaged Omarchy files."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
LAUNCHPAD = "okuma.dev_launchpad4omarchy"
DOCK = "okuma.dev_dock4omarchy"
ADAPTER = "okuma.dev_launchpad_dock_bridge"
OWNER = "okumaLaunchpadDockAdapter"
DESKTOP = "okuma-launchpad.desktop"
OPEN = "  function openApps() {\n    appGrid.open()\n  }"
APPS = "    function apps(): void { appGrid.toggle() }"
BRIDGE = '''  // Managed Launchpad entry point; the stock dock's other behavior is unchanged.
  function openApps() {
    if (!launchpadActivation.running) launchpadActivation.running = true
  }

  Process {
    id: launchpadActivation
    command: ["python3", decodeURIComponent(Qt.resolvedUrl("activate-launchpad.py").toString().replace(/^file:\\/\\//, "")), "toggle"]
  }'''
BRIDGE_APPS = '''    function apps(): void { root.openApps() }
    function launchpadIntegration(): string { return "okuma-launchpad-v1" }'''


def locations():
    home = Path.home()
    config = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
    data = Path(os.environ.get("XDG_DATA_HOME") or home / ".local/share")
    state = Path(os.environ.get("XDG_STATE_HOME") or home / ".local/state") / "okuma-launchpad"
    return config, data, state


def command(*args):
    result = subprocess.run(list(map(str, args)), capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip() or f"Command failed: {args[0]}")
    return result.stdout.strip()


def patch_dock(source):
    if source.count(OPEN) != 1 or source.count(APPS) != 1:
        raise ValueError("Unsupported built-in Dock source. No files changed; review its new entry points or use --no-dock-integration")
    return source.replace(OPEN, BRIDGE).replace(APPS, BRIDGE_APPS)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def desktop_entry(helper):
    def quote(value):
        value = str(value)
        if any(c in value for c in "\n\r\x00"):
            raise ValueError("Unsupported newline/NUL in desktop entry path")
        value = value.replace("%", "%%")
        value = "".join("\\" + c if c in '\\"`$' else c for c in value)
        # Desktop Entry general escaping is decoded before Exec quoting.
        return '"' + value.replace("\\", "\\\\") + '"'
    return ("[Desktop Entry]\nType=Application\nName=Okuma Launchpad\n"
            "Comment=Open the OkumarchyLaunchpad application grid\n"
            f"Exec={quote(sys.executable)} {quote(helper)} toggle\n"
            "Icon=view-app-grid-symbolic\nTerminal=false\nCategories=Utility;\nStartupNotify=false\n")


def load_state(path):
    return json.loads(path.read_text()) if path.exists() else None


def owned_files(adapter):
    return {str(p.relative_to(adapter)): digest(p) for p in adapter.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}


def prepare(target):
    config, data, state_dir = locations()
    path = config / "omarchy/shell.json"
    adapter = config / "omarchy/plugins" / ADAPTER
    state_path = state_dir / "dock-integration.json"
    desktop = data / "applications" / DESKTOP
    state = load_state(state_path)
    if path.is_symlink() or state_path.is_symlink():
        raise ValueError("Refusing symlink shell config or integration state")
    settings = json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(settings, dict) or not isinstance(settings.get("plugins", []), list) or not isinstance(settings.get("disabledPlugins", []), list):
        raise ValueError("Invalid shell.json plugin configuration")
    catalog = json.loads(command("omarchy", "plugin", "catalog"))
    source = next((p for p in catalog if p.get("id") == "omarchy.dock" and p.get("firstParty")), None)
    if not source:
        raise ValueError("Built-in omarchy.dock not found; use --no-dock-integration for an unsupported shell")
    for plugin in catalog:
        if plugin.get("id") == ADAPTER:
            continue
        metadata = json.loads(Path(plugin["manifestPath"]).read_text()).get("omarchy", {})
        if metadata.get("clonedFrom") == "omarchy.dock":
            if any(p.get("id") == plugin["id"] for p in settings.get("plugins", [])) and plugin["id"] not in settings.get("disabledPlugins", []):
                raise ValueError("An existing custom Dock clone is enabled; integrate it manually or use --no-dock-integration")
    source_dir = Path(source["sourceDir"])
    manifest = json.loads(Path(source["manifestPath"]).read_text())
    if manifest.get("entryPoints") != {"service": "Dock.qml"}:
        raise ValueError("Unsupported built-in Dock manifest; no automatic adapter is available")
    patched = patch_dock((source_dir / "Dock.qml").read_text())
    if not state and any(p.get("id") == ADAPTER for p in settings.get("plugins", [])):
        raise ValueError("Dock adapter config exists without ownership state; review before installation")
    if adapter.is_symlink() or (adapter.exists() and (not state or owned_files(adapter) != state["adapterFiles"])):
        raise ValueError("Dock adapter exists without matching ownership or has local edits; refusing to overwrite")
    if desktop.is_symlink() or (desktop.exists() and (not state or digest(desktop) != state["desktopHash"])):
        raise ValueError("Launchpad desktop entry exists without matching ownership or has local edits")
    helper = Path(target) / "activate-launchpad.py"
    entry = desktop_entry(helper)
    return config, state_dir, path, adapter, desktop, state, settings, source_dir, manifest, patched, entry


def integrate_config(settings, previous=None):
    settings = json.loads(json.dumps(settings))
    state = previous or {
        "builtinDisabled": "omarchy.dock" in settings.get("disabledPlugins", []),
        "dockPreference": [],
    }
    plugins = settings.setdefault("plugins", [])
    if not any(p.get("id") == ADAPTER for p in plugins):
        plugins.append({"id": ADAPTER})
    disabled = settings.setdefault("disabledPlugins", [])
    if state["builtinDisabled"]:
        if ADAPTER not in disabled:
            disabled.append(ADAPTER)
    elif ADAPTER in disabled:
        disabled.remove(ADAPTER)
    if "omarchy.dock" not in disabled:
        disabled.append("omarchy.dock")
    for plugin in plugins:
        if plugin.get("id") == DOCK:
            if plugin.get("launcherPlugin", "auto") not in {"auto", LAUNCHPAD}:
                print("Preserving explicit OkumaDock launcher preference; select Launchpad manually if desired.", flush=True)
                continue
            if not state["dockPreference"]:
                state["dockPreference"] = ["launcherPlugin" in plugin, plugin.get("launcherPlugin")]
            plugin["launcherPlugin"] = LAUNCHPAD
    return settings, state


def restore_config(settings, state):
    settings = json.loads(json.dumps(settings))
    settings["plugins"] = [p for p in settings.get("plugins", []) if p.get("id") != ADAPTER]
    settings["disabledPlugins"] = [p for p in settings.get("disabledPlugins", []) if p != ADAPTER]
    if not state["builtinDisabled"]:
        settings["disabledPlugins"] = [p for p in settings["disabledPlugins"] if p != "omarchy.dock"]
    preference = state["dockPreference"]
    if preference:
        for plugin in settings["plugins"]:
            if plugin.get("id") == DOCK and plugin.get("launcherPlugin") == LAUNCHPAD:
                if preference[0]:
                    plugin["launcherPlugin"] = preference[1]
                else:
                    plugin.pop("launcherPlugin", None)
    return settings


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".okuma.tmp")
    if path.is_symlink() or temp.is_symlink():
        raise ValueError(f"Refusing symlink config/state: {path}")
    temp.write_text(json.dumps(value, indent=2) + "\n")
    os.replace(temp, path)


def install(target):
    config, state_dir, path, adapter, desktop, state, settings, source_dir, manifest, patched, entry = prepare(target)
    backup = state_dir / ("dock-backup-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    backup.mkdir(parents=True)
    if path.exists():
        shutil.copy2(path, backup / "shell.json")
    if adapter.exists():
        shutil.copytree(adapter, backup / "adapter")
    if desktop.exists():
        shutil.copy2(desktop, backup / DESKTOP)
    state_path = state_dir / "dock-integration.json"
    if state_path.exists():
        shutil.copy2(state_path, backup / "state.json")
    settings, state = integrate_config(settings, state)
    # Build a complete private copy before publishing it. Never edit /usr/share.
    stage = backup / "staged-adapter"
    shutil.copytree(source_dir, stage)
    manifest.update(id=ADAPTER, name="Omarchy Dock with Okuma Launchpad")
    manifest["omarchy"] = dict(manifest.get("omarchy", {}), clonedFrom="omarchy.dock")
    manifest[OWNER] = 1
    save_json(stage / "manifest.json", manifest)
    (stage / "Dock.qml").write_text(patched)
    shutil.copy2(ROOT / "activate-launchpad.py", stage / "activate-launchpad.py")
    command("omarchy", "plugin", "validate", stage)
    try:
        if adapter.exists():
            shutil.rmtree(adapter)
        shutil.copytree(stage, adapter)
        desktop.parent.mkdir(parents=True, exist_ok=True)
        desktop.write_text(entry)
        state.update(adapterFiles=owned_files(adapter), desktopHash=digest(desktop), backup=str(backup))
        save_json(state_path, state)
        save_json(path, settings)
    except (OSError, ValueError):
        # Publication failures restore the prior files. Late live validation below
        # retains the installation with a visible error and a supported remove path.
        if adapter.exists():
            shutil.rmtree(adapter)
        if (backup / "adapter").exists():
            shutil.copytree(backup / "adapter", adapter)
        for destination, saved in ((desktop, backup / DESKTOP), (state_path, backup / "state.json"), (path, backup / "shell.json")):
            if saved.exists():
                shutil.copy2(saved, destination)
            else:
                destination.unlink(missing_ok=True)
        raise
    print(f"Dock integration installed; backup: {backup}", flush=True)
    try:
        command("omarchy-shell", "shell", "rescanPlugins")
    except (RuntimeError, subprocess.SubprocessError):
        print("Rescan IPC interrupted; verifying the live adapter rather than assuming failure.", flush=True)
    if ADAPTER in settings["disabledPlugins"]:
        print("Adapter installed but kept disabled because the original Dock was disabled; desktop entry and eligible OkumaDock routing installed.")
        return
    for _ in range(40):
        try:
            if command("omarchy-shell", "omarchy.dock", "launchpadIntegration") == "okuma-launchpad-v1":
                print("Built-in Dock adapter confirmed live; eligible OkumaDock Applications entries select Launchpad.")
                return
        except (RuntimeError, subprocess.SubprocessError):
            pass
        time.sleep(0.25)
    raise RuntimeError("Dock integration saved but the live adapter is not responding. Run doctor.py; if QML is cached, deliberately restart the shell. No automatic restart was forced")


def remove():
    config, data, state_dir = locations()
    state_path = state_dir / "dock-integration.json"
    state = load_state(state_path)
    if not state:
        print("No managed Dock integration to remove")
        return
    adapter = config / "omarchy/plugins" / ADAPTER
    desktop = data / "applications" / DESKTOP
    if adapter.is_symlink() or (adapter.exists() and owned_files(adapter) != state["adapterFiles"]):
        raise ValueError("Dock adapter has local edits; back it up and review before removal")
    if desktop.is_symlink() or (desktop.exists() and digest(desktop) != state["desktopHash"]):
        raise ValueError("Desktop entry has local edits; review before removal")
    path = config / "omarchy/shell.json"
    settings = json.loads(path.read_text())
    backup = state_dir / ("dock-remove-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".json")
    shutil.copy2(path, backup)
    save_json(path, restore_config(settings, state))
    if adapter.exists():
        shutil.rmtree(adapter)
    desktop.unlink(missing_ok=True)
    state_path.unlink()
    try:
        command("omarchy-shell", "shell", "rescanPlugins")
    except (RuntimeError, subprocess.SubprocessError):
        print("Removal saved; rescan IPC interrupted. Check the live Dock and rescan after the shell settles.")
    print(f"Removed managed Dock integration; unrelated settings preserved. Backup: {backup}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["install", "remove", "check"])
    parser.add_argument("--target", type=Path, help="Persistent installed Launchpad directory")
    args = parser.parse_args()
    target = args.target or locations()[0] / "omarchy/plugins" / LAUNCHPAD
    try:
        if args.action == "remove":
            remove()
        elif args.action == "check":
            prepare(target)
            print("Dock integration preflight passed")
        else:
            if not (target / "activate-launchpad.py").is_file():
                raise ValueError("Installed Launchpad activation helper is missing; update its source first")
            install(target)
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Dock integration failed: {error}\n")


if __name__ == "__main__":
    main()
