"""Safety contracts for the Teatro Alfonso Rendano official opera source."""
import json
import unittest

from opera_atlas.cosenza_rendano_opera import (
    INDEX,KEY,eligible_detail,extract_index,parse_detail,
)
from scripts.discover_season_indexes import CONFIG,validate_config,eligible,extract
from scripts.collect_candidate_details import parse_source_credited_opera_detail

DETAIL="https://www.teatrorendanocosenza.it/il-barbiere-di-siviglia-2026/"

def page(title="Il barbiere di Siviglia",category="Opera lirica",
         composer="Gioachino Rossini",venue="Teatro Alfonso Rendano",
         when="10/11/2026 ore 20.30"):
    return (f"<html><h1>{title}</h1><main><p>{category}</p>"
            f"<p>musica di {composer}</p><p>{venue}</p>"
            f"<p>{when}</p></main></html>")

class CosenzaRendanoTests(unittest.TestCase):
    def test_evergreen_source_is_explicitly_configured(self):
        d=json.loads(CONFIG.read_text(encoding="utf-8"))
        source=next(x for x in validate_config(d) if x["key"]==KEY)
        self.assertEqual(source["url"],INDEX)
        self.assertTrue(eligible_detail(DETAIL))
        self.assertTrue(eligible(KEY,DETAIL))
        self.assertFalse(eligible_detail(INDEX))
        for bad in (
            "http://www.teatrorendanocosenza.it/il-barbiere-di-siviglia-2026/",
            "https://evil.example/il-barbiere-di-siviglia-2026/",
            DETAIL+"?preview=1", DETAIL+"#notes",
            "https://www.teatrorendanocosenza.it/danza-2026/",
            "https://www.teatrorendanocosenza.it/calendario/",
        ):
            self.assertFalse(eligible_detail(bad))

    def test_index_excludes_ballet_and_other_sites(self):
        html=('<a href="/il-barbiere-di-siviglia-2026/">opera</a>'
              '<a href="/danza-2026/">danza</a>'
              '<a href="https://evil.example/opera/">other</a>')
        self.assertEqual(extract_index(html),[DETAIL])
        self.assertEqual(extract(KEY,INDEX,html,1),[DETAIL])
        with self.assertRaises(ValueError):
            extract_index('<a href="/danza-2026/">ballet</a>')

    def test_evidence_requires_composer_theatre_and_clock(self):
        title,composer,venue,recite=parse_detail(page(),url=DETAIL)
        self.assertEqual((title,composer,venue),
                         ("Il barbiere di Siviglia","Gioachino Rossini",
                          "Teatro Alfonso Rendano"))
        self.assertEqual(recite,[("2026-11-10","20:30")])
        facts=parse_source_credited_opera_detail(KEY,DETAIL,page())
        self.assertEqual(facts[0]["starts_at"],"2026-11-10T20:30:00+01:00")

    def test_rolling_future_season_without_fixed_year(self):
        result=parse_detail(page(when="11 dicembre 2027 ore 19:00"),url=DETAIL)
        self.assertEqual(result[3],[("2027-12-11","19:00")])

    def test_fail_closed_for_ballet_gala_missing_credit_and_school(self):
        samples=(
            page(title="Il barbiere di Siviglia ballet"),
            page(title="Gala lirico"),
            page(category="Danza contemporanea"),
            page(composer="Anonimo"),
            page(venue="Teatro Auditorium Unical"),
            page(when="10/11/2026"),
            page(when="40/11/2026 ore 20:30"),
            page(title="Laboratorio per le scuole"),
        )
        for html in samples:
            with self.subTest(html=html[:80]):
                with self.assertRaises(ValueError):
                    parse_detail(html,url=DETAIL)

if __name__=="__main__":
    unittest.main()
