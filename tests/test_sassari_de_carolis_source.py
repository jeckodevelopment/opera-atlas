"""De Carolis 2026 season: exact Sassari opera dates, exclude Alghero."""
import unittest
from opera_atlas.sassari_de_carolis_parser import parse_detail
from scripts.discover_season_indexes import extract,eligible

HOST="https://www.marialisadecarolis.it"
INDEX=HOST+"/opere-liriche.aspx"
URL=lambda ident: HOST+"/opera-lirica.aspx?id="+ident
DATA={
    "372":("Il flauto magico","Wolfgang Amadeus Mozart",
           "25 SETTEMBRE 20:30 / 27 SETTEMBRE 16:30"),
    "373":("Don Carlo","Giuseppe Verdi",
           "30 OTTOBRE 20:30 / 1 NOVEMBRE 16:30"),
    "375":("Rigoletto","Giuseppe Verdi",
           "11 DICEMBRE 20:30 / 13 DICEMBRE 16:30"),
}
def page(ident):
    title,composer,dates=DATA[ident]
    return (f"<p>Stagione lirica Home / Stagione / Opere e concerti 2026</p>"
            f"<h2>{title}</h2><a>{composer}</a><h3>{dates}</h3>"
            "<p>Ricordiamo che il parcheggio del Teatro Comunale e aperto.</p>"
            "<h3>Allestimento</h3><p>Ente de Carolis</p>"
            "<h2>Notizie / News</h2>"
            "<p>Alghero Festival Pagliacci 17 LUGLIO 22:00</p>")
class SassariDeCarolisTests(unittest.TestCase):
    def test_only_three_productions_not_alghero_or_concerts(self):
        html=''.join(f'<a href="/opera-lirica.aspx?id={i}">{i}</a>'
                     for i in ("370","371","372","373","374","375","376"))
        self.assertEqual(extract("sassari-de-carolis-opera-2026",INDEX,html,3),
                         [URL(i) for i in ("372","373","375")])
        for bad in (URL("370"),URL("371"),URL("374"),URL("375")+"&utm=1",
                    HOST+"/opera-lirica.aspx?ID=375",
                    "http://www.marialisadecarolis.it/opera-lirica.aspx?id=375",
                    "https://fake.example/opera-lirica.aspx?id=375"):
            self.assertFalse(eligible("sassari-de-carolis-opera-2026",bad))
    def test_six_exact_2026_showtimes(self):
        expected={
            "372":[("2026-09-25","20:30"),("2026-09-27","16:30")],
            "373":[("2026-10-30","20:30"),("2026-11-01","16:30")],
            "375":[("2026-12-11","20:30"),("2026-12-13","16:30")],
        }
        for ident,rows in expected.items():
            with self.subTest(ident=ident):
                self.assertEqual(parse_detail(page(ident),url=URL(ident))[-1],rows)
    def test_canonical_identity_is_shared_with_german_and_french_titles(self):
        import json
        from pathlib import Path
        from scripts.collect_candidate_details import parse_known_opera_detail

        registry=json.loads((Path(__file__).resolve().parents[1]/
                             "data/identity-registry.json").read_text(encoding="utf-8"))
        expected={
            "372":("Die Zauberflöte","Wolfgang Amadeus Mozart","2026-09-25","2026-09-27"),
            "373":("Don Carlos","Giuseppe Verdi","2026-10-30","2026-11-01"),
            "375":("Rigoletto","Giuseppe Verdi","2026-12-11","2026-12-13"),
        }
        for ident,(canonical,composer,first,second) in expected.items():
            with self.subTest(ident=ident):
                evidence=parse_known_opera_detail(
                    "sassari-de-carolis-opera-2026",URL(ident),page(ident),registry)
                self.assertEqual(len(evidence),2)
                self.assertEqual([e["event_title"] for e in evidence],[canonical]*2)
                self.assertEqual([e["composer"] for e in evidence],[composer]*2)
                self.assertEqual([e["date"] for e in evidence],[first,second])
        # No additional Italian-title record; use the original work ID.
        mozart=[w for w in registry["works"].values()
                if w["title"]=="Die Zauberflöte" and w["composer"]=="Wolfgang Amadeus Mozart"]
        self.assertEqual(len(mozart),1)
        self.assertEqual(mozart[0]["id"],"oa-w-000056")
        self.assertFalse(any(w["title"]=="Il flauto magico" for w in registry["works"].values()))

    def test_fails_closed_on_venue_composer_time_and_alghero(self):
        baseline=page("375")
        for invalid in (
            baseline.replace("Giuseppe Verdi","Gioachino Rossini"),
            baseline.replace("13 DICEMBRE 16:30","13 DICEMBRE 19:00"),
            baseline.replace("Teatro Comunale","Teatro Politeama"),
            baseline.replace("Stagione / Opere e concerti 2026",
                             "Stagione / Opere e concerti 2025"),
            baseline.replace("parcheggio del Teatro Comunale",
                             "Alghero Festival Forte della Maddalena e parcheggio del Teatro Comunale"),
        ):
            with self.assertRaises(ValueError):
                parse_detail(invalid,url=URL("375"))
if __name__=="__main__":
    unittest.main()
