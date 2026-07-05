#!/usr/bin/env bash
set -e

PLUGIN_ID="io.github.rrudner.plasmacsswallpaper"
INSTALL_DIR="$HOME/.local/share/plasma/wallpapers/$PLUGIN_ID"

echo "Removing CSS Wallpaper..."
rm -rf "$INSTALL_DIR"
echo "Done."
