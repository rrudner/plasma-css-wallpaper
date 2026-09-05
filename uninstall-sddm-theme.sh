#!/usr/bin/env bash
# Reverts install-sddm-theme.sh: removes the theme override and the
# installed theme files. Needs root.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "This needs root - removes files from /usr/share/sddm/themes and /etc/sddm.conf.d."
  echo "Run: sudo ./uninstall-sddm-theme.sh"
  exit 1
fi

THEME_NAME="css-wallpaper"
SDDM_BASE="${SDDM_BASE_DIR:-/usr/share}"
SDDM_ETC_DIR="${SDDM_ETC_DIR:-/etc}"
SDDM_LIB_DIR="${SDDM_LIB_DIR:-/usr/lib/sddm}"
SDDM_CONF_DIR="$SDDM_ETC_DIR/sddm.conf.d"
THEME_DIR="$SDDM_BASE/sddm/themes/$THEME_NAME"
CONF_FILE="$SDDM_CONF_DIR/zz-css-wallpaper.conf"

selection_in_file() {
  local file="$1"
  awk '
    $0 ~ /^[[:space:]]*\[Theme\][[:space:]]*$/ {
      in_theme=1
      next
    }
    /^[[:space:]]*\[[^]]+\][[:space:]]*$/ {
      in_theme=0
      next
    }
    in_theme && $0 ~ /^[[:space:]]*Current[[:space:]]*=/ {
      value=$0
      sub(/^[^=]*=[[:space:]]*/, "", value)
      sub(/[[:space:]]*$/, "", value)
      selected=(value == "css-wallpaper" || value == "\"css-wallpaper\"")
    }
    END { exit !selected }
  ' "$file"
}

other_references_file="$(mktemp)"
trap 'rm -f "$other_references_file"' EXIT
conf_files=("$SDDM_ETC_DIR/sddm.conf")
scan_dirs=("$SDDM_CONF_DIR" "$SDDM_LIB_DIR/sddm.conf.d")

for scan_dir in "${scan_dirs[@]}"; do
  [ -d "$scan_dir" ] || continue
  for file in "$scan_dir"/*.conf; do
    [ -e "$file" ] || continue
    [ "$file" = "$CONF_FILE" ] && continue
    if selection_in_file "$file"; then
      echo "$file" >> "$other_references_file"
    fi
  done
done
for file in "${conf_files[@]}"; do
  [ -f "$file" ] || continue
  [ "$file" = "$CONF_FILE" ] && continue
  if selection_in_file "$file"; then
    echo "$file" >> "$other_references_file"
  fi
done

if [ -s "$other_references_file" ]; then
  echo "Refusing to uninstall: '$THEME_NAME' is still selected by:"
  cat "$other_references_file"
  exit 1
fi

if [ -f "$CONF_FILE" ] && selection_in_file "$CONF_FILE"; then
  rm -f "$CONF_FILE"
  echo "Removed $CONF_FILE."
else
  echo "Skipping override removal: $CONF_FILE is missing or no longer selects '$THEME_NAME'."
fi

if [ -d "$THEME_DIR" ]; then
  rm -rf "$THEME_DIR"
  echo "Removed $THEME_DIR."
else
  echo "Nothing to remove at $THEME_DIR."
fi

echo "SDDM should use theme settings from remaining SDDM config files."
