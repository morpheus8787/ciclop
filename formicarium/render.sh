#!/usr/bin/env bash
# render.sh <model.scad> <PART> <out.png> <eye x,y,z> <center x,y,z> [W,H]
set -euo pipefail
xvfb-run -a openscad --render -D "PART=\"$2\"" --camera="$4,$5" --imgsize="${6:-1200,900}" \
  --colorscheme=Tomorrow --projection=p -o "$3" "$1" >/dev/null 2>&1
