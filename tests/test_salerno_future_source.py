"""Regression tests for future Salerno source and mislabelled municipal ballets."""
import json
import unittest
from opera_atlas.salerno_future_parser import INDEX,extract_index,eligible_detail,parse_detail
from scripts.discover_season_indexes import eligible,extract,CONFIG,validate_config
from scripts.collect_candidate_details import parse_known_opera_detail,parse_source_credited_opera_detail

ROOT="https://cultura.comune.salerno.it"
OPERA=ROOT+"/eventi/nuova-traviata-2027/"
BALLET=ROOT+"/eventi/la-vie-en-rose-bolero-2027/"
DATES=(("Venerdì 5 marzo","20.00"),("Domenica 7 marzo","18.00"))
REGISTRY={"works":{"traviata":{"title":"La traviata","composer":"Giuseppe Verdi"}}}

def index_html():
    return (
        '<nav><a href="/eventi/archivio-2027/">Archivio</a></nav>'
        '<h3>Teatro Verdi – Stagione Lirica e di Balletto 2027</h3>'
        '<a href="/eventi/nuova-traviata-2027/">Opera Stagione Lirica Teatro Verdi '
        'La traviata | 2027</a>'
        '<a href="/eventi/la-vie-en-rose-bolero-2027/">Opera Stagione Lirica Teatro Verdi '
        'La vie en rose Bolero | 2027</a>'
        '<a href="/eventi/turandot-2026/">Turandot | 2026</a>'
        '<a href="https://other.example/eventi/opera-2027/">Opera 2027 esterna</a>'
        '<footer><a href="/eventi/ritorno-2027/">Opera 2027</a></footer>')

def detail(*,title="La traviata",description="Opera in tre atti di Giuseppe Verdi Libretto di Francesco Maria Piave",year=2027,rows=DATES,venue="Teatro Municipale Giuseppe Verdi"):
    recite="".join(f"<p>{day}, ore {hour} TURNO</p>" for day,hour in rows)
    return (f'<h1>{title} | {year}</h1>'
            '<p>L\'evento fa parte di Teatro Verdi – Stagione Lirica e di Balletto 2027</p>'
            f'<div>{venue}</div><p>Opera</p>'
            f'<h3>Descrizione breve</h3><p>{description}</p>'
            '<h3>Evento</h3><h3>Organizzatore</h3>'
            f'<p>{venue}</p>'
            f'<h3>Descrizione completa</h3><p>{description}</p>'
            '<p>Prima rappresentazione, 6 marzo 1853</p>'
            '<h3>APPUNTAMENTI</h3>'+recite+
            '<h3>Luoghi collegati</h3><p>Teatro Verdi, Salerno</p>'
            '<footer>PREZZI OPERA BALLETTO</footer>')

class SalernoFutureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads(CONFIG.read_text())

    def test_future_index_discovery_does_not_assume_municipal_opera_tag_excludes_ballets(self):
        self.assertEqual(extract_index(index_html(),url=INDEX,min_links=1),[BALLET,OPERA])
        self.assertEqual(extract("salerno-verdi-rolling-opera",INDEX,index_html(),1),[BALLET,OPERA])
        self.assertTrue(eligible("salerno-verdi-rolling-opera",OPERA))
        self.assertTrue(eligible("salerno-verdi-rolling-opera",BALLET))
        for wrong in (OPERA+"?utm=1",OPERA+"#nav",ROOT+"/eventi/turandot-2026/",
                      "https://evil.example/eventi/nuova-traviata-2027/"):
            self.assertFalse(eligible_detail(wrong))
        with self.assertRaises(ValueError):
            extract_index(index_html().replace("Stagione Lirica e di Balletto 2027",
                                               "Stagione di Prosa 2027"),url=INDEX,min_links=1)

    def test_credited_future_opera_dates_are_canonical_and_year_consistent(self):
        self.assertEqual(parse_detail(detail(),url=OPERA),
                         ("La traviata","Giuseppe Verdi","Teatro Municipale Giuseppe Verdi",
                          [("2027-03-05","20:00"),("2027-03-07","18:00")]))
        known=parse_known_opera_detail("salerno-verdi-rolling-opera",OPERA,
                                      detail(),REGISTRY)
        self.assertEqual(len(known),2)
        self.assertEqual([x["date"] for x in known],["2027-03-05","2027-03-07"])
        credited=parse_source_credited_opera_detail("salerno-verdi-rolling-opera",
                                                     OPERA,detail())
        self.assertEqual(len(credited),2)
        self.assertEqual({x["composer"] for x in credited},{"Giuseppe Verdi"})
        self.assertEqual(parse_known_opera_detail("salerno-verdi-rolling-opera",
                                                   OPERA,detail(),{"works":{}}),[])

    def test_false_opera_tags_ballets_ambiguous_composers_missing_times_rejected(self):
        cases=[
            detail(title="La vie en rose Bolero",
                   description="BALLETTO su musiche di Ravel e Aznavour"),
            detail(description="Coreografie e danza, Opera in biglietteria di Giuseppe Verdi"),
            detail(description="Opera in tre atti. Musica di un artista non identificato"),
            detail(description="Opera in tre atti di Giuseppe Verdi e Giacomo Puccini"),
            detail(rows=(DATES[0],DATES[0])),
            detail(rows=(("Venerdì 5 marzo","da definire"),)),
            detail(rows=(("Sabato 5 marzo","20.00"),)),
            detail(year=2028),
            detail(venue="Altro teatro"),
            detail().replace("APPUNTAMENTI","Storia delle rappresentazioni"),
            detail().replace("Luoghi collegati","Galleria fotografica"),
            detail().replace("Venerdì 5 marzo, ore 20.00","ANNULLATO Venerdì 5 marzo, ore 20.00"),
        ]
        for case in cases:
            with self.subTest(case=case[-100:]),self.assertRaises(ValueError):
                parse_detail(case,url=OPERA)

    def test_historic_2026_title_allowlist_remains_unchanged(self):
        validate_config(self.config)
        sources={x["key"]:x for x in self.config["sources"]}
        self.assertIn("salerno-verdi-rolling-opera",sources)
        self.assertEqual(sources["salerno-verdi-opera-2026"]["url"],INDEX)
        self.assertEqual(sources["salerno-verdi-rolling-opera"]["url"],INDEX)
        self.assertTrue(eligible("salerno-verdi-opera-2026",ROOT+"/eventi/turandot-2026/"))
        self.assertFalse(eligible("salerno-verdi-opera-2026",BALLET))
        self.assertFalse(eligible("salerno-verdi-opera-2026",OPERA))

if __name__=="__main__":
    unittest.main()
