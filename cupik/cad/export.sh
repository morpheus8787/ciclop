#!/bin/sh
# Vygeneruje všechny STL soubory do ../stl (potřebuje OpenSCAD)
cd "$(dirname "$0")"
for dil in telo vicko noha chodidlo tykadlo; do
  echo "Exportuji $dil…"
  openscad -q -o "../stl/$dil.stl" -D "dil=\"$dil\"" cupik.scad
done
