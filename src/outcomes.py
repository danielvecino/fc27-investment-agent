"""Append-only signal outcomes and event-reaction measurement, without leakage."""
from __future__ import annotations

import csv
from datetime import timedelta
from pathlib import Path

from advisor import HORIZONS, future_price, load_rows, parse_time, write_csv


def build_outcomes(data_dir: Path) -> None:
    prices = load_rows(data_dir / "market_prices.csv")
    histories = {}
    for row in prices:
        histories.setdefault(row["card_id"], []).append(row)
    for history in histories.values(): history.sort(key=lambda r: r["ts"])
    watchlist_path = data_dir / "advisor_watchlist.csv"
    signals = list(csv.DictReader(watchlist_path.open(encoding="utf-8"))) if watchlist_path.exists() else []
    existing_path = data_dir / "signal_outcomes.csv"
    existing = list(csv.DictReader(existing_path.open(encoding="utf-8"))) if existing_path.exists() else []
    keyed = {(r["timestamp_utc"], r["card_id"]) for r in existing}
    for signal in signals:
        if signal["signal"] != "WATCH_BUY" or (signal["timestamp_utc"], signal["card_id"]) in keyed:
            continue
        row = {"timestamp_utc": signal["timestamp_utc"], "card_id": signal["card_id"], "name": signal["name"], "entry_price": signal["price"], "signal": signal["signal"], "confidence": signal["confidence"]}
        existing.append(row)
        keyed.add((signal["timestamp_utc"], signal["card_id"]))
    for row in existing:
        baseline = parse_time(row["timestamp_utc"])
        history = histories.get(row["card_id"], [])
        for label, hours in {k:v for k,v in HORIZONS.items() if k != "4h"}.items():
            if row.get(f"outcome_{label}_at"):
                continue
            observed = future_price(history, baseline + timedelta(hours=hours), max(12, hours // 4))
            row[f"outcome_{label}_price"] = observed["price"] if observed else ""
            row[f"outcome_{label}_pct"] = round((observed["price"] * .95 / int(row["entry_price"]) - 1) * 100, 3) if observed else ""
            row[f"outcome_{label}_at"] = observed["timestamp_utc"] if observed else ""
    fields = ["timestamp_utc","card_id","name","entry_price","signal","confidence","outcome_24h_price","outcome_24h_pct","outcome_24h_at","outcome_3d_price","outcome_3d_pct","outcome_3d_at","outcome_7d_price","outcome_7d_pct","outcome_7d_at"]
    write_csv(existing_path, fields, existing)


if __name__ == "__main__":
    import sys
    build_outcomes(Path(sys.argv[1] if len(sys.argv) > 1 else "data"))
