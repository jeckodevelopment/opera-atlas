"""Mantova first-party evergreen opera connector safety checks."""
import json
import unittest

from opera_atlas.mantova_sociale_opera import (
    INDEX, KEY, eligible_detail, extract_index, parse_detail,
)
from scripts.discover_season_indexes import CONFIG, validate_config, eligible, extract
from scripts.collect_candidate_details import parse_source_credited_opera_detail

DETAIL="https://www.teatrosocialemantova.it/it-it/la-traviata-v3.aspx?event=6A34D412-FDCE-46E7-A02C-2FEA0FFDD4EE"

def fixture(title="LA TRAVIATA", composer="Giuseppe Verdi",
            time="domenica 20 dicembre 2026 ore 17:30",
            venue="Teatro Sociale di Mantova",
            genre="repertorio operistico"):
    return (f"<html><h1>{title}</h1><p>{time}</p>"
            f"<section><h2>{title}</h2>"
            f"<p>Uno dei titoli del {genre}: La Traviata di {composer} "
            f"in scena al {venue}.</p>"
            "</section></html>")

class MantovaSocialeConnectorTests(unittest.TestCase):
    def test_exact_approved_evergreen_index_and_detail_urls(self):
        config=json.loads(CONFIG.read_text(encoding="utf-8"))
        record=next(x for x in validate_config(config) if x["key"]==KEY)
        self.assertEqual(record["url"],INDEX)
        self.assertTrue(eligible(KEY,DETAIL))
        self.assertTrue(eligible_detail(DETAIL))
        for bad in (DETAIL.replace("www.teatrosocialemantova.it","fake.example"),
                    DETAIL+"#fragment", DETAIL+"&other=1",
                    "http://www.teatrosocialemantova.it/it-it/la-traviata-v3.aspx",
                    INDEX):
            self.assertFalse(eligible_detail(bad))

    def test_index_discovers_only_exact_official_candidate_urls(self):
        html=('<a href="/it-it/la-traviata-v3.aspx">La traviata</a>'
              '<a href="/it-it/ricerca.aspx?fti=opera+lirica">Search</a>'
              '<a href="https://fake.example/it-it/evil.aspx">Other</a>')
        expected=["https://www.teatrosocialemantova.it/it-it/la-traviata-v3.aspx"]
        self.assertEqual(extract_index(html),expected)
        self.assertEqual(extract(KEY,INDEX,html,1),expected)

    def test_exact_official_recital_and_canonical_composer(self):
        title,composer,venue,recite=parse_detail(fixture(),url=DETAIL)
        self.assertEqual((title,composer,venue),
                         ("La traviata","Giuseppe Verdi","Teatro Sociale"))
        self.assertEqual(recite,[("2026-12-20","17:30")])
        facts=parse_source_credited_opera_detail(KEY,DETAIL,fixture())
        self.assertEqual(facts[0]["starts_at"],"2026-12-20T17:30:00+01:00")

    def test_future_editions_without_fixed_2026_boundary(self):
        data=fixture(time="domenica 19 dicembre 2027 ore 17:30")
        self.assertEqual(parse_detail(data,url=DETAIL)[3],
                         [("2027-12-19","17:30")])

    def test_refuses_nonopera_unattributed_venue_and_unsupported_date(self):
        cases=(fixture(title="A CHRISTMAS CAROL",genre="musical"),
               fixture(composer="uncredited"),
               fixture(venue="Palazzo Te"),
               fixture(time="domenica 32 dicembre 2026 ore 17:30"),
               fixture(time="domenica 20 dicembre 2026"))
        for html in cases:
            with self.subTest(html=html[:90]):
                with self.assertRaises(ValueError):
                    parse_detail(html,url=DETAIL)

if __name__=="__main__":
    unittest.main()
