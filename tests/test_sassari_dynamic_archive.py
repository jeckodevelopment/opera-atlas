"""Permanent de Carolis archive: mixed cards never bypass opera/venue checks."""
import json
import unittest
from opera_atlas.sassari_future_parser import INDEX,eligible_detail,extract_index,parse_detail
from scripts.discover_season_indexes import CONFIG,eligible,extract,validate_config
from scripts.collect_candidate_details import parse_known_opera_detail,parse_source_credited_opera_detail,selected_candidates
from datetime import date

HOST="https://www.marialisadecarolis.it"
TRAVIATA=HOST+"/opera-lirica.aspx?id=401"
RIGOLETTO=HOST+"/opera-lirica.aspx?id=375"
CONCERTO=HOST+"/opera-lirica.aspx?id=402"
ALGHERO=HOST+"/opera-lirica.aspx?id=403"
REGISTRY={"works":{"traviata":{"title":"La traviata","composer":"Giuseppe Verdi"}}}

def index():
    return ("""<p>Stagione lirica Home / Stagione / Opere e concerti</p>
    <nav><h2><a href="/opera-lirica.aspx?id=999">Falso</a></h2></nav>
    2027 <h2><a href="/opera-lirica.aspx?id=401">La traviata</a></h2>
    2027 <h2><a href="/opera-lirica.aspx?id=402">Sinfonia N.3</a></h2>
    2027 <h2><a href="/opera-lirica.aspx?id=403">Pagliacci</a></h2>
    2026 <h2><a href="/opera-lirica.aspx?id=375">Rigoletto</a></h2>
    2025 <h2><a href="/opera-lirica.aspx?id=300">Madama Butterfly</a></h2>
    <footer>2027 <h2><a href="/opera-lirica.aspx?id=998">Rigoletto</a></h2></footer>""")

def page(title="La traviata",composer="Giuseppe Verdi",
         times="11 DICEMBRE 20:30 / 13 DICEMBRE 16:30",
         year=2027,venue="Teatro Comunale di Sassari",
         description="Opera lirica in tre atti."):
    return (f"<p>Stagione lirica Home / Stagione / Opere e concerti {year}</p>"
            f"<h2>{title}</h2><a>{composer}</a><h3>{times}</h3>"
            f"<p>{description} Venerdì 11 e domenica 13 dicembre, {venue}</p>"
            "<h3>Allestimento</h3><p>Ente de Carolis</p>"
            "<h2>Notizie / News &amp; rassegna stampa</h2>"
            "<p>Alghero Festival 17 luglio 22:00</p>")

class SassariDynamicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_dynamic_archive_is_firstparty_and_filters_historic_and_symphonic(self):
        expected=[RIGOLETTO,TRAVIATA,ALGHERO]
        self.assertEqual(extract_index(index(),url=INDEX,min_links=1),expected)
        self.assertEqual(extract("sassari-de-carolis-rolling-opera",INDEX,index(),1),expected)
        self.assertTrue(eligible("sassari-de-carolis-rolling-opera",TRAVIATA))
        self.assertFalse(eligible("sassari-de-carolis-opera-2026",TRAVIATA))
        for invalid in (TRAVIATA+"&utm=1",TRAVIATA+"#poster",
                        "https://bad.example/opera-lirica.aspx?id=401",
                        HOST+"/opera-lirica.aspx?ID=401",
                        HOST+"/opera-lirica.aspx?id=000401",
                        HOST+"/opera-lirica.aspx?id=1&id=401"):
            self.assertFalse(eligible_detail(invalid))
        with self.assertRaises(ValueError):
            extract_index(index().replace("Stagione lirica Home","Programma prosa Home"),
                          url=INDEX,min_links=1)

    def test_new_year_opera_credits_dates_and_canonical_resolution(self):
        facts=parse_detail(page(),url=TRAVIATA)
        self.assertEqual(facts,("La traviata","Giuseppe Verdi",
                               "Teatro Comunale di Sassari",
                               [("2027-12-11","20:30"),("2027-12-13","16:30")]))
        known=parse_known_opera_detail("sassari-de-carolis-rolling-opera",
                                       TRAVIATA,page(),REGISTRY)
        self.assertEqual(len(known),2)
        self.assertEqual([x["date"] for x in known],
                         ["2027-12-11","2027-12-13"])
        self.assertEqual(parse_known_opera_detail("sassari-de-carolis-rolling-opera",
                                                   TRAVIATA,page(),{"works":{}}),[])
        unknown=parse_source_credited_opera_detail("sassari-de-carolis-rolling-opera",
                                                    TRAVIATA,page())
        self.assertEqual(len(unknown),2)
        # A legitimate first-party numeric query must pass the candidate gate.
        candidates={"schema_version":1,"candidates":[
            {"id":"test-sassari-future","source_key":"sassari-de-carolis-rolling-opera",
             "official_url":TRAVIATA,"status":"needs_review"}]}
        # Current candidate gates may prioritize known identities; either
        # way this event must remain eligible, not blocked by its ID query.
        self.assertEqual([x["official_url"] for x in selected_candidates(
            candidates,today=date(2026,11,22))],[TRAVIATA])

    def test_concerts_unknown_venue_and_unverified_times_rejected(self):
        cases=(page(title="Sinfonia N.3 in Re Minore",composer="Gustav Mahler"),
               page(title="Il concerto di Natale",composer="AA.VV."),
               page(venue="Forte della Maddalena di Alghero"),
               page(description="Concerto sinfonico."),
               page(description="Partitura per orchestra, senza voce."),
               page(composer=""),
               page(composer="autore non identificato"),
               page(times="11 DICEMBRE 20:30 / 13 DICEMBRE"),
               page(times="11 DICEMBRE 20:30 / 11 DICEMBRE 20:30"),
               page(year=2025),
               page(description="Opera annullata."),
               page().replace("Teatro Comunale di Sassari","Teatro Sociale di Como"))
        for case in cases:
            with self.subTest(case=case[:100]),self.assertRaises(ValueError):
                parse_detail(case,url=TRAVIATA)

    def test_two_alghero_festival_operas_use_real_city_and_venue(self):
        from scripts.auto_catalogue import verified_venue
        from scripts.collect_candidate_details import parse_known_opera_detail
        from scripts.build_verified_catalog import official_local_time
        examples=[
            ("370","L'elisir d'amore","Gaetano Donizetti",
             "3 LUGLIO 22:00 / 5 LUGLIO 22:00",
             ["2026-07-03","2026-07-05"]),
            ("371","Pagliacci","Ruggero Leoncavallo",
             "17 LUGLIO 22:00 / 19 LUGLIO 22:00",
             ["2026-07-17","2026-07-19"]),
        ]
        for id,title,composer,times,days in examples:
            with self.subTest(id=id):
                url=HOST+"/opera-lirica.aspx?id="+id
                html=(f"<p>Stagione lirica / Opere e concerti 2026</p>"
                      f"<h2>{title}</h2><a href='/compositore'>{composer}</a>"
                      f"<h3>{times}</h3>"
                      "<p>Alghero Festival, Forte della Maddalena.</p>"
                      "<p>Melodramma in due atti</p>"
                      "<h2>Notizie / News e rassegna stampa</h2>")
                parsed=parse_detail(html,url=url)
                self.assertEqual(parsed,(title,composer,"Forte della Maddalena",
                    [(day,"22:00") for day in days]))
                registry={"works":{title:{"title":title,"composer":composer}}}
                facts=parse_known_opera_detail(
                    "sassari-de-carolis-rolling-opera",url,html,registry)
                self.assertEqual(len(facts),2)
                self.assertEqual([x["date"] for x in facts],days)
                self.assertEqual(verified_venue(
                    "sassari-de-carolis-rolling-opera",facts,{"venues":{}})[:2],
                    ("Alghero","Forte della Maddalena"))
                for bad in (
                    html.replace("Forte della Maddalena","Teatro Comunale"),
                    html.replace(composer,"Wrong Composer"),
                    html.replace("22:00","21:00"),
                    html.replace("2026","2027",1),
                ):
                    with self.subTest(change=bad[-65:]),self.assertRaises(ValueError):
                        parse_detail(bad,url=url)
        # Other Sassari productions still require the municipal theatre;
        # a generic unknown 2027 Alghero event is not automatically accepted.
        with self.assertRaises(ValueError):
            parse_detail(page(venue="Forte della Maddalena di Alghero"),
                         url=ALGHERO)

    def test_hist_2026_allowlist_remains_isolated(self):
        validate_config(self.cfg)
        sources={x["key"]:x for x in self.cfg["sources"]}
        self.assertEqual(sources["sassari-de-carolis-opera-2026"]["url"],INDEX)
        self.assertEqual(sources["sassari-de-carolis-rolling-opera"]["url"],INDEX)
        self.assertTrue(eligible("sassari-de-carolis-opera-2026",RIGOLETTO))
        self.assertFalse(eligible("sassari-de-carolis-opera-2026",CONCERTO))

if __name__=="__main__":
    unittest.main()
