"""Both Haydn performances share one source-verified new opera identity."""
import json
import unittest
from pathlib import Path

from scripts.auto_catalogue import official_identity_candidates

URLS = (
    "https://www.haydn.it/eventi/cronaca-di-un-amore-callas-e-pasolini",
    "https://www.haydn.it/eventi/cronaca-di-un-amore-callas-e-pasolini-2",
)
IDS = (
    "oa-index-5fea5e594da012daa488",
    "oa-index-b4aaa5341d6c996550c0",
)


class CronacaAuthorityTests(unittest.TestCase):
    def test_both_dates_share_canonical_identity(self):
        seeds = json.loads(Path("data/verified-work-authority-seeds.json").read_text())["works"]
        matches = [row for row in seeds if row.get("source_url") in URLS]
        self.assertEqual(len(matches), 2)
        for row in matches:
            self.assertEqual(row["title"], "Cronaca di un amore. Callas e Pasolini")
            self.assertEqual(row["composer"], "Davide Tramontano")
            self.assertEqual(row["history"]["librettist"], "Alberto Mattioli")
            self.assertEqual(row["history"]["premiere_year"], 2026)
            self.assertEqual(row["history"]["premiere_city"], "Piacenza")

        evidence = {
            "schema_version": 1,
            "evidence": [
                {"candidate_id": cid, "source_key": "haydn-rolling-opera",
                 "source_url": url, "status": "needs_editorial_review",
                 "event_facts": [{
                     "event_title": "Cronaca di un amore. Callas e Pasolini",
                     "composer": "Davide Tramontano", "venue": "Teatro Sociale",
                     "date": date, "starts_at": instant,
                 }]}
                for cid, url, date, instant in (
                    (IDS[0], URLS[0], "2027-01-29", "2027-01-29T20:00:00+01:00"),
                    (IDS[1], URLS[1], "2027-01-31", "2027-01-31T16:00:00+01:00"),
                )
            ]
        }
        queue = {"schema_version": 1, "candidates": [
            {"id": cid, "source_key": "haydn-rolling-opera",
             "official_url": url, "status": "needs_review"}
            for cid, url in zip(IDS, URLS)
        ]}
        result = official_identity_candidates(evidence, queue,
                                               {"schema_version": 1, "works": []})
        works = result["works"]
        self.assertEqual(len(works), 2)
        self.assertEqual({w["title"] for w in works},
                         {"Cronaca di un amore. Callas e Pasolini"})
        self.assertEqual({w["composer"] for w in works}, {"Davide Tramontano"})
        self.assertEqual({w["history"]["premiere_year"] for w in works}, {2026})


if __name__ == "__main__":
    unittest.main()
