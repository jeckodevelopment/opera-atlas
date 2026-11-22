"""First-party Sabbioneta opera festival tests: date, venue, author, future editions."""
import json
import unittest

from opera_atlas.sabbioneta_antica_opera import (
    KEY, INDEX, eligible_detail, extract_index, parse_detail,
)
from scripts.discover_season_indexes import CONFIG, validate_config, eligible, extract
from scripts.collect_candidate_details import parse_source_credited_opera_detail

BARBIERE="https://sabbionetaoperafestival.it/evento/il-barbiere-di-siviglia-di-g-rossini/"
ORFEO="https://sabbionetaoperafestival.it/evento/lorfeo-di-c-monteverdi/"
EDIPO="https://sabbionetaoperafestival.it/evento/edipo/"

def event(title="“Il barbiere di Siviglia” di G. Rossini",
          edition="Sabbioneta chamber OPERA festival – Residenze 2026",
          when="Sabato 14 novembre ore 20:30",
          venue="Teatro all’Antica",
          text="(riduzione dell’opera con pianoforte)"):
    return (f"<html><h2>{edition}</h2><h1>{title}</h1>"
            f"<h2>{when}</h2><p>{venue}</p><h1>{title}</h1>"
            f"<p>{text}</p></html>")

def orfeo():
    return event(title="L’ORFEO di C. MONTEVERDI",
                 when="Sabato 19 settembre | ore 20:30",
                 text="Favola in musica. Libretto di Alessandro Striggio. "
                      "Musica di Claudio MONTEVERDI. Produzione del festival")

class SabbionetaOfficialTests(unittest.TestCase):
    def test_approved_index_and_host_path_allowlist(self):
        data=json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(next(x for x in validate_config(data) if x["key"]==KEY)["url"],INDEX)
        self.assertTrue(eligible(KEY,BARBIERE))
        for bad in (INDEX,EDIPO+"?preview=1",ORFEO+"#hash",
                    "http://sabbionetaoperafestival.it/evento/example/",
                    "https://evil.example/evento/example/",
                    "https://sabbionetaoperafestival.it/formazione/orfeo-monteverdi/",
                    "https://sabbionetaoperafestival.it/category/stampa/"):
            self.assertFalse(eligible_detail(bad))

    def test_index_links_are_only_candidates(self):
        html=('<a href="/evento/il-barbiere-di-siviglia-di-g-rossini/">Opera</a>'
              '<a href="/evento/edipo/">Other venue</a>'
              '<a href="/formazione/orfeo-monteverdi/">Training</a>'
              '<a href="https://evil.example/evento/work/">Untrusted</a>')
        self.assertEqual(extract_index(html),sorted([BARBIERE,EDIPO]))
        self.assertEqual(extract(KEY,INDEX,html,1),sorted([BARBIERE,EDIPO]))

    def test_rossini_title_composer_and_single_real_recital(self):
        title,composer,venue,recite=parse_detail(event(),url=BARBIERE)
        self.assertEqual((title,composer,venue),
                         ("Il barbiere di Siviglia","Gioachino Rossini","Teatro all'Antica"))
        self.assertEqual(recite,[("2026-11-14","20:30")])
        facts=parse_source_credited_opera_detail(KEY,BARBIERE,event())
        self.assertEqual(facts[0]["starts_at"],"2026-11-14T20:30:00+01:00")

    def test_orfeo_2026_and_rolling_2027(self):
        self.assertEqual(parse_detail(orfeo(),url=ORFEO),
                         ("L’Orfeo","Claudio Monteverdi","Teatro all'Antica",
                          [("2026-09-19","20:30")]))
        nextyear=event(edition="Sabbioneta chamber OPERA festival – Residenze 2027",
                       when="Domenica 14 novembre ore 20:30")
        self.assertEqual(parse_detail(nextyear,url=BARBIERE)[3],
                         [("2027-11-14","20:30")])

    def test_churches_concerts_and_missing_credit_are_not_promoted(self):
        cases=(
            event(title="Gran Concerto di Natale",text="G. Rossini"),
            event(title="Schumann e Mahler, tra amore ed infinito"),
            event(title="“Il barbiere di Siviglia” di G. Rossini",
                  venue="Chiesa di Santa Maria Assunta",text="concerto di arie"),
            event(title="Edipo",venue="Chiesa della Beata Vergine Incoronata"),
            event(title="“Il barbiere di Siviglia”",text="riduzione dell'opera"),
            event(when="Sabato 40 novembre ore 20:30"),
            event(when="Sabato 14 novembre"),
            event(edition="Festival 2026"),
        )
        for html in cases:
            with self.subTest(html=html[:100]),self.assertRaises(ValueError):
                parse_detail(html,url=BARBIERE)

if __name__=="__main__":
    unittest.main()
