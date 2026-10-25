#!/usr/bin/env python3
"""Resolve installed app/device icons without Qt's session-scoped theme cache."""
import json
import os
from pathlib import Path


def build_index():
    home = Path.home()
    data_home = Path(os.environ.get("XDG_DATA_HOME") or home / ".local/share")
    data_dirs = [Path(p) for p in os.environ.get(
        "XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":") if p]
    roots = [home / ".icons", data_home / "icons"]
    roots += [p / "icons" for p in data_dirs]
    roots += [data_home / "pixmaps"] + [p / "pixmaps" for p in data_dirs]
    candidates = {}
    for priority, root in enumerate(dict.fromkeys(roots)):
        for directory, dirs, files in os.walk(root):
            dirs.sort()
            parts = set(Path(directory).relative_to(root).parts)
            # Do not confuse app names with toolbar/action icons (e.g. zoom).
            if root.name != "pixmaps" and not parts.intersection({"apps", "devices"}):
                continue
            for filename in sorted(files):
                path = Path(directory) / filename
                ext = path.suffix.lower()
                if ext not in {".svg", ".png", ".xpm"} or not path.is_file():
                    continue
                size = max((int(p.split("x")[0]) for p in parts
                            if p.split("x")[0].isdigit()), default=0)
                rank = (priority, {".svg": 0, ".png": 1, ".xpm": 2}[ext], -size, str(path))
                key = path.stem
                if key not in candidates or rank < candidates[key][0]:
                    candidates[key] = (rank, path.absolute().as_uri())
    return {key: value[1] for key, value in candidates.items()}


if __name__ == "__main__":
    print(json.dumps(build_index(), ensure_ascii=True))
