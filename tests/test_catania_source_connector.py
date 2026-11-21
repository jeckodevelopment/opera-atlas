"""Regression tests for Catania Bellini official opera event ingestion."""
import json
import unittest

from opera_atlas.catania_detail_parser import parse_detail
from scripts.discover_season_indexes import CONFIG, extract, eligible, validate_config
from scripts.collect_candidate_details import parse_source_credited_opera_detail

KEY = "bellini-catania-opera-2026-27"
INDEX = "https://www.teatromassimobellini.it/opere-e-balletto/"
DETAIL = "https://www.teatromassimobellini.it/eventi/carmen-2026/"

DATES = [
    ("Domenica", "14", "20.30", "A"),
    ("Martedì", "16", "17.30", "S1"),
    ("Mercoledì", "17", "20.30", "B"),
    ("Giovedì", "18", "17.30", "S2"),
    ("Venerdì", "19", "17.30", "C"),
    ("Sabato", "20", "17.30", "R"),
    ("Domenica", "21", "17.30", "D"),
]


def page(*, venue="Teatro Massimo Bellini", composer="Georges Bizet",
         title="Carmen", recite=None, category="Opere e Balletto"):
    if recite is None:
        recite = DATES
    dates = "".join(
        f"<p>{weekday} {day} febbraio 2027 ore {time} (Turno {turn})</p>"
        for weekday, day, time, turn in recite)
    return (
        "<html><nav>Stagione Concerti Recital</nav><main>"
        f"<h3>Luogo</h3><div>{venue}</div><h3>Categoria</h3>"
        f"<div>{category}</div><h3>Data</h3><div>Feb 14 - 21 2027</div>"
        "<h3>Ora</h3>20:30"
        f"<h1>{title}</h1><p>Opéra-comique</p>"
        f"<p>Musica di {composer}</p><p>Direttore Gianluca Martinenghi</p>"
        "<h5>Prima rappresentazione</h5>"+dates+
        "<h3>Naviga sul sito</h3><p>Altri spettacoli</p></main></html>"
    )


class CataniaSourceTests(unittest.TestCase):
    def test_exact_index_and_production_origin(self):
        sources = validate_config(json.loads(CONFIG.read_text(encoding="utf-8")))
        src = next(x for x in sources if x["key"] == KEY)
        self.assertEqual(src["url"], INDEX)
        self.assertTrue(eligible(KEY, DETAIL))
        self.assertFalse(eligible(KEY, "https://www.teatromassimobellini.it/news/carmen-2026/"))
        self.assertEqual(len(sources), 18)
        markup = '<a href="/eventi/carmen-2026/">Carmen</a>' + (
            '<a href="https://fake.example/eventi/carmen-2026/">External</a>'
            '<a href="/biglietteria/">Tickets</a>')
        self.assertEqual(extract(KEY, INDEX, markup, 1), [DETAIL])

    def test_carmen_seven_exact_recitals(self):
        title, composer, venue, recite = parse_detail(page(), url=DETAIL)
        self.assertEqual((title, composer, venue),
                         ("Carmen", "Georges Bizet", "Teatro Massimo Bellini"))
        self.assertEqual(len(recite), 7)
        self.assertEqual(recite[0], ("2027-02-14", "20:30"))
        self.assertEqual(recite[-1], ("2027-02-21", "17:30"))
        facts = parse_source_credited_opera_detail(KEY, DETAIL, page())
        self.assertEqual(facts[0]["starts_at"], "2027-02-14T20:30:00+01:00")
        self.assertEqual(len(facts), 7)

    def test_other_venue_cannot_be_misattributed(self):
        with self.assertRaises(ValueError):
            parse_detail(page(venue="Teatro Metropolitan."), url=DETAIL)
        with self.assertRaises(ValueError):
            parse_detail(page(venue="Teatro Sangiorgi"), url=DETAIL)

    def test_ballet_and_unverified_composer_rejected(self):
        with self.assertRaises(ValueError):
            parse_detail(page(category="Balletto"), url=DETAIL)
        with self.assertRaises(ValueError):
            parse_detail(page(composer=""), url=DETAIL)

    def test_missing_conflicting_and_cancelled_recitals_rejected(self):
        with self.assertRaises(ValueError):
            parse_detail(page(recite=DATES + [DATES[0]]), url=DETAIL)
        with self.assertRaises(ValueError):
            parse_detail(page().replace("Prima rappresentazione","Prima rappresentazione ANNULLATA"),url=DETAIL)
        with self.assertRaises(ValueError):
            parse_detail(page(),url=DETAIL.replace("www.teatromassimobellini.it","evil.invalid"))

if __name__ == "__main__":
    unittest.main()
