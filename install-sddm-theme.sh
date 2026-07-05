#!/usr/bin/env bash
# Installs the sddm-theme/ directory as a real SDDM login-screen theme
# and sets it as active. Needs root (writes to /usr/share and /etc).
set -e

if [ "$(id -u)" -ne 0 ]; then
  echo "This needs root - writes to /usr/share/sddm/themes and /etc/sddm.conf.d."
  echo "Run: sudo ./install-sddm-theme.sh"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THEME_NAME="css-wallpaper"
THEME_DIR="/usr/share/sddm/themes/$THEME_NAME"
CONF_FILE="/etc/sddm.conf.d/zz-css-wallpaper.conf"

echo "Installing SDDM theme '$THEME_NAME' to $THEME_DIR ..."
mkdir -p "$THEME_DIR"
cp -r "$SCRIPT_DIR/sddm-theme/." "$THEME_DIR/"

# contents/html/ is the only copy of the animations kept in the repo -
# theme.conf's webBackground= points at html/<file> relative to the theme
# dir, so they're copied in here rather than duplicated in sddm-theme/.
# Re-run this script after adding a new .html file to pick it up here too.
mkdir -p "$THEME_DIR/html"
cp "$SCRIPT_DIR"/contents/html/*.html "$THEME_DIR/html/"

echo "Setting it as the active theme via $CONF_FILE ..."
echo "(named to sort after kde_settings.conf, so it wins the Current= key)"
cat > "$CONF_FILE" <<EOF
[Theme]
Current=$THEME_NAME
EOF

echo
echo "Done. Log out or reboot to see it on the real login screen."
echo
echo "To preview any changes safely first, without logging out:"
echo "  sddm-greeter-qt6 --test-mode --theme $THEME_DIR"
echo
echo "Animation/FPS/render-resolution are set in:"
echo "  $THEME_DIR/theme.conf  (webBackground=, webFps=, webScale=)"
echo
echo "To revert to the previous theme, run uninstall-sddm-theme.sh."
