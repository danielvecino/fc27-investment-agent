"""Measure official announcements and rumours separately against later prices."""
from __future__ import annotations

import csv
from datetime import timedelta
from pathlib import Path

from advisor import HORIZONS, future_price, load_rows, parse_time, write_csv


def build_event_reactions(data_dir: Path) -> None:
    event_file = data_dir / "events.csv"
    if not event_file.exists():
        return
    events = list(csv.DictReader(event_file.open(encoding="utf-8")))
    prices = load_rows(data_dir / "market_prices.csv")
    histories = {}
    for row in prices: histories.setdefault(row["card_id"], []).append(row)
    for history in histories.values(): history.sort(key=lambda r: r["ts"])
    reactions = []
    for event in events:
        if not event.get("event_id") or event.get("status") not in {"RUMOUR", "CONFIRMED", "RELEASED", "FALSE"}:
            continue
        at = parse_time(event["detected_at"])
        target_ids = {x.strip() for x in event.get("affected_players", "").split("|") if x.strip().startswith("27-")}
        for card_id in target_ids:
            history = histories.get(card_id, [])
            baseline = next((r for r in reversed(history) if r["ts"] <= at), None)
            if not baseline: continue
            row = {"event_id":event["event_id"], "event_status":event["status"], "source":event.get("source", ""), "source_confidence":event.get("source_confidence", ""), "card_id":card_id, "detected_at":event["detected_at"], "price_at_detection":baseline["price"]}
            for label, hours in HORIZONS.items():
                observed = future_price(history, at + timedelta(hours=hours), max(12, hours // 4))
                row[f"reaction_{label}_pct"] = round((observed["price"] / baseline["price"] - 1) * 100, 3) if observed else ""
                row[f"reaction_{label}_at"] = observed["timestamp_utc"] if observed else ""
            reactions.append(row)
    fields = ["event_id","event_status","source","source_confidence","card_id","detected_at","price_at_detection","reaction_4h_pct","reaction_4h_at","reaction_24h_pct","reaction_24h_at","reaction_3d_pct","reaction_3d_at","reaction_7d_pct","reaction_7d_at"]
    write_csv(data_dir / "event_reactions.csv", fields, reactions)


if __name__ == "__main__":
    import sys
    build_event_reactions(Path(sys.argv[1] if len(sys.argv) > 1 else "data"))
