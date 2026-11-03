#!/usr/bin/env bash
# Vygeneruje všechny STL (v tiskové orientaci) a DXF skel.
# Použití:  ./build.sh            (velikost "medium")
#           SPECIES=large ./build.sh
set -euo pipefail
cd "$(dirname "$0")"
SPECIES="${SPECIES:-medium}"
OUT="stl/${SPECIES}"
mkdir -p "$OUT" dxf

declare -A PARTS=(
  [colosseum]="core facade plinth_left plinth_right tower tower_cap dome_cap bezel cover plugs"
  [parthenon]="core temple roof bezel cover plugs"
  [pisa]="core tower_lower tower_upper belfry bezel cover plugs"
)
for model in colosseum parthenon pisa; do
  for part in ${PARTS[$model]}; do
    echo ">> $model / $part"
    openscad -q -D "PART=\"$part\"" -D "SPECIES=\"$SPECIES\"" \
      -o "$OUT/${model}_${part}.stl" "$model.scad"
  done
  openscad -q -D 'PART="plate"' -o "dxf/${model}_plate.dxf" "$model.scad"
done
echo "hotovo -> $OUT, dxf/"
