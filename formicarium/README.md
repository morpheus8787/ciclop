# Mraveniště – památky světa (3D tisk, Prusa CORE One)

Tři parametrická formikária (mraveniště) ve tvaru památek, navržená v OpenSCADu.
Každý model ukazuje **řez budovou**: vpředu je pozorovací plocha s komůrkami pod
sklem, vzadu „zbytek“ památky. Inspirace: přiložené koncepty (Colosseum / Pyramid
Formicarium).

| Model | Rozměr (Š × H × V) | Díly |
|---|---|---|
| **Koloseum v2** (Řím) | 340 × 214 mm podstavec, budova 224 × 151 × 118 mm (+ kopule) | jádro, fasáda, podstavec (2 díly), vodní věž + víčko, čepička kopule, rámeček, víčko, zátky |
| **Parthenón** (Atény) | 236 × 172 × 122 mm | jádro, chrám (sloupy + kladí), střecha, rámeček, víčko, zátky |
| **Šikmá věž** (Pisa) | 95 × 42 × 228 mm | jádro, věž dole, věž nahoře, zvonice, rámeček, víčko, zátky |

Všechny díly se vejdou na **Prusa CORE One / CORE One+ (250 × 220 × 270 mm)**,
tisknou se **bez podpěr** a jsou ověřené jako uzavřená (watertight) tělesa.

### Koloseum v2 – podle konceptu „Colosseum Formicarium“
![](img/colosseum_assembly.png)
![](img/colosseum_back.png)

Co je převzato z konceptu:
- **celý eliptický amfiteátr** s výsekem vpředu – v řezu jsou klenuté komůrky, sladěné s patry arkád
  (3 patra hnízda = 3 patra oblouků),
- **80 průchozích oblouků** s ochozem za nimi a polosloupy, atika s okénky,
- **průhledná kopule nahoře = aréna (outworld)** se stupňovitým hledištěm a pískem/mechem;
  mravenci do ní vylézají chodbou z horního patra hnízda,
- **větrací čepička** na vrcholu kopule (vyjímatelná zátka se síťkou = otvor na krmení),
- **vodní věž** vlevo (plexi trubka) propojená hadičkou se sádrou v základně,
- **eliptický podstavec** s obvodovým chodníkem a nápis COLOSSEVM,
- rámeček skla s **okny ve tvaru komůrek** – zepředu vypadá jako kamenný řez jako na obrázku.

Rozdíly proti obrázku (kvůli mravencům a tisku): kopule je kulová Ø 120 mm (koupená, tisk
průhledné kopule není možný) a nepokrývá celou střechu; osvětlení komůrek („noční režim“)
jsem nedával – světlo v hnízdě mravence stresuje (max. slabé červené LED zvenku).

| Parthenón | Pisa |
|---|---|
| ![](img/parthenon_iso.png) | ![](img/pisa_iso.png) |
| ![](img/parthenon_back.png) | ![](img/pisa_back.png) |

Pohled na komůrky: `img/colosseum_front.png` (s rámečkem), `img/*_core_front.png` (bez skla).

---

## 1. Co mravenci potřebují a jak to modely řeší

| Potřeba kolonie | Řešení v modelu |
|---|---|
| **Vlhkostní gradient** – vlhká část pro plod, suchá pro zásoby a královnu podle potřeby | Spodní patro má pod komůrkami **6 mm sádry** (kapsy se schůdkem = ryska, kam lít). Sádra je propojená kanálem a zalévá se **akvarijní hadičkou 4/6 mm** shora. Horní patra jsou suchá a větraná → mravenci si sami vyberou. |
| **Plast nedrží vlhkost** (na rozdíl od sádry/Ytongu) | Proto hybridní řešení: plastové tělo + sádrová hydratační zóna. Plast zůstává suchý (méně plísní). |
| **Větrání bez úniku** | Z horních komůrek vedou kanálky Ø 4 mm na horní hranu, kde je zápustné lůžko pro **nerezovou síťku 0,2 mm** (Ø 10 mm). 0,2 mm zadrží i malé nanitiky Lasius (~2 mm). |
| **Správná hloubka komůrek** (mravenci nesmí „lézt po sobě“, ale ani se ztrácet) | Parametr `SPECIES`: 6 / 10 / 15 mm (viz tabulka níže) – odpovídá běžné praxi prodejců (10 mm pro Lasius/Formica, větší pro Camponotus/Messor). |
| **Chodby** | Šířka 4 / 6 / 9 mm podle druhu, galerie na úrovni podlahy, šikmé rampy mezi patry střídavě vlevo/vpravo (kolonie musí projít celé hnízdo – lepší cirkulace a rozdělení pater). |
| **Tma** | Zatemňovací **víčko na magnety** (6×2 mm) s nápisem – sundáš jen při pozorování. Alternativně červená fólie na sklo. |
| **Pozorování** | Plexisklo/sklo 3 mm přitisknuté k rovné čelní ploše (tisk čelem nahoru + žehlení horní vrstvy = rovina bez škvír). |
| **Únikuvzdornost** | Jádro je **jeden kus** (žádné spáry v hnízdě), sklo v drážce rámečku, hrdlo hadičky má vlastní zátku, zavlažovací hadička má zátku. |
| **Aréna (outworld) na krmení a vodu** | Koloseum: aréna je **pod kopulí na střeše** (větrání 3 otvory se síťkou v atice + čepička). Ostatní modely: hrdlo pro **silikonovou hadičku 8×12 mm** na boku a aréna = libovolný box s Fluonem (PTFE) na stěnách a víkem se síťkou. Koloseum má boční hrdlo také (pro 2. arénu, jinak zátka). |
| **Snadná údržba** | Rámeček se sklem jde odšroubovat (M3), sádru lze dovlhčit bez otevírání. |

### Velikost podle druhu (`SPECIES`)

| `SPECIES` | Druhy (příklady) | Hloubka komůrky | Chodba | Výška komůrky |
|---|---|---|---|---|
| `small` | Tetramorium, Temnothorax, Leptothorax, nanitici | 6 mm | 4 mm | 7–9 mm |
| `medium` *(výchozí)* | Lasius niger, Formica, Myrmica, Tapinoma | 10 mm | 6 mm | 10–13 mm |
| `large` | Messor, Camponotus | 15 mm | 9 mm | 14–18 mm |

Předgenerované STL jsou pro **medium** (`stl/medium/`). Jinou velikost vygeneruješ:
```bash
SPECIES=large ./build.sh        # -> stl/large/
```
(Hloubka jádra se mění, proto se přegenerují i fasády – sedí k sobě jen díly stejné velikosti.)

---

## 2. Materiál

| Díl | Materiál | Proč |
|---|---|---|
| **Jádro (hnízdo)** | **PETG** (např. Prusament PETG) | Odolá trvalé vlhkosti; PLA ve vlhku časem degraduje a hůř se čistí. PETG je běžně doporučované pro formikária. |
| Fasády, střecha, zvonice | PETG (nebo PLA – nejsou ve styku s vlhkostí ani mravenci) | PLA „mramor/kámen“ vypadá hezky, PETG je odolnější. |
| Rámeček, víčko | PETG / PLA | – |
| **Nepoužívat** | ABS/ASA (výpary styrenu v uzavřeném prostoru), resin/SLA (nevytvrzené zbytky jsou toxické) | – |

**Barva jádra:** tmavá (černá/hnědá) – mravenci se cítí lépe a lépe je vidět kontrast.

---

## 3. Nastavení tisku (PrusaSlicer, CORE One, tryska 0,4)

| Díl | Vrstva | Perimetry | Výplň | Poznámka |
|---|---|---|---|---|
| `*_core` | 0,2 mm | 4 | 20 % gyroid, 6 horních vrstev | Tiskne se **čelem nahoru**. Zapni **Žehlení → jen nejvyšší plocha** (rovná plocha pod sklo). Žádné podpěry. |
| `*_facade`, `*_temple`, `*_tower_*`, `*_belfry` | 0,15 mm | 3 | 10–15 % gyroid | Stojí tak, jak jsou ve STL. Bez podpěr (jen krátké můstky). Parthenón: pomalejší můstky. |
| `*_roof` | 0,15 mm | 3 | 10 % | plochou stranou dolů |
| `*_bezel` | 0,2 mm | 3 | 30 % | pohledovou stranou na podložku |
| `colosseum_plinth_*` | 0,2 mm | 3 | 15 % | každá polovina zvlášť (170 × 214 mm) |
| `colosseum_tower`, `_tower_cap`, `_dome_cap` | 0,15 mm | 3 | 20 % | věž: 4 perimetry, ať je pata vodotěsná |
| `*_cover` | 0,2 mm | 3 | 20 % | nápis nahoru (lze změnit barvu na vrstvě 2,4 mm = barevný nápis) |
| `*_plugs` | 0,15 mm | 4 | 100 % | |

PETG: 240/85 °C (profil Prusament PETG), na texturovaný plát nebo s lepidlem/separací.

---

## 4. Nákupní seznam (na 1 model)

- PETG ~ 0,3–0,7 kg (dle modelu, fasády jsou plné s řídkou výplní)
- **Plexisklo (PMMA) nebo sklo 3 mm** – rozměr:
  - Koloseum **158 × 81 mm** (obdélník)
  - Pisa **66 × 160 mm** (obdélník)
  - Parthenón **pětiúhelník 184 × 89 mm** → nech vyřezat laserem podle `dxf/parthenon_plate.dxf`
    (DXF pro laser jsou i pro ostatní: `dxf/*_plate.dxf`)
- Šrouby **M3 × 12 zápustné** (samořezné do plastu): Koloseum 7, Parthenón 7, Pisa 4
- Neodymové magnety **6 × 2 mm**: Koloseum 8, Parthenón 8, Pisa 4 (půlka do rámečku, půlka do víčka)
- Nerezová síťka **0,2 mm** (kolečka Ø 10 mm): Koloseum 5 (+ 1 kolečko Ø 26 mm do čepičky kopule), Parthenón 2, Pisa 2
- **Jen Koloseum:**
  - průhledná **dělitelná plastová koule Ø 120 mm** (dekorační, PET/PS) nebo akrylová polokoule Ø 120 mm – použije se půlka
  - **plexi trubka 40/34 mm, délka 70 mm** (vodní věž)
  - akvarijní silikon bez fungicidů (utěsnění trubky ve věži)
  - jemný písek / hlína, mech na dno arény
- **Sádra** – modelářská/alabastrová nebo dentální, bez přísad (~50 g)
- **Akvarijní vzduchovací hadička 4/6 mm** (~30 cm)
- **Silikonová hadička 8 × 12 mm** k aréně
- Kousky filamentu 1,75 mm jako **kolíky** (15 mm)
- Lepidlo na spoje mimo hnízdo: vteřinové (CA) nebo 2složkový epoxid
- **Fluon (PTFE)** do arény

---

## 5. Montáž

1. **Tisk** všech dílů. Zkontroluj čelní plochu jádra pravítkem – nesmí být prohnutá.
2. **Zavlažovací hadička:** zasuň hadičku 4/6 mm do otvoru na horní hraně jádra (nejbližší
   kraji) až dolů a do spodního kanálu (jde ohnout), konec ucpi chumáčkem vaty.
3. **Sádra:** jádro polož čelem nahoru, rozmíchej sádru a nalij do spodních (vlhkých) komůrek
   **po schůdek** (6 mm). Sádra proteče kanálem pod příčkami → jedna souvislá vrstva. Nechej
   vytvrdnout 24 h, pak 2–3 dny vysychat.
4. **Větrací síťky** vlep do lůžek na horní hraně (tenká vrstva CA nebo akvarijního silikonu
   jen po obvodu, otvor nezalepit). U Pisy se síťky přitlačí zvonicí.
5. **Fasády:** do otvorů zasuň kolíky z filamentu, slep fasádu (a střechu/zvonici) s jádrem –
   lepidlo jen na vnější styčné plochy, nikdy do komůrek.
6. **Nech všechno min. 48 h větrat** (lepidla, sádra).
7. **Sklo + rámeček:** sklo vlož do drážky rámečku, přišroubuj M3 × 12 (nepřetáhnout).
8. Vlep magnety do rámečku a víčka (pozor na polaritu).
9. **Test těsnosti:** nalij 3–5 ml vody do hadičky, za 1 h zkontroluj, že voda nepronikla mimo
   sádru. Posviť zezadu – skrz spáru mezi sklem a čelem nesmí prosvítat světlo.
10. Do hrdla zasuň hadičku 8 × 12 k aréně (nebo zátku).

### Koloseum – navíc
1. **Podstavec** slep ze dvou polovin (kolíky z filamentu).
2. **Zavlažování = spojené nádoby:** hadička 4/6 mm vede z vývodu u paty věže drážkou v podstavci a
   do otvoru v levém boku jádra (vodní kanál pod podlahou spodního patra). Nejdřív hadičku zasuň do
   jádra (konec s chumáčkem vaty), pak teprve nalij sádru.
3. **Věž:** plexi trubku vlep silikonem do lůžka věže (vodotěsně), nasaď víčko na sloupky.
   **Ryska na sloupcích = MAX hladina.** Hladina ve věži je stejná jako v kanálu pod podlahou
   hnízda – pod ryskou nikdy nevyteče do komůrek a sádra se sama dosytí. Nad rysku nenalévat!
   Věž zároveň ukazuje, kolik vody v hnízdě zbývá.
4. **Kopule:** do půlky koule vyvrtej stupňovitým vrtákem otvor Ø 30 mm, zvenku nalep kroužek
   čepičky, do zátky vlep síťku Ø 26 mm. Kopuli posaď do drážky na střeše; spáru utěsni tenkým
   proužkem molitanu/plastelíny, nebo ji natři Fluonem zevnitř (aby mravenci nelezli k okraji).
5. Do arény nasyp 5–10 mm písku/hlíny, dej mech, misku s vodou (zkumavku s vatou) a krmení.
   Krmí se vyndáním zátky v čepičce, kopuli zvedej jen při úklidu.
6. Vstup z hnízda do arény je otvor v horní hraně jádra pod přední částí kopule.

### Stěhování kolonie
Kolonie v zkumavce: připoj arénu, zkumavku vlož do arény, hnízdo zatemni víčkem a sádru navlhči.
Mravenci se přestěhují sami (dny až týdny). Hnízdo by nemělo být o moc větší než kolonie –
malé kolonii můžeš horní patra dočasně oddělit/neprovlhčovat, ale hlavně ji nespěchej.

---

## 6. Provoz

- **Zavlažování:** 2–5 ml vody do hadičky 1× týdně (podle druhu a teploty). Sádra má být vlhká,
  **ne mokrá**; kondenzace na skle = moc vody.
- **Gradient:** spodní patro vlhké, horní suché. Nikdy neprovlhčuj celé hnízdo.
- **Teplota:** většina středoevropských druhů 22–26 °C (Messor rád tepleji), mimo přímé slunce.
- **Tma:** víčko nasazené, sundávat jen na pozorování.
- **Čistota:** jídlo jen v aréně. Plíseň v hnízdě = méně vody, víc větrání. Rámeček jde
  odšroubovat a sklo vyčistit (mimo období s plodem).
- **Zimování** (Lasius, Formica, Myrmica…): celé hnízdo s arénou do 5–10 °C, sádra jen lehce vlhká.

---

## 7. Úpravy a generování

Potřebuješ [OpenSCAD](https://openscad.org) (testováno 2021.01).

```bash
./build.sh                                # všechny STL (medium) + DXF skel
SPECIES=small ./build.sh
openscad -D 'PART="core"' -D 'SPECIES="large"' -o core.stl colosseum.scad
```

`PART`: `assembly` (náhled se sklem), `display` (bez skla), `core`, `facade` / `temple` /
`roof` / `tower_lower` / `tower_upper` / `belfry`, `bezel`, `cover`, `plugs`, `plate` (2D → DXF);
Koloseum navíc `plinth_left`, `plinth_right`, `tower`, `tower_cap`, `dome_cap`.
Koloseum: `DOME_D` (průměr kopule, max ~128 mm), `TUBE40_*` (trubka věže).

Hlavní parametry (`lib/formicarium.scad`): `SPECIES`, `PLASTER_T` (sádra), `PLATE_T`
(sklo), `TUBE_OD` (hadička k aréně), `AIRLINE_OD`, `MESH_D`, rozměry šroubů a magnetů.
V souboru modelu: rozložení pater `COLS` (počet komůrek v každém patře), rozsah pole komůrek
`FIELD_X`, `Z0`, `ZTOP`.

Pro **CORE One L** (300 × 300 × 330) můžeš modely zvětšit úpravou rozměrů v hlavičce
souboru (např. `A`, `B`, `H` u Kolosea) – komůrky zůstanou ve správné velikosti pro druh.

### Kontrola
`build.sh` + kontrola v Pythonu (trimesh): všechny díly jsou uzavřená tělesa z jednoho kusu,
vejdou se do 250 × 220 × 270 mm, plochy s převisem > 45° jsou jen krátké můstky (otvory, horní
hrany nik, kladí mezi hlavicemi sloupů).

---

## Omezení / na co dát pozor

- Modely jsou **stylizované**, ne přesné repliky.
- Koloseum: fasáda je masivní díl (~0,5 kg PETG při 10 % výplni); hlídej hladinu ve věži pod ryskou.
- Je to **zatím nevytištěný návrh** – ověřeno výpočetně (geometrie, rozměry, převisy).
  Doporučuji nejdřív vytisknout jádro Pisy (nejmenší) a vyzkoušet sádru + těsnost skla.
- Velikosti pro druhy vychází z praxe chovatelů a prodejců, ne z vědeckých norem –
  podle svého druhu případně uprav `CH_D` / `TUN_W`.
- U lepidel a silikonu dodrž dobu vytvrzení a nech hnízdo před nastěhováním vyvětrat.

## Zdroje
- Rozměry tiskárny: [3DJake – Prusa CORE One](https://www.3djake.com/prusa/core-one), [CORE One L](https://www.3djake.com/prusa/core-one-l)
- Šířky mezer podle druhů: [antstore.net – formikária](https://www.antstore.net/shop/en/antfarms---nests), [antstore – akrylová formikária](https://www.antstore.net/shop/en/antfarms---nests/acrylglas-formicaria/)
- Lasius niger velikost: [antstore – Lasius niger](https://www.antstore.net/shop/en/ants/Ants-from-Central-Europe/Lasius-niger--Black-Garden-Ant-.html), [AntCube](https://antcube.shop/en/product/lasius-niger/)
- Vlhkostní gradient, hydratace: [furrycritter – typy formikárií](https://www.furrycritter.com/pages/articles/invertebrates/formicarium_types.htm), [Formiculture – nest humidity](https://www.formiculture.com/topic/2112-nest-humidity-level/)
- PLA vs PETG, plíseň, 3D tisk: [Formiculture – 3D printed nests](https://www.formiculture.com/topic/19064-3d-printed-nests/page-2), [MakerWorld – formicarium (PETG doporučeno)](https://makerworld.com/en/models/3225264-formicarium)
- Větrací síťka 0,2 mm, nanitici: [Formiculture – ventilation for Lasius niger](https://formiculture.com/topic/20022-what-is-the-right-size-for-ventilation-holes-sliths-for-lasius-niger), [antstore – mřížka 0,2 mm](https://www.antstore.net/shop/en/components/grid/grid-insert---27mm---stainless-steel.html)
- Únikuvzdornost, Fluon: [Formiculture – escape prevention](https://formiculture.com/topic/18736-escape-prevention), [AntGear – Fluon](https://antgear.com/?p=510)
