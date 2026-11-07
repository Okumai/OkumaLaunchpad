#!/usr/bin/env python3
"""Strict Launchpad activation for Dock adapters and desktop entries; never opens another launcher."""
import argparse
import subprocess
import sys
import time

PLUGIN = "okuma.dev_launchpad4omarchy"


def ipc(*args):
    result = subprocess.run(["omarchy-shell", "shell", *args], capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Omarchy shell IPC failed")
    return result.stdout.strip()


def activate(action="toggle"):
    before = ipc("call", PLUGIN, "status", "")
    if before not in {"open", "closed"}:
        raise RuntimeError("Launchpad is not loaded/enabled. Run its installer or doctor.py; no system launcher was opened")
    expected = "closed" if action == "hide" or (action == "toggle" and before == "open") else "open"
    if before == expected:
        return PLUGIN
    if expected == "open":
        if ipc("summon", PLUGIN, "{}") != "ok":
            raise RuntimeError("Launchpad could not be summoned")
    else:
        ipc("hide", PLUGIN)
    for _ in range(20):
        if ipc("call", PLUGIN, "status", "") == expected:
            return PLUGIN
        time.sleep(0.1)
    raise RuntimeError("Launchpad did not reach the requested state; inspect plugin logs")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", choices=["toggle", "show", "hide"], default="toggle")
    args = parser.parse_args()
    try:
        print(activate(args.action))
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        message = f"Cannot activate Launchpad: {error}"
        print(message, file=sys.stderr)
        try:
            subprocess.run(["notify-send", "OkumarchyLaunchpad", message], check=False, timeout=5)
        except (OSError, subprocess.SubprocessError):
            pass
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
