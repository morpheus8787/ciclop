"""Rozbor vlastních obchodů: co fungovalo, co ne, a jaké chyby se opakují.

Výstupem je report (dict + markdown) a návrh adaptací pravidel. Adaptace smí pravidla
jen ZPŘÍSNIT (vypnout pattern, zablokovat situaci, chránit zisk) – nikdy nezvýší riziko.
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from .strategy import CONTEXT_FEATURES

QUICK_STOP_BARS = 3
GAVE_BACK_MFE_R = 1.0
NEVER_WORKED_MFE_R = 0.25
MAX_BLOCKED_CONTEXTS = 3
BREAKEVEN_GAVE_BACK_SHARE = 0.3

MISTAKE_LABELS = {
    "quick_stop": "Rychlý stop – trh se otočil do pár svíček (špatné načasování nebo moc těsný stop)",
    "gave_back": "Vrácený zisk – obchod byl ≥ 1R v plusu a skončil ve ztrátě (chybí ochrana zisku)",
    "chased": "Honění ceny – vstup daleko nad EMA50 (> 2 ATR) a ztráta",
    "never_worked": "Vstup nikdy nefungoval – cena se skoro hned obrátila proti (slabý signál)",
    "news_exit": "Výstup kvůli zprávám",
}
GOOD_LABELS = {
    "take_profit": "Dosažen cíl (take-profit)",
    "clean_win": "Zisk s malým poklesem po cestě (MAE > −0,5R)",
}


@dataclass(frozen=True)
class TradeRecord:
    entry_time: str
    exit_time: str
    entry: float
    exit: float
    stop: float
    qty: float
    pnl: float
    r_multiple: float
    mfe_r: float
    mae_r: float
    bars_held: int
    reason: str
    patterns: str
    context: dict = field(default_factory=dict)
    source: str = "backtest"


def from_backtest(t) -> TradeRecord:
    return TradeRecord(str(t.entry_time), str(t.exit_time), t.entry, t.exit, t.stop, t.qty, t.pnl,
                       t.r_multiple, t.mfe_r, t.mae_r, t.bars_held, t.reason, t.patterns, dict(t.context))


def append_record(path: str | Path, rec: TradeRecord) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")


def load_records(path: str | Path) -> list[TradeRecord]:
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(TradeRecord(**json.loads(line)))
    return out


# --- klasifikace jednoho obchodu ----------------------------------------------
def classify(rec: TradeRecord) -> tuple[list[str], list[str]]:
    """Vrátí (chyby, dobré_vlastnosti)."""
    mistakes, good = [], []
    if rec.r_multiple <= 0:
        if rec.reason == "stop" and rec.bars_held <= QUICK_STOP_BARS:
            mistakes.append("quick_stop")
        if rec.mfe_r >= GAVE_BACK_MFE_R:
            mistakes.append("gave_back")
        if rec.context.get("stretch") == ">2ATR":
            mistakes.append("chased")
        if rec.mfe_r < NEVER_WORKED_MFE_R:
            mistakes.append("never_worked")
    else:
        if rec.reason == "take_profit":
            good.append("take_profit")
        if rec.mae_r > -0.5:
            good.append("clean_win")
    if rec.reason == "news_panic":
        mistakes.append("news_exit")
    return mistakes, good


# --- agregace -----------------------------------------------------------------
def _stats(rs: list[float]) -> dict:
    wins = [r for r in rs if r > 0]
    return {"n": len(rs), "win_rate": round(len(wins) / len(rs), 3) if rs else 0.0,
            "avg_r": round(sum(rs) / len(rs), 3) if rs else 0.0, "total_r": round(sum(rs), 2)}


def group(records: Iterable[TradeRecord], keys: Callable[[TradeRecord], Iterable[str]]) -> dict:
    buckets: dict[str, list[float]] = defaultdict(list)
    for r in records:
        for k in keys(r):
            buckets[k].append(r.r_multiple)
    return {k: _stats(v) for k, v in sorted(buckets.items())}


def analyze(records: list[TradeRecord]) -> dict:
    mistakes, goods = defaultdict(list), defaultdict(list)
    for r in records:
        m, g = classify(r)
        for label in m:
            mistakes[label].append(r)
        for label in g:
            goods[label].append(r)
    losers = [r for r in records if r.r_multiple <= 0]
    ranked = sorted(records, key=lambda r: r.r_multiple)
    return {
        "overall": _stats([r.r_multiple for r in records]),
        "by_source": group(records, lambda r: [r.source]),
        "by_pattern": group(records, lambda r: [p for p in r.patterns.split(",") if p] or ["(žádný)"]),
        "by_reason": group(records, lambda r: [r.reason]),
        "by_context": {f: group(records, lambda r, f=f: [str(r.context.get(f, "?"))]) for f in CONTEXT_FEATURES},
        "mistakes": {k: {"count": len(v), "share_of_losers": round(len(v) / len(losers), 3) if losers else 0.0,
                         "lost_r": round(sum(x.r_multiple for x in v), 2)} for k, v in mistakes.items()},
        "good": {k: {"count": len(v), "won_r": round(sum(x.r_multiple for x in v), 2)} for k, v in goods.items()},
        "worst": [_brief(r) for r in ranked[:5]],
        "best": [_brief(r) for r in ranked[::-1][:5]],
        "losers": len(losers),
    }


def _brief(r: TradeRecord) -> dict:
    m, g = classify(r)
    return {"entry_time": r.entry_time, "r": r.r_multiple, "mfe_r": r.mfe_r, "reason": r.reason,
            "patterns": r.patterns, "context": r.context, "labels": m + g, "source": r.source}


# --- odvození adaptací --------------------------------------------------------
def derive_adaptations(report: dict, min_trades: int = 15, bad_avg_r: float = -0.1) -> dict:
    reasons: list[str] = []
    disabled = []
    for name, s in report["by_pattern"].items():
        if name != "(žádný)" and s["n"] >= min_trades and s["avg_r"] < 0:
            disabled.append(name)
            reasons.append(f"pattern {name}: {s['n']} obchodů, průměr {s['avg_r']:+.2f}R → vypnout")

    candidates = []
    for feature, buckets in report["by_context"].items():
        bad = [(b, s) for b, s in buckets.items() if s["n"] >= min_trades and s["avg_r"] <= bad_avg_r]
        # nikdy nezablokovat všechny přihrádky jedné vlastnosti
        if bad and len(bad) < len(buckets):
            candidates += [(s["avg_r"], f"{feature}={b}", s) for b, s in bad]
    blocked = []
    for avg_r, key, s in sorted(candidates)[:MAX_BLOCKED_CONTEXTS]:
        blocked.append(key)
        reasons.append(f"situace {key}: {s['n']} obchodů, průměr {avg_r:+.2f}R → nevstupovat")

    breakeven = None
    gb = report["mistakes"].get("gave_back", {})
    if report["losers"] >= min_trades // 2 and gb.get("share_of_losers", 0) >= BREAKEVEN_GAVE_BACK_SHARE:
        breakeven = 1.0
        reasons.append(f"{gb['count']} ztrátových obchodů bylo předtím ≥1R v zisku → posouvat stop na nákupku při +1R")

    return {"disabled_patterns": disabled, "blocked_contexts": blocked,
            "breakeven_at_r": breakeven, "reasons": reasons}


def is_noop(adapt: dict) -> bool:
    return not (adapt.get("disabled_patterns") or adapt.get("blocked_contexts") or adapt.get("breakeven_at_r"))


# --- report -------------------------------------------------------------------
def _table(title: str, rows: dict) -> list[str]:
    out = [f"### {title}", "", "| | obchodů | úspěšnost | průměr R | celkem R |", "|---|---:|---:|---:|---:|"]
    for k, s in sorted(rows.items(), key=lambda kv: -kv[1]["total_r"]):
        out.append(f"| {k} | {s['n']} | {s['win_rate']*100:.0f} % | {s['avg_r']:+.2f} | {s['total_r']:+.1f} |")
    return out + [""]


def render_markdown(report: dict, adapt: dict | None = None, validation: dict | None = None,
                    title: str = "Rozbor obchodů") -> str:
    o = report["overall"]
    lines = [f"# {title}", "",
             f"**Obchodů:** {o['n']} · **úspěšnost:** {o['win_rate']*100:.0f} % · "
             f"**průměr:** {o['avg_r']:+.2f}R · **celkem:** {o['total_r']:+.1f}R", ""]
    lines += _table("Podle zdroje", report["by_source"])
    lines += ["## Opakované chyby", ""]
    if report["mistakes"]:
        for k, m in sorted(report["mistakes"].items(), key=lambda kv: kv[1]["lost_r"]):
            lines.append(f"- **{MISTAKE_LABELS.get(k, k)}** – {m['count']}× "
                         f"({m['share_of_losers']*100:.0f} % ztrát), {m['lost_r']:+.1f}R")
    else:
        lines.append("- žádné")
    lines += ["", "## Co fungovalo", ""]
    for k, g in report["good"].items():
        lines.append(f"- **{GOOD_LABELS.get(k, k)}** – {g['count']}×, {g['won_r']:+.1f}R")
    lines += [""] + _table("Podle patternu", report["by_pattern"]) + _table("Podle důvodu výstupu", report["by_reason"])
    for f, rows in report["by_context"].items():
        lines += _table(f"Kontext: {f}", rows)
    for name, key in (("5 nejhorších obchodů", "worst"), ("5 nejlepších obchodů", "best")):
        lines += [f"## {name}", ""]
        for t in report[key]:
            lines.append(f"- {t['entry_time']} ({t['source']}) **{t['r']:+.2f}R**, MFE {t['mfe_r']:+.2f}R, "
                         f"{t['reason']}, {t['patterns'] or '-'}, {t['context']} {t['labels']}")
        lines.append("")
    if adapt is not None:
        lines += ["## Závěry pro pravidla", ""]
        lines += [f"- {r}" for r in adapt["reasons"]] or ["- beze změn (málo dat nebo žádný jasný problém)"]
        lines.append("")
    if validation:
        verdict = ("PŘIJATO" if validation["accepted"]
                   else "BEZE ZMĚN" if validation["why"] == "není co měnit" else "ZAMÍTNUTO")
        lines += ["## Ověření na datech, ze kterých se agent neučil", "",
                  f"- **{verdict}** – {validation['why']}",
                  f"- původní pravidla: {validation['baseline']}",
                  f"- upravená pravidla: {validation['candidate']}", ""]
    return "\n".join(lines)
