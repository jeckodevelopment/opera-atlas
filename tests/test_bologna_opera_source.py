"""Official Bologna index and fact extraction regression tests."""
import unittest
from scripts.discover_season_indexes import extract,eligible,validate_config,CONFIG
from scripts.collect_candidate_details import parse_known_opera_detail,parse_source_credited_opera_detail
from opera_atlas.bologna_detail_parser import parse_detail,normalize_event_fact
import json

KEY="bologna-comunale-opera-2027"
CURRENT="bologna-comunale-opera-2026"
BASE="https://www.tcbo.it/"
URL=BASE+"evento/opera/il-ritorno-di-ulisse-in-patria-2027/"
MANZONI=BASE+"evento/opera/la-straniera-2027/"

def fixture(*,title="Il ritorno di Ulisse in patria",composer="Claudio Monteverdi",
            venue="Teatro Comunale",dates=(("2 Mar 2027","20:00"),("7 Mar 2027","16:00"))):
    cards=" ".join(f"Prima {day} Ore {clock} In vendita dal 27 nov 2026"
                   for day,clock in dates)
    return (f"<h1>{title}</h1><article><h2>L'opera</h2>"
            f"<p>Opera in tre atti</p><p>Compositore {composer} (1567-1643)</p>"
            f"<h3>Date e turni</h3>{cards}<h3>Sede</h3>{venue}"
            f"<h3>Altri eventi</h3>Spettacolo 12 Nov 2027 Ore 20:00</article>")

class BolognaSourceTests(unittest.TestCase):
    def test_exact_official_opera_links_not_concerts(self):
        config=json.loads(CONFIG.read_text(encoding="utf-8"))
        source=next(x for x in validate_config(config) if x["key"]==KEY)
        url=source["url"]
        html=('<a href="/evento/opera/la-straniera-2027/">Opera</a>'
              '<a href="/evento/opera/il-ritorno-di-ulisse-in-patria-2027/">Opera</a>'
              '<a href="/evento/concerto/musica-2027/">Concerto</a>'
              '<a href="https://other.example/evento/opera/fake-2027/">External</a>')
        self.assertEqual(len(extract(KEY,url,html,2)),2)
        self.assertFalse(eligible(KEY,BASE+"evento/concerto/musica-2027/"))
        self.assertFalse(eligible(KEY,BASE+"evento/opera/musica-2027/?preview=1"))
    def test_both_2026_and_2027_official_indexes_are_kept(self):
        config=json.loads(CONFIG.read_text(encoding="utf-8"))
        sources={x["key"]:x for x in validate_config(config)}
        self.assertEqual(sources[CURRENT]["url"],BASE+"stagione-presente/?_tipo=opera")
        self.assertEqual(sources[KEY]["url"],BASE+"stagione-futura/?_tipo=opera")
        url=BASE+"evento/opera/samson-et-dalila-2026/"
        self.assertEqual(extract(CURRENT,sources[CURRENT]["url"],
                                 f'<a href="{url}">Opera 2026</a>',1),[url])
        self.assertFalse(eligible(CURRENT,BASE+"evento/concerto/test-2026/"))
        html=fixture(title="Samson et Dalila",composer="Camille Saint-Saëns",
                     dates=(("13 Nov 2026","20:00"),))
        self.assertEqual(parse_detail(html,url=url)[3],[("2026-11-13","20:00")])

    def test_ticket_dates_clock_composer_and_real_venue(self):
        title,composer,venue,rows=parse_detail(fixture(),url=URL)
        self.assertEqual((title,composer,venue),
                         ("Il ritorno di Ulisse in patria","Claudio Monteverdi","Teatro Comunale di Bologna"))
        self.assertEqual(rows,[("2027-03-02","20:00"),("2027-03-07","16:00")])
        _,_,place,other=parse_detail(fixture(title="La straniera",composer="Vincenzo Bellini",
                                           venue="Teatro Auditorium Manzoni",
                                           dates=(("22 Gen 2027","20:00"),)),
                                     url=MANZONI)
        self.assertEqual(place,"Teatro Auditorium Manzoni")
        self.assertEqual(other,[("2027-01-22","20:00")])
    def test_invalid_times_cancellations_and_incomplete_page_fail(self):
        with self.assertRaises(ValueError):
            parse_detail(fixture().replace("Ore 20:00","Ore 29:00").replace("Ore 16:00","Ore 29:00"),url=URL)
        with self.assertRaises(ValueError):
            parse_detail(fixture().replace("In vendita dal","Annullata. In vendita dal",1),url=URL)
        with self.assertRaises(ValueError):
            parse_detail(fixture().replace("Teatro Comunale","Teatro ignoto"),url=URL)
        with self.assertRaises(ValueError):
            parse_detail(fixture(),url=URL+"?preview=1")
    def test_checkpoint_identity_normalization_is_safe_and_idempotent(self):
        examples=[
            ("Vincenzo Bellini (1801-1835)","Teatro Auditorium Manzoni",
             "Vincenzo Bellini","Teatro Auditorium Manzoni"),
            ("Georges Bizet (1838–1875)","Teatro Comunale",
             "Georges Bizet","Teatro Comunale di Bologna"),
            ("Francesco Filidei (1973)","Teatro Comunale",
             "Francesco Filidei","Teatro Comunale di Bologna"),
            ("Giuseppe Verdi","Teatro Comunale di Bologna",
             "Giuseppe Verdi","Teatro Comunale di Bologna"),
        ]
        for composer,venue,canonical,place in examples:
            fact={"event_title":"Opera","composer":composer,"venue":venue,
                  "date":"2027-05-07","starts_at":"2027-05-07T20:00:00+02:00"}
            cleaned=normalize_event_fact(fact)
            self.assertEqual((cleaned["composer"],cleaned["venue"]),(canonical,place))
            self.assertEqual(cleaned["starts_at"],fact["starts_at"])
            self.assertEqual(normalize_event_fact(cleaned),cleaned)
            self.assertEqual(fact["composer"],composer)
        unsafe=normalize_event_fact({"composer":"Vincenzo Bellini (?–1835)",
                                     "venue":"Teatro ignoto"})
        self.assertEqual(unsafe,{"composer":"Vincenzo Bellini (?–1835)",
                                 "venue":"Teatro ignoto"})

    def test_source_credited_events_keep_true_location(self):
        rows=parse_source_credited_opera_detail(KEY,MANZONI,
            fixture(title="La straniera",composer="Vincenzo Bellini",
                    venue="Teatro Auditorium Manzoni",dates=(("22 Gen 2027","20:00"),)))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["venue"],"Teatro Auditorium Manzoni")
        self.assertEqual(rows[0]["starts_at"],"2027-01-22T20:00:00+01:00")

if __name__=="__main__":unittest.main()
