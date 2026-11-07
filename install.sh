#!/usr/bin/env bash
# Explicit installation entry point; never executed by the plugin lifecycle.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec python3 "$root/install.py" "$@"
