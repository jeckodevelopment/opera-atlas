"""Future Ravenna Opera rows from the Cherubini first-party events listing."""
import json
import unittest
from opera_atlas.ravenna_future_parser import INDEX,eligible_detail,extract_index,parse_detail
from scripts.discover_season_indexes import CONFIG,eligible,extract,validate_config
from scripts.collect_candidate_details import parse_known_opera_detail,parse_source_credited_opera_detail

ROOT="https://www.orchestracherubini.it"
EVENT=ROOT+"/eventi/nuova-traviata/"
OLD=ROOT+"/eventi/pagliacci-2/"
REGISTRY={"works":{"traviata":{"title":"La traviata","composer":"Giuseppe Verdi"}}}
DATES=("venerdì 5 marzo 2027 alle 20:00","domenica 7 marzo 2027 alle 15:30")

def listing():
    def row(title,genre,venue,link,when="05, 07 marzo 2027"):
        return (f"<tr><td>{when}</td><td><a href='{link}'>{title}</a></td>"
                f"<td>{genre}</td><td>{venue}</td></tr>")
    return ('<nav><a href="/eventi/falso/">Falso</a></nav><h1>Eventi</h1>'
            '<table><thead><tr><th>Data</th><th>Titolo</th>'
            '<th>Genere</th><th>Luogo</th></tr></thead><tbody>'+
            row("La traviata","Opera","Teatro Alighieri, Ravenna","/eventi/nuova-traviata/")+
            row("Pagliacci","Opera","Teatro Alighieri, Ravenna","/eventi/pagliacci-2/")+
            row("Macbeth","Opera","Teatro Comunale di Ferrara","/eventi/macbeth-7/")+
            row("Requiem","Opera","Teatro Alighieri, Ravenna","/eventi/requiem/")+
            row("La Cenerentola","Balletto","Teatro Alighieri, Ravenna","/eventi/la-cenerentola-4/")+
            row("Opera falsa","Opera","Teatro Alighieri, Rimini","https://bad.example/eventi/falso/")+
            '</tbody></table><footer><table><tr><td>Domani</td><td><a href="/eventi/altro/">'
            'Altra opera</a></td><td>Opera</td><td>Teatro Alighieri, Ravenna</td></tr></table></footer>')

def page(title="La traviata",composer="Giuseppe Verdi",dates=DATES,
         venue="Teatro Alighieri, Ravenna",kind="Opera"):
    return (f"<h1>{title}</h1><p>musica di {composer} prima rappresentazione 6 marzo 1853</p>"
            "<p>Orchestra Giovanile Luigi Cherubini</p><h3>Date</h3>"+
            "".join(f"<p>{x}</p>" for x in dates)+
            f"<h3>Dettagli</h3><p>{kind}</p><h3>Luogo</h3><p>{venue}</p>"
            "<footer>domenica 3 novembre 2028 alle 20:30</footer>")

class RavennaRollingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads(CONFIG.read_text())
    def test_row_scoped_location_and_genre_exclude_mixed_orchestra_shows(self):
        expected=[EVENT,OLD]
        self.assertEqual(extract_index(listing(),url=INDEX,min_links=1),expected)
        self.assertEqual(extract("ravenna-cherubini-rolling-opera",INDEX,listing(),1),expected)
        self.assertTrue(eligible("ravenna-cherubini-rolling-opera",EVENT))
        self.assertFalse(eligible("ravenna-alighieri-cherubini-2027",EVENT))
        for bad in (EVENT+"?ref=1",EVENT+"#top",ROOT+"/news/nuova-traviata",
                    "https://bad.example/eventi/nuova-traviata/"):
            self.assertFalse(eligible_detail(bad))
        with self.assertRaises(ValueError):
            extract_index(listing().replace("<h1>Eventi</h1>","<h1>Articoli</h1>"),
                          url=INDEX,min_links=1)

    def test_source_credited_future_opera_and_canonical_work(self):
        rows=parse_detail(page(),url=EVENT)
        self.assertEqual(rows,("La traviata","Giuseppe Verdi","Teatro Dante Alighieri",
                               [("2027-03-05","20:00"),("2027-03-07","15:30")]))
        known=parse_known_opera_detail("ravenna-cherubini-rolling-opera",EVENT,page(),REGISTRY)
        self.assertEqual(len(known),2)
        unknown=parse_source_credited_opera_detail("ravenna-cherubini-rolling-opera",
                                                    EVENT,page())
        self.assertEqual(len(unknown),2)
        self.assertEqual(parse_known_opera_detail("ravenna-cherubini-rolling-opera",
                                                   EVENT,page(),{"works":{}}),[])

    def test_wrong_venue_genre_composer_and_date_fail_closed(self):
        cases=(page(venue="Teatro Municipale Valli, Reggio Emilia"),
               page(kind="Balletto"),
               page(title="Requiem"),
               page(composer="sconosciuto"),
               page(dates=(DATES[0],DATES[0])),
               page(dates=("sabato 5 marzo 2027 alle 20:00",DATES[1])),
               page(dates=("venerdì 5 marzo 2027 ora da definire",DATES[1])),
               page(dates=("venerdì 5 marzo 2026 alle 20:00",DATES[1])),
               page().replace("Orchestra Giovanile Luigi Cherubini","Orchestra fittizia"),
               page().replace("<h3>Date</h3>","<h3>Biografie</h3>"),
               page().replace("<h3>Dettagli</h3>","<h3>Altre opere</h3>"),
               page().replace("venerdì 5 marzo","ANNULLATO venerdì 5 marzo"))
        for item in cases:
            with self.subTest(case=item[-95:]),self.assertRaises(ValueError):
                parse_detail(item,url=EVENT)

    def test_original_2027_allowlist_unchanged(self):
        validate_config(self.config)
        sources={r["key"]:r for r in self.config["sources"]}
        self.assertEqual(sources["ravenna-alighieri-cherubini-2027"]["url"],INDEX)
        self.assertEqual(sources["ravenna-cherubini-rolling-opera"]["url"],INDEX)
        self.assertTrue(eligible("ravenna-alighieri-cherubini-2027",OLD))
        self.assertFalse(eligible("ravenna-alighieri-cherubini-2027",EVENT))

if __name__=="__main__":
    unittest.main()
