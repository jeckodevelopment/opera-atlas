"""Future Filarmonico opera cards: independently verified genres, credits and clocks."""
import json
import unittest

from opera_atlas.verona_rolling_opera import INDEX,eligible_detail,extract_index,parse_detail
from scripts.discover_season_indexes import CONFIG,eligible,extract,validate_config
from scripts.collect_candidate_details import parse_known_opera_detail,parse_source_credited_opera_detail

HOST="https://www.arena.it"
EVENT=HOST+"/teatro-filarmonico-verona/2028/nuova-opera/"
ROWS=("domenica 16 gennaio 2028 ore 15:30",
      "mercoledì 19 gennaio 2028 ore 19:00",
      "venerdì 21 gennaio 2028 ore 20:00",
      "domenica 23 gennaio 2028 ore 15:30")
REGISTRY={"works":{"nuova":{"title":"Nuova opera","composer":"Giuseppe Verdi"}}}

def index_html():
    return (
        '<nav>Opera<h2><a href="/teatro-filarmonico-verona/2028/archivio/">'
        'Archivio</a></h2></nav>'
        'Opera<h2><a href="/teatro-filarmonico-verona/2028/nuova-opera/">'
        'Nuova opera</a></h2>'
        'Concerto<h2><a href="/teatro-filarmonico-verona/2028/requiem/">'
        'Requiem</a></h2>'
        'Balletto<h2><a href="/teatro-filarmonico-verona/2028/lo-schiaccianoci/">'
        'Lo schiaccianoci</a></h2>'
        'Opera<h2><a href="/arena-opera-festival/carmen/">Carmen</a></h2>'
        'Opera<h2><a href="https://evil.example/teatro-filarmonico-verona/2028/fake/">'
        'Opera di un altro teatro</a></h2>'
        '<footer>Opera<h2><a href="/teatro-filarmonico-verona/2028/vecchia/">'
        'Archivio</a></h2></footer>')

def detail(*,title="Nuova opera",composer="Giuseppe Verdi",
           kind="Opera",venue="Teatro Filarmonico",rows=ROWS):
    return (
        f'<h1>{title}</h1><p>Location</p><p>{venue}</p>'
        f'<p>Tipo di spettacolo</p><p>{kind}</p><p>Musica</p><p>{composer}</p>'
        '<p>Durata 2h</p><h2>Prossimi spettacoli</h2>'
        +''.join(f'<h4>{row}</h4><p>Mostra il cast</p>' for row in rows)
        +'<h2>Cast</h2><p>Regia: Maria Rossi</p>'
        +'<footer>domenica 17 gennaio 2027 ore 15:30</footer>')

class VeronaRollingOperaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=json.loads(CONFIG.read_text())

    def test_mixed_future_listing_only_opera_and_first_party(self):
        self.assertEqual(extract_index(index_html(),url=INDEX,min_links=1),[EVENT])
        self.assertEqual(extract("filarmonico-verona-rolling-opera",INDEX,index_html(),1),[EVENT])
        self.assertTrue(eligible("filarmonico-verona-rolling-opera",EVENT))
        self.assertFalse(eligible("filarmonico-verona-opera-2027",EVENT))
        for bad in (EVENT+"?ref=x",EVENT+"#tickets",
                    "https://evil.example/teatro-filarmonico-verona/2028/nuova-opera/",
                    HOST+"/arena-opera-festival/carmen/"):
            self.assertFalse(eligible_detail(bad))
        for page in (INDEX+"?page=2",HOST+"/prossime-stagioni/2027/"):
            with self.assertRaises(ValueError):
                extract_index(index_html(),url=page,min_links=1)
        with self.assertRaises(ValueError):
            extract_index('<nav>Opera<h2><a href="'+EVENT+'">Falso</a></h2></nav>',
                          url=INDEX,min_links=1)

    def test_new_opera_exact_future_showtimes_and_firstparty_composer(self):
        values=parse_detail(detail(),url=EVENT)
        self.assertEqual(values,("Nuova opera","Giuseppe Verdi","Teatro Filarmonico",
                         [("2028-01-16","15:30"),("2028-01-19","19:00"),
                          ("2028-01-21","20:00"),("2028-01-23","15:30")]))
        known=parse_known_opera_detail("filarmonico-verona-rolling-opera",
                                       EVENT,detail(),REGISTRY)
        self.assertEqual(len(known),4)
        self.assertEqual([x["date"] for x in known],
                         ["2028-01-16","2028-01-19","2028-01-21","2028-01-23"])
        unknown=parse_source_credited_opera_detail("filarmonico-verona-rolling-opera",
                                                    EVENT,detail())
        self.assertEqual(len(unknown),4)
        self.assertEqual(parse_known_opera_detail("filarmonico-verona-rolling-opera",
                                                   EVENT,detail(),{"works":{}}),[])

    def test_missing_dates_other_genres_and_wrong_year_fail_closed(self):
        cases=(detail(kind="Balletto"),detail(venue="Arena di Verona"),
               detail(composer=""),
               detail(rows=(ROWS[0],ROWS[0])),
               detail(rows=("lunedì 16 gennaio 2028 ore 15:30",)+ROWS[1:]),
               detail(rows=("domenica 16 gennaio 2027 ore 15:30",)+ROWS[1:]),
               detail(rows=("domenica 16 gennaio 2028 ore da definire",)+ROWS[1:]),
               detail().replace("Prossimi spettacoli","Note di regia"),
               detail().replace("Cast</h2><p>Regia","Interpreti</h2><p>Regia"),
               detail().replace("domenica 16 gennaio 2028 ore 15:30","ANNULLATO domenica 16 gennaio 2028 ore 15:30"))
        for page in cases:
            with self.subTest(page=page[-80:]),self.assertRaises(ValueError):
                parse_detail(page,url=EVENT)

    def test_historical_five_title_source_is_not_widened(self):
        validate_config(self.cfg)
        rows={x["key"]:x for x in self.cfg["sources"]}
        self.assertEqual(rows["filarmonico-verona-opera-2027"]["url"],
             HOST+"/teatro-filarmonico-verona/spettacoli-prossima-stagione/")
        self.assertEqual(rows["filarmonico-verona-rolling-opera"]["url"],INDEX)
        self.assertTrue(eligible("filarmonico-verona-opera-2027",
                                 HOST+"/teatro-filarmonico-verona/2027/alzira/"))
        self.assertFalse(eligible("filarmonico-verona-opera-2027",EVENT))

if __name__=="__main__":
    unittest.main()
