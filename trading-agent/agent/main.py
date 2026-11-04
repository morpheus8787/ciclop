"""CLI: python -m agent.main {learn,backtest,review,news,run}"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from . import data, learn, news, selflearn
from .backtest import run_backtest
from .broker import ExchangeBroker, PaperBroker
from .bot import TradingAgent
from .config import config_from_env, load_dotenv
from .review import load_records
from .risk import RiskLimits
from .store import Store
from .strategy import StrategyParams

LEARNED_FILE = "learned_patterns.json"


def _base_params(cfg) -> StrategyParams:
    """Pravidla + naučené patterny, BEZ adaptací z rozboru (ty se odvozují vždy znovu)."""
    if cfg.strategy == "trend":
        return StrategyParams(kind="trend", stop_atr_mult=cfg.stop_atr_mult, take_profit_r=cfg.take_profit_r,
                              entry_period=cfg.entry_period, exit_period=cfg.exit_period,
                              trail_atr_mult=cfg.trail_atr_mult or None)
    base = StrategyParams(stop_atr_mult=cfg.stop_atr_mult, take_profit_r=cfg.take_profit_r)
    return base.with_learned(Path(cfg.state_dir) / LEARNED_FILE)


def _params(cfg) -> StrategyParams:
    return _base_params(cfg).with_adaptations(Path(cfg.state_dir) / selflearn.ADAPTATIONS_FILE)


def _run_review(cfg, ex, days: int) -> selflearn.SelfReview:
    df = data.fetch_history(ex, cfg.symbol, cfg.timeframe, days)
    live = load_records(Path(cfg.state_dir) / selflearn.TRADES_FILE)
    result = selflearn.self_review(df, _base_params(cfg), _limits(cfg), live, cfg.paper_start_equity,
                                   cfg.fee_rate, min_trades=cfg.adapt_min_trades)
    path = selflearn.save_review(result, cfg.state_dir)
    logging.getLogger(__name__).warning("Report rozboru uložen: %s (adaptace %s)", path,
                                        "PŘIJATY" if result.validation["accepted"] else "nepřijaty")
    return result


def _limits(cfg) -> RiskLimits:
    return RiskLimits(cfg.risk_per_trade, cfg.max_position_pct, cfg.max_order_quote,
                      cfg.max_daily_loss_pct, cfg.max_trades_per_day)


def cmd_learn(cfg, args):
    ex = data.make_market_data(cfg)
    df = data.fetch_history(ex, cfg.symbol, cfg.timeframe, args.days)
    report = learn.select_patterns(df, horizon=args.horizon)
    learn.save(report, Path(cfg.state_dir) / LEARNED_FILE)
    print(f"Svíček: {report['bars']}, horizont: {report['horizon']}")
    print(f"{'pattern':28} {'směr':8} {'počet':>6} {'win%':>6} {'edge%':>7} | test: {'počet':>5} {'win%':>6} {'edge%':>7}")
    test = {s["name"]: s for s in report["test"]}
    for s in report["train"]:
        t = test[s["name"]]
        mark = "  ✔" if s["name"] in report["selected_bullish"] + report["selected_bearish"] else ""
        print(f"{s['name']:28} {s['direction']:8} {s['count']:>6} {s['win_rate']*100:>6.1f} {s['mean_edge_pct']:>7.2f}"
              f" |       {t['count']:>5} {t['win_rate']*100:>6.1f} {t['mean_edge_pct']:>7.2f}{mark}")
    print("Vybrané bullish:", report["selected_bullish"] or "žádné → agent nebude otevírat obchody (žádný pattern neprokázal výhodu)")


def cmd_backtest(cfg, args):
    ex = data.make_market_data(cfg)
    df = data.fetch_history(ex, cfg.symbol, cfg.timeframe, args.days)
    res = run_backtest(df, _params(cfg), _limits(cfg), cfg.paper_start_equity, cfg.fee_rate)
    buy_hold = (df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100
    print(json.dumps({**res.summary(), "buy_and_hold_pct": round(buy_hold, 2)}, indent=2))
    for t in res.trades[-10:]:
        print(f"{t.entry_time:%Y-%m-%d %H:%M} → {t.exit_time:%Y-%m-%d %H:%M}  {t.reason:12} pnl {t.pnl:+8.2f}  {t.patterns}")


def cmd_review(cfg, args):
    ex = data.make_market_data(cfg)
    r = _run_review(cfg, ex, args.days)
    o = r.report["overall"]
    print(f"Obchodů v rozboru: {o['n']} (z toho skutečných: {r.live_report['overall']['n'] if r.live_report else 0})")
    print(f"Úspěšnost {o['win_rate']*100:.0f} %, průměr {o['avg_r']:+.2f}R")
    print("Opakované chyby:")
    for k, m in sorted(r.report["mistakes"].items(), key=lambda kv: kv[1]["lost_r"]):
        print(f"  - {k}: {m['count']}× ({m['lost_r']:+.1f}R)")
    print("Navržené úpravy:", *(r.adaptations["reasons"] or ["žádné"]), sep="\n  - ")
    print(f"Ověření: {'PŘIJATO' if r.validation['accepted'] else 'NEPŘIJATO'} – {r.validation['why']}")
    print(f"  původní:  {r.validation['baseline']}")
    print(f"  upravené: {r.validation['candidate']}")


def cmd_news(cfg, args):
    headlines, ok = news.fetch_headlines(cfg.news_feeds)
    a = news.assess(headlines, datetime.now(timezone.utc), cfg.news_lookback_hours,
                    (cfg.base_asset,), ok, cfg.news_fail_safe)
    print(f"Titulků: {len(headlines)}, feedy OK: {ok}, skóre: {a.score:+.1f}, blokace nákupů: {a.block_entries}, panika: {a.panic}")
    for r in a.reasons:
        print(" -", r)


def cmd_run(cfg, args):
    store = Store(cfg.state_dir)
    if cfg.mode == "paper":
        ex = data.make_market_data(cfg)
        paper = store.load().paper or {"cash": cfg.paper_start_equity, "base": 0.0}
        broker = PaperBroker(ex, cfg.symbol, paper["cash"], paper["base"], cfg.fee_rate)
    else:  # testnet/live: data i příkazy ze stejné burzy, ať sedí ceny s tím, co se skutečně plní
        ex = data.make_exchange(cfg)
        broker = ExchangeBroker(ex, cfg.symbol)
    def adapt():
        _run_review(cfg, ex, cfg.adapt_history_days)
        return _params(cfg)

    agent = TradingAgent(cfg, broker, store, _params(cfg),
                         bars_fn=lambda: data.fetch_recent(ex, cfg.symbol, cfg.timeframe), adapt_fn=adapt)
    agent.run_forever()


def main(argv=None):
    load_dotenv()
    p = argparse.ArgumentParser(prog="agent")
    sub = p.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("learn", help="změř, které patterny na trhu fungují")
    pl.add_argument("--days", type=int, default=730)
    pl.add_argument("--horizon", type=int, default=12)
    pb = sub.add_parser("backtest", help="otestuj strategii na historii")
    pb.add_argument("--days", type=int, default=365)
    pr = sub.add_parser("review", help="rozbor vlastních obchodů a učení z chyb")
    pr.add_argument("--days", type=int, default=730)
    sub.add_parser("news", help="aktuální vyhodnocení zpráv")
    sub.add_parser("run", help="spusť agenta (paper/testnet/live dle MODE)")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = config_from_env()
    {"learn": cmd_learn, "backtest": cmd_backtest, "review": cmd_review, "news": cmd_news, "run": cmd_run}[args.cmd](cfg, args)


if __name__ == "__main__":
    main()
