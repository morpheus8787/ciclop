# IQOS VEEV ONE – návlek / kryt

Jednoduchý parametrický kryt na tělo (baterii) VEEV ONE pro 3D tisk.

| Soubor | Účel |
|---|---|
| `veev_one_case.stl` | pro slicer (tisk) |
| `veev_one_case.step` | pro úpravy v Shapr3D / Fusion / FreeCAD |
| `veev_one_case.py` | parametrický zdroj (CadQuery) |
| `preview.png` | náhled |

**Vnější rozměr:** 22,7 × 13,7 × 73,2 mm  
**Předpokládaný rozměr těla:** 85,4 × 19 × 10 mm (z prodejních listingů, ověřte posuvkou).

- Vůle 0,25 mm na stranu, stěna 1,6 mm, dno 1,2 mm
- Výřez ve dně pro USB‑C nabíjení
- Podélný výřez na palec na přední straně pro vysunutí zařízení
- Horních ~13 mm těla zůstává volných, aby šla vyměnit náplň (pod)

## Tisk
- Orientace: dnem dolů (stojí), bez podpěr
- PETG nebo PLA, vrstva 0,2 mm, 3–4 perimetry
- Pro pružnější kryt: TPU 95A (vůli pak snižte na 0,15 mm)

## Úprava rozměrů
Změřte vlastní zařízení, upravte konstanty nahoře v `veev_one_case.py`
a spusťte `pip install cadquery && python3 veev_one_case.py`.
