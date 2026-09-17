import sys
import unittest
import io
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from advisor import independent_rows, market_data_hash, round_up_tick
from advisor import asof_price, break_even_buy
from outcomes import build_outcomes


class AdvisorTests(unittest.TestCase):
    def test_duplicate_market_hash_does_not_become_evidence(self):
        start = datetime(2026, 9, 14, tzinfo=timezone.utc)
        rows = []
        for number in range(13):
            price = 1000 + number if number < 12 else 850
            sample = {"card_id":"27-x", "rating":84, "position":"ST", "price":price}
            digest = market_data_hash([sample])
            rows.append({"timestamp_utc":(start + timedelta(hours=4*number)).isoformat(), "ts":start + timedelta(hours=4*number), "snapshot_id":f"s{number}", "market_data_sha256":digest, **sample})
        duplicate = dict(rows[-1]); duplicate["snapshot_id"] = "duplicate"; rows.append(duplicate)
        self.assertEqual(len(independent_rows(rows)), 13)
        self.assertEqual(round_up_tick(1001), 1100)

    def test_no_future_price_in_features(self):
        t = datetime(2026, 9, 14, tzinfo=timezone.utc)
        self.assertIsNone(asof_price([{'ts': t + timedelta(seconds=1), 'price': 1000}], t))

    def test_tick_at_band_boundary(self):
        self.assertEqual(break_even_buy(1000), 950)
        self.assertEqual(break_even_buy(10000), 9500)

    def test_pending_outcomes_fill_on_later_run(self):
        t = datetime(2026, 9, 14, tzinfo=timezone.utc)
        captured = []
        texts = {
            'advisor_watchlist.csv': 'timestamp_utc,card_id,signal\n',
            'signal_outcomes.csv': 'timestamp_utc,card_id,name,entry_price,signal,confidence\n' + t.isoformat() + ',27-x,Test,1000,WATCH_BUY,70\n',
        }
        rows = [{'card_id':'27-x', 'ts':t + timedelta(hours=24), 'timestamp_utc':(t + timedelta(hours=24)).isoformat(), 'price':1200}]
        with patch('outcomes.load_rows', return_value=rows), patch.object(Path, 'exists', return_value=True), patch.object(Path, 'open', lambda p, **kw: io.StringIO(texts[p.name])), patch('outcomes.write_csv', side_effect=lambda p,f,r: captured.extend(r)):
            build_outcomes(Path('data'))
        self.assertEqual(captured[0]['outcome_24h_pct'], 14.0)
        self.assertEqual(captured[0]['outcome_3d_price'], '')


if __name__ == "__main__":
    unittest.main()
