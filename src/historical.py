"""Validation helpers for importing verifiable FC25/FC26 price history.

Attribute-only player datasets are deliberately rejected: a historical row must
contain a timestamp, price, platform, source and stable card id.
"""
from __future__ import annotations
import csv
from datetime import datetime

REQUIRED = {"edition", "platform", "card_id", "observed_at", "price", "source", "source_url"}

def load_verified_history(path: str, target_platform: str = "PC") -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return []
    missing = REQUIRED - set(rows[0])
    if missing:
        raise ValueError(f"historical data missing required fields: {sorted(missing)}")
    out = []
    for row in rows:
        if row["platform"].upper() != target_platform.upper():
            continue
        if not row["source"].strip() or not row["source_url"].startswith("http"):
            raise ValueError("historical rows require a source and source_url")
        datetime.fromisoformat(row["observed_at"].replace("Z", "+00:00"))
        price = float(row["price"])
        if price <= 0 or not row["card_id"].strip():
            raise ValueError("historical rows require positive price and card_id")
        out.append(row)
    return out
