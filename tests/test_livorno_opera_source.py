"""Goldoni Livorno official 2026/27 opera source regressions."""
import json
import unittest
from opera_atlas.livorno_opera_parser import parse_detail,SOURCES
from scripts.discover_season_indexes import CONFIG,extract,eligible,validate_config,classify
from scripts.collect_candidate_details import parse_source_credited_opera_detail

URL="https://www.goldoniteatro.it/notizie/la-stagione-lirica/"
DIDO="goldoni-livorno-dido-2026-27"
OTELLO="goldoni-livorno-otello-2026-27"
ELISIR="goldoni-livorno-elisir-2026-27"

def fixture(*,otello="Venerdì 29 gennaio, ore 20 Domenica 31 gennaio, ore 16"):
    return """
    <html><main><h1>La STAGIONE LIRICA 2026/27</h1>
    <p>Mercoledì 19 agosto, ore 21.30 – Piazza Goldoni</p>
    <p>Giovedì 20 agosto, ore 21.30 – Piazza Goldoni</p>
    <h2>CAVALLERIA RUSTICANA</h2><p>Opera atto unico di Pietro Mascagni</p>
    <p>Venerdì 6 novembre, ore 20</p><p>Domenica 8 novembre, ore 16</p>
    <h2>DIDO AND AENEAS</h2><p>Opera in tre atti – Musica di Henry Purcell</p>
    <p>Direttore Attilio Cremonesi</p>
    <p>"""+otello+"""</p>
    <h2>OTELLO</h2><p>Dramma Lirico – Libretto di Arrigo Boito – Musica di Giuseppe Verdi</p>
    <p>Venerdì 16 aprile, ore 20</p><p>Domenica 18 aprile, ore 16</p>
    <h2>L’ELISIR D’AMORE</h2>
    <p>Melodramma giocoso – Libretto di Felice Romani – Musica di Gaetano Donizetti</p>
    <h3>OPERA OGGI</h3><p>Goldonetta</p>
    <p>Sabato 17 ottobre ore 18:00</p><h3>CALAF</h3>
    </main></html>"""

class LivornoOperaTests(unittest.TestCase):
    def test_three_distinct_bounded_official_sources(self):
        config=validate_config(json.loads(CONFIG.read_text(encoding="utf-8")))
        keys=set(SOURCES)
        self.assertEqual(len(config),35)
        self.assertEqual({x["key"] for x in config if x["key"] in keys},keys)
        for key in keys:
            self.assertTrue(eligible(key,URL))
            self.assertEqual(extract(key,URL,fixture(),1),[URL])
        self.assertFalse(eligible(OTELLO,"https://www.goldoniteatro.it/spettacoli/"))
        self.assertEqual(len({x[0] for x in SOURCES.values()}),3)

    def test_three_known_work_identities_and_clocks(self):
        expected={
            DIDO:[("2026-11-06","20:00"),("2026-11-08","16:00")],
            OTELLO:[("2027-01-29","20:00"),("2027-01-31","16:00")],
            ELISIR:[("2027-04-16","20:00"),("2027-04-18","16:00")],
        }
        for key,days in expected.items():
            with self.subTest(key=key):
                title,composer,venue,recite=parse_detail(fixture(),url=URL,source_key=key)
                self.assertEqual(venue,"Teatro Goldoni")
                self.assertEqual(recite,days)
                self.assertEqual(composer,SOURCES[key][1])
                rows=parse_source_credited_opera_detail(key,URL,fixture())
                self.assertEqual(len(rows),2)
                self.assertEqual(rows[0]["date"],days[0][0])
                self.assertEqual(rows[0]["composer"],composer)

    def test_other_venue_and_partial_dates_are_not_accepted(self):
        for key in SOURCES:
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    parse_detail(fixture(),url=URL.replace("www.goldoniteatro.it","other.invalid"),source_key=key)
        with self.assertRaises(ValueError):
            parse_detail(fixture(otello="Venerdì 29 gennaio, ore 20 Domenica 31 gennaio"),url=URL,source_key=OTELLO)
        with self.assertRaises(ValueError):
            parse_detail(fixture(otello="Venerdì 30 gennaio, ore 20 Domenica 31 gennaio, ore 16"),url=URL,source_key=OTELLO)
        with self.assertRaises(ValueError):
            parse_detail(fixture().replace("Musica di Giuseppe Verdi","Musica di Arrigo Boito"),url=URL,source_key=OTELLO)

    def test_non_goldoni_programme_and_missing_second_recital_fail_closed(self):
        # The same official article also contains Piazza Goldoni and
        # Goldonetta performances; neither is this main theatre's opera.
        for source in SOURCES:
            with self.subTest(source=source):
                with self.assertRaises(ValueError):
                    parse_detail(fixture().replace("La STAGIONE LIRICA 2026/27",
                            "La stagione di prosa 2026/27"),
                            url=URL,source_key=source)

    def test_shared_page_does_not_mark_other_opera_published(self):
        for key in SOURCES:
            self.assertEqual(classify(key,URL,{URL}),"needs_review")

if __name__=="__main__":
    unittest.main()
