#!/usr/bin/env bash
# Shared entry point; paths never depend on the caller's working directory.
SCRIPT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
wallpaper_command() {
  python3 "$SCRIPT_ROOT/scripts/wallpaper.py" "$@"
}
