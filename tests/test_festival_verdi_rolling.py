"""Festival Verdi's official edition index is independent from the Teatro Regio season."""
import json
import unittest
from datetime import date
from pathlib import Path

from opera_atlas.festival_verdi_future import (
    edition_year, next_edition, eligible_detail, extract_index,
)
from scripts.discover_season_indexes import eligible, extract, validate_config
from scripts.rollover_season_indexes import next_index

ROOT = Path(__file__).resolve().parents[1]
INDEX = "https://teatroregioparma.it/categoria-spettacoli/edizione-27-festival-verdi/"
HTML = """<html><header><a href="/spettacolo/il-pipistrello/">IL PIPISTRELLO</a></header>
<h1>Festival Verdi</h1><p>Parma e Busseto 1-24 ottobre 2027</p>
<a href="/spettacolo/aroldo/">AROLDO</a>
<a href="/spettacolo/la-traviata/">LA TRAVIATA</a>
<a href="/spettacolo/stiffelio/">STIFFELIO</a>
<a href="/spettacolo/gala-verdiano/">GALA VERDIANO</a>
<a href="/spettacolo/nabucco-canto-del-mondo-mutilato/">NABUCCO CANTO DEL MONDO MUTILATO</a>
</html>"""


class FestivalVerdiRollingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = next(s for s in validate_config(json.loads(
            (ROOT / "data/season-index-config.json").read_text(encoding="utf-8")))
            if s["key"] == "festival-verdi-rolling")

    def test_index_has_only_festival_operas_not_regio_season(self):
        expected = [
            "https://teatroregioparma.it/spettacolo/aroldo/",
            "https://teatroregioparma.it/spettacolo/la-traviata/",
            "https://teatroregioparma.it/spettacolo/stiffelio/",
        ]
        self.assertEqual(extract_index(HTML, url=INDEX, min_links=3), expected)
        self.assertEqual(extract("festival-verdi-rolling", INDEX, HTML, 3), expected)

    def test_strict_index_year_and_detail_hosts(self):
        self.assertEqual(edition_year(INDEX), 2027)
        self.assertEqual(next_edition(INDEX),
                         "https://teatroregioparma.it/categoria-spettacoli/edizione-28-festival-verdi/")
        self.assertTrue(eligible("festival-verdi-rolling",
                                 "https://teatroregioparma.it/spettacolo/aroldo/"))
        for bad in ("https://example.com/spettacolo/aroldo/",
                    "https://teatroregioparma.it/categoria-spettacoli/opera/",
                    "https://teatroregioparma.it/spettacolo/aroldo/?date=1"):
            self.assertFalse(eligible_detail(bad))
        with self.assertRaises(ValueError):
            edition_year("https://teatroregioparma.it/categoria-spettacoli/opera/")
        with self.assertRaises(ValueError):
            extract_index(HTML.replace("<h1>Festival Verdi</h1>", "<h1>Opera</h1>"),
                          url=INDEX, min_links=3)

    def test_rollover_never_replaces_unverified_edition(self):
        self.assertEqual(next_index(self.source, today=date(2027, 8, 31)), None)
        self.assertEqual(next_index(self.source, today=date(2027, 9, 1)),
                         "https://teatroregioparma.it/categoria-spettacoli/edizione-28-festival-verdi/")
        # The rollover pipeline checks live source availability and a nonempty
        # edition-specific index before it changes the active URL.

    def test_editorial_festival_identity_is_not_generic_parma_season(self):
        config = json.loads((ROOT / "data/festival-registry.json").read_text(encoding="utf-8"))
        rule = next(f for f in config["festivals"] if f["id"] == "festival-verdi")
        self.assertEqual(len(rule["official_event_urls"]), 3)
        self.assertNotIn("https://teatroregioparma.it/spettacolo/rigoletto/",
                         rule["official_event_urls"])


if __name__ == "__main__":
    unittest.main()
