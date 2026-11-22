# Dolina

Budovatelská hospodářská strategie pro iPad (a každý moderní prohlížeč).
Stavíš osadu v údolí, propojuješ budovy sítí cest s vlajkami, nosiči přenášejí
zboží mezi vlajkami a výrobní řetězce (dřevo → prkna, obilí → mouka → chléb,
ruda + uhlí → železo → nářadí/zbraně, zlato → mince) postupně rostou.
Vojenské budovy rozšiřují území.

## Hraní na iPadu
1. Stránku zveřejni přes HTTPS (např. GitHub Pages – složka `dolina/`).
2. Otevři ji v Safari → **Sdílet → Přidat na plochu**.
3. Spouští se přes celou obrazovku a díky service workeru funguje i offline.
   Hra se ukládá automaticky (localStorage).

Lokálně stačí otevřít `index.html` v prohlížeči.

## Ovládání
- jeden prst: posun mapy, dva prsty: zoom, klepnutí: výběr místa/budovy
- 🏗 zobrazí stavební místa, 📦 zásoby, 🎯 cíle, ☰ menu (uložit, nová hra, nápověda)

## Struktura
- `js/data.js` – budovy, suroviny, cíle
- `js/map.js` – mřížka a generátor mapy
- `js/world.js` – vlajky, cesty, budovy, území
- `js/econ.js` – trasy zboží, sklady, poptávka, výroba
- `js/units.js` – nosiči a pracovníci
- `js/sim.js` – nová hra, krok simulace, ukládání
- `js/render.js`, `js/ui.js`, `js/main.js` – grafika, rozhraní, ovládání

## Testy
```bash
node --test dolina/tests/sim.test.js
```
