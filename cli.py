"""Interactive CLI for SMT signal scanning.

Usage:
    python cli.py                          # default: SPY_QQQ, last ~1 year
    python cli.py --pair TSMC_0050 --mode scan
    python cli.py --list-pairs
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

import yaml

from data import YFinanceLoader, TwYFinanceLoader, align
from signals import scan_signals, TradeSignal


CONFIG_PATH = Path(__file__).resolve().parent / "config" / "pairs.yaml"


def _load_pairs() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))["pairs"]


def _loader(market: str):
    return YFinanceLoader() if market == "US" else TwYFinanceLoader()


def _format_signal_row(s: TradeSignal) -> str:
    icon = {"actionable": "✓", "pending_confirmation": "…", "expired": "x"}[s.status]
    return (
        f"{icon} {str(s.timestamp.date()):<12}"
        f" {s.direction.upper():<8}"
        f" {s.status:<22}"
        f" entry={s.entry:>9.2f}"
        f" stop={s.stop:>9.2f}"
        f" target={s.target:>9.2f}"
        f" R:R={s.rr_ratio:<4.1f}"
        f" age={s.age_bars:>3}"
        f"  {s.note}"
    )


def _print_table(signals: list[TradeSignal]) -> None:
    header = (
        f"  {'Date':<12} {'Dir':<8} {'Status':<22}"
        f" {'Entry':>10} {'Stop':>10} {'Target':>10} {'R:R':<5} {'Age':>4}  Note"
    )
    print(header)
    print("  " + "-" * (len(header) - 2))
    for s in signals:
        print(_format_signal_row(s))


def _print_latest(signals: list[TradeSignal]) -> None:
    actionable = [s for s in signals if s.status == "actionable"]
    if not actionable:
        pending = [s for s in signals if s.status == "pending_confirmation"]
        if pending:
            latest = max(pending, key=lambda s: s.timestamp)
            print(">>> NO ACTIONABLE SIGNAL — latest pending:")
            print("    " + _format_signal_row(latest))
        else:
            print(">>> 目前無 SMT 訊號")
        return
    latest = max(actionable, key=lambda s: s.timestamp)
    print(">>> LATEST ACTIONABLE SIGNAL")
    print(
        f"    {str(latest.timestamp.date())}  {latest.direction.upper()}"
        f"  entry={latest.entry:.2f}  stop={latest.stop:.2f}"
        f"  target={latest.target:.2f}  R:R={latest.rr_ratio:.1f}"
    )
    print(f"    ✓ {latest.note}")
    print("    ! 訊息僅供參考,非投資建議")


def main() -> int:
    pairs = _load_pairs()

    parser = argparse.ArgumentParser(
        description="SMT signal scanner (not investment advice)."
    )
    parser.add_argument("--pair", default="SPY_QQQ", help="pair name from config/pairs.yaml")
    parser.add_argument("--start", default=None, help="YYYY-MM-DD (default: 1 year ago)")
    parser.add_argument("--end", default=None, help="YYYY-MM-DD (default: today)")
    parser.add_argument("--timeframe", default="1d", help="1d / 1h / 4h (TW only 1d)")
    parser.add_argument("--swing-window", type=int, default=5)
    parser.add_argument("--rr-ratio", type=float, default=2.0)
    parser.add_argument("--signal-ttl", type=int, default=10)
    parser.add_argument(
        "--no-confirmation",
        action="store_true",
        help="show all SMT events, even without BOS/CHOCH confirmation",
    )
    parser.add_argument(
        "--mode",
        choices=["latest", "scan"],
        default="latest",
        help="latest: only most recent actionable; scan: list all",
    )
    parser.add_argument("--list-pairs", action="store_true", help="list available pairs and exit")
    args = parser.parse_args()

    if args.list_pairs:
        print("Available pairs:")
        for name, cfg in pairs.items():
            print(
                f"  {name:<14} market={cfg['market']:<3}"
                f" {cfg['primary']} / {cfg['reference']}"
                f"  ({cfg.get('correlation', 'positive')})"
            )
        return 0

    if args.pair not in pairs:
        print(f"ERROR: unknown pair '{args.pair}'. Use --list-pairs to see options.")
        return 2

    today = date.today()
    end = args.end or today.isoformat()
    start = args.start or (today - timedelta(days=365)).isoformat()

    cfg = pairs[args.pair]
    print(
        f"Fetching {args.pair}: {cfg['primary']} / {cfg['reference']}"
        f" ({cfg['market']}) {start} → {end} [{args.timeframe}]"
    )
    loader = _loader(cfg["market"])
    try:
        a = loader.fetch(cfg["primary"], start, end, args.timeframe)
        b = loader.fetch(cfg["reference"], start, end, args.timeframe)
    except Exception as exc:
        print(f"ERROR: data fetch failed: {exc}")
        return 1

    a, b = align(a, b)
    if len(a) < args.swing_window * 2 + 3:
        print(f"ERROR: insufficient bars after alignment ({len(a)}).")
        return 1

    signals = scan_signals(
        a,
        b,
        swing_window=args.swing_window,
        rr_ratio=args.rr_ratio,
        signal_ttl=args.signal_ttl,
        correlation=cfg.get("correlation", "positive"),
    )

    print(f"\nScanned {len(a)} bars → {len(signals)} SMT event(s)\n")

    if args.mode == "scan":
        if not signals:
            print("(no SMT events found)")
        else:
            _print_table(signals)
        print()
        _print_latest(signals)
    else:
        _print_latest(signals)

    print("\n! 本工具僅為訊號提示,非投資建議。交易自負盈虧。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
