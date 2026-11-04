# Trading agent (BTC, spot, jen long)

Pravidlový agent, který obchoduje podle pevně daných pravidel, takže do rozhodování nevstupují emoce.
Každé rozhodnutí je deterministické, zalogované a zapsané do deníku `state/journal.csv`.

```
svíčky z burzy ──► indikátory (EMA50/200, RSI, ATR)
                  + 23 svíčkových/cenových patternů ──► signál
zprávy (RSS) ────► filtr zpráv (blokace nákupů / panický výstup) ──┤
                                                                   ▼
                     řízení rizika (velikost pozice, stop, denní limit, kill-switch) ──► burza
```

## Pravidla strategie

**Vstup (nákup)** na uzavřené svíčce, když platí všechno:
1. Trend nahoru: `close > EMA200` a `EMA50 > EMA200`
2. RSI mezi 40 a 70 (trh není překoupený)
3. Na svíčce se dokončil aspoň jeden **povolený** bullish pattern (viz učení níže)
4. Zprávy neblokují nákupy
5. Risk manager povolí obchod (není aktivní denní limit, kill-switch ani limit počtu obchodů)

**Výstup (prodej)** podle toho, co nastane dřív:
- stop-loss = vstup − 2× ATR
- take-profit = vstup + 2× riziko (poměr 1 : 2)
- bearish pattern a zároveň close < EMA50, nebo close < EMA200
- kritická zpráva (hack, krach burzy, žaloba SEC…), pokud `NEWS_EXIT_ON_PANIC=true`

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
Feedy jdou upravit v `NEWS_FEEDS`. Aktuální vyhodnocení zpráv ukáže `python -m agent.main news`.

## Instalace

```bash
cd trading-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # a uprav hodnoty
python -m pytest          # 89 testů
```

## Doporučený postup (i když chceš jít rovnou živě)

```bash
python -m agent.main learn --days 730      # 1) které patterny fungují
python -m agent.main backtest --days 365   # 2) jak by strategie dopadla (srovnej s buy & hold)
python -m agent.main review --days 730     # 3) rozbor obchodů, učení z chyb
python -m agent.main news                  #    stav zpráv
MODE=paper python -m agent.main run        # 4) pár dní nanečisto se živými daty
MODE=live  python -m agent.main run        # 5) živě s malou částkou
```

Pro **live** v `.env` nastav:
```
MODE=live
API_KEY=...
API_SECRET=...
LIVE_CONFIRM=I_UNDERSTAND_THE_RISK
MAX_ORDER_QUOTE=50          # žádná objednávka nikdy nepřesáhne 50 USDT
```

### API klíč na burze: bezpečnost
- Povol **jen Spot trading**. **Výběry (withdrawals) NIKDY nepovoluj.**
- Zapni omezení na IP adresu počítače, na kterém agent běží.
- Klíč patří jen do `.env` (je v `.gitignore`), nikdy ho necommituj.
- Na burze drž jen částku, kterou jsi ochoten ztratit.

## Pojistky

| Pojistka | Výchozí | Co dělá |
|---|---|---|
| `RISK_PER_TRADE` | 1 % | ztráta při stopu je max. 1 % účtu (konfigurace víc než 5 % nepovolí) |
| `MAX_POSITION_PCT` | 25 % | max. podíl účtu v jedné pozici |
| `MAX_ORDER_QUOTE` | 50 USDT | absolutní strop na objednávku |
| `MAX_DAILY_LOSS_PCT` | 3 % | po denní ztrátě 3 % agent do půlnoci UTC neotevírá obchody |
| `MAX_TRADES_PER_DAY` | 4 | ochrana proti „overtradingu“ |
| Kill-switch | – | `touch state/STOP` → okamžitě žádné nové nákupy |
| Live potvrzení | – | bez `LIVE_CONFIRM` se live režim nespustí |
| 10 chyb za sebou | – | agent se sám zastaví |
| Jen BTC | `SYMBOL=BTC/USDT` | jiné aktivum se nespustí bez `ALLOW_ALTCOINS=true` |

## Známé limity (přečti si je)

1. **Stop-loss hlídá agent, ne burza.** Agent kontroluje cenu každých `POLL_SECONDS` (30 s).
   Když agent neběží (vypnutý počítač, výpadek sítě), stop se neprovede. Agent proto musí běžet nepřetržitě,
   ideálně na serveru nebo VPS. Dalším krokem by mohly být stop objednávky přímo na burze (OCO).
2. **Backtest nezahrnuje zprávy.** Historické titulky nejsou k dispozici, takže backtest testuje jen technickou část.
3. **Skluz (slippage)** backtest nemodeluje, počítá jen s poplatkem 0,1 %.
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
