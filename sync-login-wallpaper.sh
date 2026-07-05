#!/usr/bin/env bash
# Copies the currently-configured desktop wallpaper animation (file,
# render resolution, FPS) - set the normal way via right-click desktop
# -> Configure Desktop and Wallpaper -> CSS Wallpaper - to both the
# lock screen and the SDDM login theme, so those don't need to be
# edited by hand every time you change something on the desktop.
#
# Usage:
#   ./sync-login-wallpaper.sh            # uses the first desktop found
#   ./sync-login-wallpaper.sh <containment-id>   # pick a specific screen
set -e

PLUGIN_ID="com.user.csswallpaper"
SDDM_THEME_DIR="/usr/share/sddm/themes/css-wallpaper"

# This only needs to write to /usr/share for the SDDM part, and calls
# sudo itself for just that - don't run the whole script with sudo, or
# $HOME becomes /root and it can't find your desktop's config at all.
# (If you did run it with sudo anyway, recover gracefully by using the
# original user's home instead of root's.)
if [ "$(id -u)" -eq 0 ] && [ -n "$SUDO_USER" ]; then
  REAL_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
  AS_USER=(sudo -u "$SUDO_USER")
else
  REAL_HOME="$HOME"
  AS_USER=()
fi

APPLETS_FILE="$REAL_HOME/.config/plasma-org.kde.plasma.desktop-appletsrc"

if [ ! -f "$APPLETS_FILE" ]; then
  echo "Can't find $APPLETS_FILE"
  exit 1
fi

CONTAINMENT="$1"
if [ -z "$CONTAINMENT" ]; then
  CONTAINMENT=$(grep -oP "(?<=\[Containments\]\[)\d+(?=\]\[Wallpaper\]\[$PLUGIN_ID\]\[General\])" "$APPLETS_FILE" | head -1)
fi

if [ -z "$CONTAINMENT" ]; then
  echo "No desktop is currently using $PLUGIN_ID as its wallpaper."
  echo "Set it first: right-click desktop -> Configure Desktop and Wallpaper -> CSS Wallpaper."
  exit 1
fi

HTML_FILE=$("${AS_USER[@]}" kreadconfig6 --file "$APPLETS_FILE" --group Containments --group "$CONTAINMENT" --group Wallpaper --group "$PLUGIN_ID" --group General --key HtmlFile)
RENDER_SCALE=$("${AS_USER[@]}" kreadconfig6 --file "$APPLETS_FILE" --group Containments --group "$CONTAINMENT" --group Wallpaper --group "$PLUGIN_ID" --group General --key RenderScale)
FRAME_RATE=$("${AS_USER[@]}" kreadconfig6 --file "$APPLETS_FILE" --group Containments --group "$CONTAINMENT" --group Wallpaper --group "$PLUGIN_ID" --group General --key FrameRate)

echo "Read from desktop wallpaper (containment $CONTAINMENT):"
echo "  HtmlFile=$HTML_FILE  RenderScale=$RENDER_SCALE  FrameRate=$FRAME_RATE"
echo

# --- Lock screen: per-user config, no root needed ---
LOCK_FILE="$REAL_HOME/.config/kscreenlockerrc"

"${AS_USER[@]}" kwriteconfig6 --file "$LOCK_FILE" --group Greeter --key WallpaperPlugin "$PLUGIN_ID"
"${AS_USER[@]}" kwriteconfig6 --file "$LOCK_FILE" --group Greeter --group Wallpaper --group "$PLUGIN_ID" --group General --key HtmlFile "$HTML_FILE"
"${AS_USER[@]}" kwriteconfig6 --file "$LOCK_FILE" --group Greeter --group Wallpaper --group "$PLUGIN_ID" --group General --key RenderScale "$RENDER_SCALE"
"${AS_USER[@]}" kwriteconfig6 --file "$LOCK_FILE" --group Greeter --group Wallpaper --group "$PLUGIN_ID" --group General --key FrameRate "$FRAME_RATE"

echo "Updated lock screen: $LOCK_FILE"

# --- SDDM theme: system-wide, needs root ---
if [ -d "$SDDM_THEME_DIR" ]; then
  echo
  echo "Updating SDDM theme (may ask for your password) ..."
  sudo cp "$REAL_HOME/.local/share/plasma/wallpapers/$PLUGIN_ID/contents/html/"*.html "$SDDM_THEME_DIR/html/"
  sudo kwriteconfig6 --file "$SDDM_THEME_DIR/theme.conf" --group General --key webBackground "html/$HTML_FILE"
  sudo kwriteconfig6 --file "$SDDM_THEME_DIR/theme.conf" --group General --key webFps "$FRAME_RATE"
  sudo kwriteconfig6 --file "$SDDM_THEME_DIR/theme.conf" --group General --key webScale "$RENDER_SCALE"
  sudo kwriteconfig6 --file "$SDDM_THEME_DIR/theme.conf" --group General --key type "web"

  # theme.conf.user (a user-override file SDDM's own KCM writes to) can
  # end up with type=color in it - e.g. after opening System Settings ->
  # Login Screen (SDDM) and touching anything there - which silently
  # overrides theme.conf's type=web and shows a flat color background
  # instead of the animation. Since it always wins over theme.conf, wipe
  # it clean on every sync so that can't linger.
  sudo tee "$SDDM_THEME_DIR/theme.conf.user" > /dev/null <<'EOF'
[General]
EOF

  echo "Updated SDDM theme: $SDDM_THEME_DIR/theme.conf (and reset theme.conf.user)"
else
  echo
  echo "SDDM theme isn't installed yet at $SDDM_THEME_DIR - run install-sddm-theme.sh first."
fi

echo
echo "Done. Test the lock screen safely with:"
echo "  /usr/lib/kscreenlocker_greet --testing"
echo "Test the SDDM theme safely with:"
echo "  sddm-greeter-qt6 --test-mode --theme $SDDM_THEME_DIR"
