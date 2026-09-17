"""Conservative, no-trade FC27 market advisor.

This module never places orders.  It turns independent FUT.GG market snapshots
into an explainable watchlist and records evidence for later evaluation.
"""
from __future__ import annotations

import csv
import hashlib
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

EA_TAX = 0.05
HORIZONS = {"4h": 4, "24h": 24, "3d": 72, "7d": 168}


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def market_tick(price: float) -> int:
    """EA transfer-market price step by price band (kept in one auditable place)."""
    if price < 1_000:
        return 50
    if price < 10_000:
        return 100
    if price < 50_000:
        return 250
    if price < 100_000:
        return 500
    return 1_000


def round_up_tick(price: float) -> int:
    step = market_tick(price)
    return int(math.ceil(price / step) * step)


def break_even_buy(target_sale: int) -> int:
    """Maximum buy price that breaks even after EA's 5% tax, tick-rounded."""
    net = target_sale * (1 - EA_TAX)
    return int(math.floor(net / market_tick(net)) * market_tick(net))


def market_data_hash(rows: Iterable[dict]) -> str:
    """Hash parsed market content, rather than volatile HTML or scrape time."""
    canonical = [
        (r["card_id"], int(r["rating"]), r["position"], int(r["price"]))
        for r in rows
    ]
    canonical.sort()
    return hashlib.sha256(repr(canonical).encode()).hexdigest()


def regime(at: datetime) -> str:
    # FC27 calendar. Dates are deliberately explicit and easy to revise next year.
    if at < datetime(2026, 9, 18, tzinfo=timezone.utc):
        return "PRE_EARLY_ACCESS"
    if at < datetime(2026, 9, 25, tzinfo=timezone.utc):
        return "EARLY_ACCESS"
    if at < datetime(2026, 10, 2, tzinfo=timezone.utc):
        return "LAUNCH_SHOCK"
    return "NORMALIZING"


def asof_price(history: list[dict], at: datetime, tolerance_hours: int = 14) -> dict | None:
    """Latest observation at/before a target; prevents future-data leakage."""
    eligible = [r for r in history if r["ts"] <= at and at - r["ts"] <= timedelta(hours=tolerance_hours)]
    return max(eligible, key=lambda r: r["ts"]) if eligible else None


def future_price(history: list[dict], after: datetime, tolerance_hours: int) -> dict | None:
    eligible = [r for r in history if r["ts"] >= after and r["ts"] - after <= timedelta(hours=tolerance_hours)]
    return min(eligible, key=lambda r: r["ts"]) if eligible else None


def pct(now: int, then: dict | None) -> float | None:
    return round((now / then["price"] - 1) * 100, 3) if then and then["price"] else None


def segment_for(row: dict, rating_medians: dict[int, float]) -> str:
    """Only classify what current input supports; promos remain unknown without card type."""
    med = rating_medians.get(row["rating"], row["price"])
    if 81 <= row["rating"] <= 88 and row["price"] <= max(20_000, med * 2):
        return "fodder"
    if row["price"] >= max(50_000, med * 2.5):
        return "meta"
    return "other"


def independent_rows(rows: list[dict]) -> list[dict]:
    """One observation per parsed market hash, never per scraper run."""
    by_snapshot = defaultdict(list)
    for row in rows:
        by_snapshot[row["snapshot_id"]].append(row)
    seen, kept = set(), []
    for snapshot_rows in sorted(by_snapshot.values(), key=lambda rs: rs[0]["ts"]):
        digest = snapshot_rows[0].get("market_data_sha256") or market_data_hash(snapshot_rows)
        if digest in seen:
            continue
        seen.add(digest)
        kept.extend(snapshot_rows)
    return kept


def load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["price"] = int(row["price"])
        row["rating"] = int(row["rating"])
        row["ts"] = parse_time(row["timestamp_utc"])
    return independent_rows(rows)


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_advisor(data_dir: Path) -> list[dict]:
    rows = load_rows(data_dir / "market_prices.csv")
    if not rows:
        raise ValueError("Sin datos de mercado")
    by_snapshot, by_card = defaultdict(list), defaultdict(list)
    for row in rows:
        by_snapshot[row["snapshot_id"]].append(row)
        by_card[row["card_id"]].append(row)
    for history in by_card.values():
        history.sort(key=lambda r: r["ts"])
    latest = max(by_snapshot.values(), key=lambda rs: rs[0]["ts"])
    now = latest[0]["ts"]
    rating_prices = defaultdict(list)
    for row in latest:
        rating_prices[row["rating"]].append(row["price"])
    rating_medians = {rating: statistics.median(values) for rating, values in rating_prices.items()}
    snapshot_count = len(by_snapshot)
    output = []
    for current in latest:
        history = by_card[current["card_id"]]
        prices = [r["price"] for r in history]
        n, span = len(history), (history[-1]["ts"] - history[0]["ts"]).total_seconds() / 3600
        recent = prices[-min(6, n):]
        recent_med = statistics.median(recent)
        returns = [math.log(b / a) for a, b in zip(prices, prices[1:]) if a > 0 and b > 0]
        volatility = statistics.pstdev(returns) if len(returns) >= 2 else None
        persistence = sum(abs(p / recent_med - 1) <= .15 for p in recent) / len(recent) if n >= 3 else 0
        coverage = sum(asof_price(history, now - timedelta(hours=h)) is not None for h in HORIZONS.values())
        availability = n / snapshot_count
        density = len(rating_prices[current["rating"]])
        liquidity = round(100 * (0.45 * availability + 0.35 * persistence + 0.20 * min(density / 10, 1)))
        liquidity = round(liquidity * min(n / 12, span / 48, 1))
        confidence = round(100 * (0.40 * min(n / 12, 1) + 0.25 * min(span / 48, 1) + 0.20 * persistence + 0.15 * availability) * (1 - .30 * min((volatility or 0) / .35, 1)))
        features = {label: pct(current["price"], asof_price(history, now - timedelta(hours=hours))) for label, hours in HORIZONS.items()}
        rating_med = rating_medians[current["rating"]]
        relative_rating = round((current["price"] / rating_med - 1) * 100, 3) if rating_med else None
        target_sale = round_up_tick(recent_med)
        net_roi = round(((target_sale * (1 - EA_TAX)) / current["price"] - 1) * 100, 3)
        has_temporal_evidence = n >= 12 and span >= 48 and coverage >= 2 and features["24h"] is not None
        signal, reason = "WAIT", "histórico o cobertura temporal insuficientes"
        if has_temporal_evidence:
            confirmed_discount = len(history) >= 2 and (history[-1]["ts"] - history[-2]["ts"]).total_seconds() >= 7200 and all(p <= recent_med * .90 for p in prices[-2:])
            if confidence >= 60 and liquidity >= 45 and confirmed_discount and (features["24h"] or 0) <= -8 and net_roi >= 8:
                signal = "WATCH_BUY"
                reason = "descuento 24h persistente, liquidez inferida suficiente y margen neto tras impuesto"
            else:
                reason = "sin descuento confirmado o margen neto suficiente"
        output.append({
            "timestamp_utc": now.isoformat(), "snapshot_id": current["snapshot_id"], "market_data_sha256": market_data_hash(latest),
            "card_id": current["card_id"], "name": current["name"], "rating": current["rating"], "position": current["position"],
            "segment": segment_for(current, rating_medians), "price": current["price"], "n_independent": n, "span_hours": round(span, 2),
            "coverage_windows": coverage, "return_4h_pct": features["4h"], "return_24h_pct": features["24h"], "return_3d_pct": features["3d"], "return_7d_pct": features["7d"],
            "rating_relative_pct": relative_rating, "persistence": round(persistence, 3), "volatility": round(volatility, 4) if volatility is not None else None,
            "liquidity_inferred": liquidity, "confidence": confidence, "regime": regime(now), "target_sale": target_sale,
            "break_even_buy": break_even_buy(target_sale), "net_roi_pct": net_roi, "signal": signal, "reason": reason,
        })
    output.sort(key=lambda r: (r["signal"] != "WATCH_BUY", -r["confidence"], -r["net_roi_pct"]))
    fields = list(output[0])
    write_csv(data_dir / "advisor_watchlist.csv", fields, output)
    report = ["# FC27 Advisor v0.1", "", f"Régimen: **{regime(now)}** · observaciones independientes: **{snapshot_count}**.", "", "> No compra ni vende automáticamente. Una señal sólo es una carta para revisar manualmente.", "", "## Watchlist", "", "| Carta | Segmento | Precio | 4h | 24h | 3d | 7d | Cobertura | Liquidez | Conf. | Objetivo | BE compra | Estado |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    def format_pct(value): return "—" if value is None else f"{value:+.1f}%"
    for row in output[:30]:
        report.append(f"| {row['name']} (`{row['card_id']}`) | {row['segment']} | {row['price']:,} | {format_pct(row['return_4h_pct'])} | {format_pct(row['return_24h_pct'])} | {format_pct(row['return_3d_pct'])} | {format_pct(row['return_7d_pct'])} | {row['coverage_windows']}/4 | {row['liquidity_inferred']} | {row['confidence']} | {row['target_sale']:,} | {row['break_even_buy']:,} | {row['signal']} |")
    (data_dir / "advisor_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    import sys
    build_advisor(Path(sys.argv[1] if len(sys.argv) > 1 else "data"))
