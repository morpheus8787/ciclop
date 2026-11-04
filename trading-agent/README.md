# Trading agent (BTC, Coinbase, spot, jen long)

Pravidlový agent, který obchoduje podle pevně daných pravidel, takže do rozhodování nevstupují emoce.
Každé rozhodnutí je deterministické, zalogované a zapsané do deníku `state/journal.csv`.

```
svíčky z burzy ──► indikátory (EMA50/200, RSI, ATR)
                  + 23 svíčkových/cenových patternů ──► signál
zprávy (RSS) ────► filtr zpráv (blokace nákupů / panický výstup) ──┤
                                                                   ▼
                     řízení rizika (velikost pozice, stop, denní limit, kill-switch) ──► burza
```

## Strategie: trend-following (výchozí, `STRATEGY=trend`)

Na **denních** svíčkách BTC/EUR. Žádné předpovídání, jen pravidla:

**Vstup (nákup)**, když platí všechno:
1. Close překoná maximum posledních **20 dní** (průraz Donchianova kanálu)
2. Close je nad **EMA200**, tedy v dlouhodobém býčím trendu
3. Zprávy neblokují nákupy a risk manager obchod povolí

**Výstup (prodej)** podle toho, co nastane dřív:
- close spadne pod minimum posledních **10 dní**
- **trailing stop**: nejvyšší cena od vstupu − 3× ATR. Posouvá se jen nahoru, takže zamyká zisk.
- počáteční stop: vstup − 3× ATR
- kritická zpráva, pokud `NEWS_EXIT_ON_PANIC=true`
- pevný take-profit **není**: zisky se nechávají běžet, protože na tom trend-following stojí

### Výsledky backtestu (BTC denně, 17. 8. 2017 – 3. 11. 2026, data Binance BTC/USDT)

| Varianta | Obchodů | Úspěšnost | Průměr na obchod | Profit factor | Výnos | Max. propad |
|---|---:|---:|---:|---:|---:|---:|
| 20/10, poplatek 0,6 % | 46 | 37 % | +0,25R | 1,57 | +11,4 % | −4,4 % |
| **20/10, poplatek 0,9 %** | 46 | 37 % | **+0,19R** | 1,40 | +8,6 % | −4,8 % |
| 20/10, poplatek 1,2 % | 46 | 37 % | +0,13R | 1,25 | +5,8 % | −5,7 % |
| 55/20, poplatek 0,9 % | 35 | 40 % | +0,14R | 1,28 | +4,5 % | −5,9 % |
| 20/10, 0,9 %, celý účet v obchodu | 46 | 37 % | – | – | +37,6 % | −21,9 % |
| *Buy & hold BTC* | – | – | – | – | *+1 708 %* | *−83 %* |

Jak to číst:
- Strategie je **v plusu ve všech variantách i po poplatcích Coinbase**, na rozdíl od svíčkových patternů.
- Výhoda je ale malá a v novější polovině dat skoro zmizela: 1. polovina +0,38R, 2. polovina +0,02R na obchod.
- Strategie **zdaleka nedosahuje výnosu prostého držení BTC**. Jejím přínosem je nízký propad, ne výnos.
- Při výchozím 1% riziku je pozice asi 10 % účtu a v trhu je strategie jen 24 % času.

## Strategie: svíčkové patterny (`STRATEGY=patterns`)

Původní varianta na hodinových svíčkách: trend (EMA50 > EMA200), RSI 40–70 a ověřený bullish pattern.
Stop 2× ATR, cíl 2R. **Na BTC nemá prokázanou výhodu** (1h: −0,19R na obchod), viz učení patternů níže.

## „Učení“ patternů

Knihovna obsahuje 23 patternů: hammer, engulfing, harami, morning a evening star, three soldiers a crows,
piercing, dark cloud, tweezer, marubozu, Donchian breakout, inside bar breakout a další (`agent/patterns.py`).

Příkaz `learn` změří na historii zvoleného trhu, které patterny **skutečně** mají výhodu:
- Data se rozdělí na 70 % trénovacích a 30 % ověřovacích.
- Pattern se vybere jen tehdy, když má kladný průměrný pohyb (≥ 0,25 %) a úspěšnost nad 50 % v **obou** částech.
- Výsledek se uloží do `state/learned_patterns.json` a agent pak obchoduje jen s vybranými patterny.
- Když neprojde žádný pattern, agent **neobchoduje**. To je správně: znamená to, že na daném trhu nejsou podložené.

> Upřímně: samotné svíčkové patterny mají na krypto trzích obvykle slabou výhodu.
> Proto je tu trendový filtr, filtr zpráv a hlavně tvrdé řízení rizika.

## Učení z vlastních obchodů

Agent si ke **každému** obchodu uloží do `state/trades.jsonl`, za jakých okolností vstoupil a jak obchod dopadl:
- **kontext vstupu:** patterny, RSI, vzdálenost od EMA50 v ATR (`stretch`), volatilita, obchodní seance (Asie/Evropa/USA), objem a skóre zpráv,
- **výsledek:** zisk/ztráta v **R** (násobcích rizika), **MFE** (maximální zisk během obchodu), **MAE** (maximální pokles během obchodu), doba držení a důvod výstupu.

Rozbor (`python -m agent.main review`, nebo automaticky každých `ADAPT_EVERY_TRADES` uzavřených obchodů)
roztřídí dobré i špatné obchody a pojmenuje opakované chyby:

| Chyba | Co znamená | Možná náprava |
|---|---|---|
| Rychlý stop | stop do 3 svíček | špatné načasování vstupu |
| Vrácený zisk | obchod byl ≥ 1R v plusu, skončil ve ztrátě | posun stopu na nákupku při +1R |
| Honění ceny | vstup > 2 ATR nad EMA50 a ztráta | nevstupovat v situaci `stretch=>2ATR` |
| Vstup nikdy nefungoval | cena se hned obrátila (MFE < 0,25R) | vypnout slabý pattern |

Ze závěrů agent odvodí **úpravy pravidel**: vypne ztrátové patterny, zablokuje ztrátové situace
(nejvýš 3 a nikdy všechny varianty jedné vlastnosti) a zapne ochranu zisku.

**Ochrana proti přeučení**, protože nejčastější chybou „samoučících se“ botů je, že se naučí šum:
1. Závěr se dělá jen ze skupiny s aspoň `ADAPT_MIN_TRADES` (15) obchody.
2. Úpravy se odvodí ze starší části historie a ze skutečných obchodů, pak se **ověří na novější části**, kterou rozbor neviděl.
3. Úpravy se přijmou jen tehdy, když na ověřovacích datech zlepší průměrné R i výnos a nezhorší drawdown o víc než 1 p. b.
   Původní i upravená pravidla tam navíc musí mít **aspoň 10 obchodů**, jinak nejde výsledek odlišit od náhody.
4. Úpravy smí pravidla **jen zpřísnit**. Nikdy nezvýší riziko, velikost pozice ani limity.

Každý rozbor se uloží jako čitelný report v `state/reviews/review-*.md`. Je v něm tabulka podle patternů, kontextů
a důvodů výstupu, 5 nejlepších a 5 nejhorších obchodů a samostatná sekce **jen pro skutečné obchody agenta**.
Přijaté úpravy jsou v `state/adaptations.json`. Smazáním souboru se agent vrátí k výchozím pravidlům.

> Na začátku bude skutečných obchodů málo, takže se agent učí hlavně z backtestu na historii BTC.
> Čím déle běží, tím větší váhu mají jeho vlastní obchody.

## Zprávy

Agent stahuje titulky z RSS kanálů (CoinDesk, Cointelegraph a veřejné RSS Financial Times) a hodnotí je
slovníkem klíčových slov. Ten je auditovatelný, bez „černé skříňky“.
- **Kritická** krypto zpráva → nákupy se zablokují a otevřená pozice se prodá.
- Nakupí-li se negativních zpráv (skóre ≤ −3) → nákupy se zablokují.
- Když zprávy nejdou stáhnout a `NEWS_FAIL_SAFE=block` → agent nenakupuje (bezpečná varianta).

**K účtu na FT:** agent se do FT nepřihlašuje a nestahuje placené články. Automatizované stahování
s osobním přihlášením by porušovalo podmínky FT. Používá jen veřejné RSS titulky, a to na tento účel stačí.
Feedy jdou upravit v `NEWS_FEEDS`.

**Tržní data:** `MARKET_DATA=binance_vision` bere svíčky z veřejného `data-api.binance.vision`. To se hodí tam, kde je `api.binance.com` blokované (některé země, cloud servery). Platí pro `learn`, `backtest`, `review` a paper režim. Testnet a live berou data vždy přímo z burzy, na které obchodují. Aktuální vyhodnocení zpráv ukáže `python -m agent.main news`.

## Instalace

```bash
cd trading-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # a uprav hodnoty
python -m pytest          # 100 testů
```

## Doporučený postup (i když chceš jít rovnou živě)

```bash
python -m agent.main backtest --days 3300  # 1) jak by strategie dopadla (srovnej s buy & hold)
python -m agent.main review --days 3300    # 2) rozbor obchodů, učení z chyb
python -m agent.main learn --days 730      #    (jen pro STRATEGY=patterns) které patterny fungují
python -m agent.main news                  #    stav zpráv
MODE=paper python -m agent.main run        # 4) pár dní nanečisto se živými daty
MODE=live  python -m agent.main run        # 5) živě s malou částkou
```

Pro **live** v `.env` nastav:
```
MODE=live
API_KEY=organizations/.../apiKeys/...
API_SECRET=-----BEGIN EC PRIVATE KEY-----\n...\n-----END EC PRIVATE KEY-----\n
LIVE_CONFIRM=I_UNDERSTAND_THE_RISK
MAX_ORDER_QUOTE=50          # žádná objednávka nikdy nepřesáhne 50 EUR
```

### Coinbase: API klíč a bezpečnost
- Klíč vytvoříš v Coinbase Developer Platform (CDP) → API keys. Typ **ECDSA**, oprávnění **View + Trade**.
  **Transfer (výběry) NIKDY nepovoluj.**
- `API_KEY` je ve tvaru `organizations/<org_id>/apiKeys/<key_id>`. `API_SECRET` je privátní klíč (PEM)
  na **jednom řádku** s konci řádků zapsanými jako `\n` (viz `.env.example`).
- Zapni omezení na IP adresu počítače, na kterém agent běží.
- Klíč patří jen do `.env` (je v `.gitignore`), nikdy ho necommituj.
- Coinbase nemá testnet: nejdřív `MODE=paper` (simulace se živými cenami), pak `MODE=live`.
- **Poplatky:** market objednávka na nejnižší úrovni objemu stojí 0,6–1,2 % (agent počítá s 0,9 %).
  Svůj skutečný tarif uvidíš v náhledu objednávky v Coinbase Advanced a nastavíš ho ve `FEE_RATE`.
- I regulovaná burza je riziko protistrany: drž tam jen částku, se kterou agent obchoduje.
- Agent potřebuje přístup na `api.coinbase.com` a na zpravodajské domény.

## Pojistky

| Pojistka | Výchozí | Co dělá |
|---|---|---|
| `RISK_PER_TRADE` | 1 % | ztráta při stopu je max. 1 % účtu (konfigurace víc než 5 % nepovolí) |
| `MAX_POSITION_PCT` | 25 % | max. podíl účtu v jedné pozici |
| `MAX_ORDER_QUOTE` | 50 EUR | absolutní strop na objednávku |
| `MAX_DAILY_LOSS_PCT` | 3 % | po denní ztrátě 3 % agent do půlnoci UTC neotevírá obchody |
| `MAX_TRADES_PER_DAY` | 4 | ochrana proti „overtradingu“ |
| Kill-switch | – | `touch state/STOP` → okamžitě žádné nové nákupy |
| Live potvrzení | – | bez `LIVE_CONFIRM` se live režim nespustí |
| 10 chyb za sebou | – | agent se sám zastaví |
| Jen BTC | `SYMBOL=BTC/EUR` | jiné aktivum se nespustí bez `ALLOW_ALTCOINS=true` |

## Známé limity (přečti si je)

1. **Stop-loss (i trailing) hlídá agent, ne burza.** Agent kontroluje cenu každých `POLL_SECONDS` (30 s).
   Když agent neběží (vypnutý počítač, výpadek sítě), stop se neprovede. Agent proto musí běžet nepřetržitě,
   ideálně na serveru nebo VPS. Dalším krokem by mohly být stop objednávky přímo na burze (OCO).
2. **Backtest nezahrnuje zprávy.** Historické titulky nejsou k dispozici, takže backtest testuje jen technickou část.
3. **Skluz (slippage)** backtest nemodeluje, počítá jen s poplatkem (`FEE_RATE`).
   Backtest běží na datech Binance BTC/USDT; na Coinbase BTC/EUR se navíc projeví kurz EUR/USD.
4. Minulé výsledky nezaručují budoucí. Zisky z kryptoměn mohou podléhat dani z příjmu, deník obchodů se k tomu hodí.

## Struktura

```
agent/
  config.py      konfigurace + validace (.env)
  indicators.py  EMA, SMA, RSI, ATR
  patterns.py    23 detektorů patternů (bez pohledu do budoucnosti)
  learn.py       statistické vyhodnocení patternů (train/test)
  review.py      rozbor obchodů, klasifikace chyb, návrh úprav, report
  selflearn.py   smyčka učení z chyb s ověřením na nových datech
  strategy.py    pravidla vstupu a výstupu, sdílená backtestem i živým agentem
  risk.py        velikost pozice, denní limity, kill-switch
  news.py        RSS + skórování zpráv
  backtest.py    simulace na historii
  broker.py      PaperBroker / ExchangeBroker (ccxt)
  data.py        stahování svíček z burzy
  store.py       stav (state.json) + deník (journal.csv)
  bot.py         hlavní smyčka
  main.py        CLI
```
