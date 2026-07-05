#!/usr/bin/env bash
# Reverts install-sddm-theme.sh: removes the theme override and the
# installed theme files. Needs root.
set -e

if [ "$(id -u)" -ne 0 ]; then
  echo "This needs root - removes files from /usr/share/sddm/themes and /etc/sddm.conf.d."
  echo "Run: sudo ./uninstall-sddm-theme.sh"
  exit 1
fi

THEME_NAME="css-wallpaper"
THEME_DIR="/usr/share/sddm/themes/$THEME_NAME"
CONF_FILE="/etc/sddm.conf.d/zz-css-wallpaper.conf"

rm -f "$CONF_FILE"
rm -rf "$THEME_DIR"

echo "Removed $CONF_FILE and $THEME_DIR."
echo "SDDM will fall back to whatever Current= is set in the remaining config"
echo "(e.g. /etc/sddm.conf.d/kde_settings.conf), typically 'breeze'."
