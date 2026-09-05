#!/usr/bin/env bash
# Builds a .plasmoid file for manual installation or distribution
set -euo pipefail

# shellcheck source=scripts/common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/scripts/common.sh"
cd -- "$SCRIPT_ROOT"

VERSION=$(python3 -c "import json; print(json.load(open('metadata.json'))['KPlugin']['Version'])")
OUTPUT="plasma-css-wallpaper-$VERSION.plasmoid"

python3 -c "
import zipfile, os, sys
output = sys.argv[1]
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
    z.write('metadata.json')
    for root, dirs, files in os.walk('contents'):
        for f in files:
            path = os.path.join(root, f)
            z.write(path)
print('Created', output)
" "$OUTPUT"
