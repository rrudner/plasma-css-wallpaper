#!/usr/bin/env bash
set -e

PLUGIN_ID="io.github.rrudner.plasmacsswallpaper"
INSTALL_DIR="$HOME/.local/share/plasma/wallpapers/$PLUGIN_ID"

echo "Installing CSS Wallpaper..."
mkdir -p "$INSTALL_DIR"
cp -r metadata.json contents "$INSTALL_DIR/"
echo "Done. Installed to $INSTALL_DIR"
echo ""
echo "Right-click your desktop → Configure Desktop and Wallpaper → CSS Wallpaper"
echo ""
echo "To add animations, drop .html files into:"
echo "  $INSTALL_DIR/contents/html/"
