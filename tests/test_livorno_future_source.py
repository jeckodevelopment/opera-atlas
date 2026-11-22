"""Rolling Goldoni Lirica category: each detail URL has its own date and time."""
import json
import unittest
from opera_atlas.livorno_future_parser import INDEX,eligible_detail,extract_index,parse_detail
from scripts.discover_season_indexes import CONFIG,eligible,extract,validate_config
from scripts.collect_candidate_details import parse_known_opera_detail,parse_source_credited_opera_detail

HOST="https://www.goldoniteatro.it"
D1=HOST+"/spettacoli/nuova-traviata/"
D2=HOST+"/spettacoli/nuova-traviata-2/"
REGISTRY={"works":{"traviata":{"title":"La traviata","composer":"Giuseppe Verdi"}}}

def listing():
    return ('<nav><h3><a href="/spettacoli/falso/">Nascosto</a></h3></nav>'
      '<h1>Archivio spettacoli "Lirica"</h1>'
      '<p>18/04/2028</p><h3><a href="/spettacoli/nuova-traviata/">La traviata</a></h3>'
      '<p>16/04/2028</p><h3><a href="/spettacoli/nuova-traviata-2/">La traviata</a></h3>'
      '<h3><a href="/spettacoli/lirica-abbonamenti/">Lirica: abbonamenti online</a></h3>'
      '<h3><a href="https://bad.example/spettacoli/falso/">Concerto</a></h3>'
      '<footer><h3><a href="/spettacoli/vecchio/">Vecchio</a></h3></footer>')

def detail(*,title="La traviata",date="18 Aprile 2028",clock="16",
           kind="Lirica",composer="Giuseppe Verdi",venue="Teatro Goldoni"):
    return (f'<div>{venue} - {date}</div><p>Orario/i: {clock}</p>'
      f'<span>{kind}</span><h1>{title}</h1>'
      '<p>Venerdì 16 aprile, ore 20</p><p>Domenica 18 aprile, ore 16</p>'
      f'<p>Melodramma in tre atti. Musica di {composer} Direttore Maria Rossi</p>'
      '<p>Orchestra del Teatro Goldoni Massimo de Bernart</p>'
      '<h2>Mediagallery</h2><p>Prima del 1853, prova del 2025 ore 20</p>'
      '<h3>Scopri le date dello spettacolo</h3>')

class GoldoniFutureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_archive_links_and_official_detail_hosts(self):
        self.assertEqual(extract_index(listing(),url=INDEX,min_links=1),sorted([D1,D2]))
        self.assertEqual(extract("goldoni-livorno-rolling-lirica",INDEX,listing(),1),sorted([D1,D2]))
        self.assertTrue(eligible("goldoni-livorno-rolling-lirica",D1))
        self.assertFalse(eligible("goldoni-livorno-dido-2026-27",D1))
        for bad in (D1+"?ref=1",D1+"#calendar",
                    "http://www.goldoniteatro.it/spettacoli/nuova-traviata/",
                    HOST+"/notizie/la-stagione-lirica/"):
            self.assertFalse(eligible_detail(bad))
        for bad in (listing().replace('Archivio spettacoli "Lirica"','Archivio prosa'),
                    "<h1>Archivio spettacoli Lirica</h1><nav><a href='/spettacoli/falso/'>Traviata</a></nav>"):
            with self.assertRaises(ValueError):
                extract_index(bad,url=INDEX,min_links=1)

    def test_one_official_date_per_url_not_both_dates_in_description(self):
        self.assertEqual(parse_detail(detail(),url=D1),
                         ("La traviata","Giuseppe Verdi","Teatro Goldoni",
                          [("2028-04-18","16:00")]))
        known=parse_known_opera_detail("goldoni-livorno-rolling-lirica",D1,detail(),REGISTRY)
        self.assertEqual(len(known),1)
        self.assertEqual(known[0]["date"],"2028-04-18")
        other=parse_known_opera_detail("goldoni-livorno-rolling-lirica",D2,
                                      detail(date="16 Aprile 2028",clock="20"),REGISTRY)
        self.assertEqual(other[0]["date"],"2028-04-16")
        credited=parse_source_credited_opera_detail("goldoni-livorno-rolling-lirica",D1,detail())
        self.assertEqual(len(credited),1)
        self.assertEqual(credited[0]["composer"],"Giuseppe Verdi")
        self.assertEqual(parse_known_opera_detail("goldoni-livorno-rolling-lirica",
                                                   D1,detail(),{"works":{}}),[])

    def test_long_navigation_does_not_hide_verified_ticket_metadata(self):
        long_nav="<nav>"+"<span>Navigation and archives </span>"*80+"</nav>"
        html=long_nav+detail(date="31 Gennaio 2027",clock="16",
                             title="Otello",composer="Giuseppe Verdi")
        self.assertEqual(parse_detail(html,url=HOST+"/spettacoli/otello-3/"),
                         ("Otello","Giuseppe Verdi","Teatro Goldoni",
                          [("2027-01-31","16:00")]))
        # A date shown only in the description is not a ticket for this URL.
        missing=html.replace("Teatro Goldoni - 31 Gennaio 2027",
                             "Teatro Goldoni - Data da definire")
        with self.assertRaisesRegex(ValueError,"own dated ticket clock"):
            parse_detail(missing,url=HOST+"/spettacoli/otello-3/")
        # A second metadata event before the heading is ambiguous.
        ambiguous=html.replace('<span>Lirica</span><h1>',
             '<span>Lirica</span><div>Teatro Goldoni - 29 Gennaio 2027</div>'
             '<p>Orario/i: 20</p><span>Lirica</span><h1>')
        with self.assertRaisesRegex(ValueError,"own dated ticket clock"):
            parse_detail(ambiguous,url=HOST+"/spettacoli/otello-3/")

    def test_official_composer_stops_at_primary_cast_or_premiere_label(self):
        for delimiter,composer,title in (
            ("Personaggi e interpreti","Giuseppe Verdi","Otello"),
            ("Prima esecuzione mondiale","Henry Purcell","Dido and Aeneas"),
            ("Direttore Fabrizio Maria Carminati","Gaetano Donizetti",
             "L’elisir d’amore"),
        ):
            with self.subTest(title=title):
                html=detail(date="29 Gennaio 2027",clock="20",title=title,
                            composer=composer)
                html=html.replace("Direttore Maria Rossi",delimiter)
                self.assertEqual(parse_detail(html,url=D1)[1],composer)

    def test_non_opera_uncredited_missing_clock_and_historic_page_fail_closed(self):
        cases=[
          detail(kind="Prosa"),detail(title="Concerto di Capodanno"),
          detail(venue="La Goldonetta"),detail(composer=""),
          detail(composer="autore non identificato"),
          detail(clock="da definire"),detail(date="18 Aprile 2026"),
          detail().replace("Mediagallery","Prove di orchestra")
                  .replace("Scopri le date dello spettacolo","Calendario generico"),
          detail().replace("Musica di Giuseppe Verdi","Musiche di vari autori"),
          detail().replace("Melodramma in tre atti.","Annullato spettacolo."),
        ]
        for page in cases:
            with self.subTest(source=page[:80]),self.assertRaises(ValueError):
                parse_detail(page,url=D1)
        with self.assertRaises(ValueError):
            parse_detail(detail(),url="https://evil.example/spettacoli/nuova-traviata/")

    def test_old_three_2026_27_sources_remain_unchanged(self):
        validate_config(self.cfg)
        rows={r["key"]:r for r in self.cfg["sources"]}
        self.assertEqual(rows["goldoni-livorno-rolling-lirica"]["url"],INDEX)
        for key in ("goldoni-livorno-dido-2026-27","goldoni-livorno-elisir-2026-27",
                    "goldoni-livorno-otello-2026-27"):
            self.assertEqual(rows[key]["url"],HOST+"/notizie/la-stagione-lirica/")

if __name__=="__main__":
    unittest.main()
