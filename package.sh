#!/usr/bin/env bash
# Builds a .plasmoid file for manual installation or distribution
set -e

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
