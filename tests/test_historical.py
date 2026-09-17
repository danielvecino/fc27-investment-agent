import csv, tempfile, unittest
from src.historical import load_verified_history

class HistoricalValidationTests(unittest.TestCase):
    def test_filters_non_pc_and_requires_provenance(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
            w = csv.DictWriter(f, fieldnames=["edition","platform","card_id","observed_at","price","source","source_url"])
            w.writeheader()
            w.writerow({"edition":"FC26","platform":"PC","card_id":"x","observed_at":"2025-09-20T12:00:00Z","price":"1000","source":"FUTBIN","source_url":"https://example.test/x"})
            w.writerow({"edition":"FC26","platform":"PS","card_id":"y","observed_at":"2025-09-20T12:00:00Z","price":"900","source":"FUTBIN","source_url":"https://example.test/y"})
            path = f.name
        self.assertEqual(len(load_verified_history(path)), 1)
