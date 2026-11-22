"""Novara rolling opera-only evidence is separate from the fixed 2027 allowlist."""
import json
import unittest

from opera_atlas.novara_future_parser import (
    INDEX,eligible_detail,extract_index,parse_detail)
from scripts.discover_season_indexes import CONFIG,eligible,extract,validate_config
from scripts.collect_candidate_details import (
    parse_known_opera_detail,parse_source_credited_opera_detail)

HOST="https://www.fondazioneteatrococcia.it"
NEW=HOST+"/stagione-27-don-pasquale.html"
RIGOLETTO=HOST+"/stagione-27-rigoletto.html"
REGISTRY={"works":{"donpasquale":{"title":"Don Pasquale",
                                 "composer":"Gaetano Donizetti"}}}
DATES=(("Venerdì 29 gennaio 2027","20:30"),
       ("Sabato 30 gennaio 2027","20:00"))

def listing():
    return (
      '<nav><a href="/stagione-27-musical.html">Archivio</a></nav>'
      '<h1>SPETTACOLI OPERA, DANZA, CONCERTI</h1>'
      '<h3><a href="/stagione-27-don-pasquale.html">DON PASQUALE</a></h3>'
      '<h3><a href="/stagione-27-rigoletto.html">RIGOLETTO</a></h3>'
      '<h3><a href="/stagione-27-il-lago-dei-cigni.html">LO SCHIACCIANOCI BALLETTO</a></h3>'
      '<h3><a href="/stagione-27-opera-gala.html">OPERA GALA</a></h3>'
      '<h3><a href="/stagione-27-pop-music.html">SYMPHONIC ITALIAN POP</a></h3>'
      '<h3><a href="https://bad.example/stagione-27-fake.html">ALTRA OPERA</a></h3>'
      '<footer><h3><a href="/stagione-27-balletto.html">Coda</a></h3></footer>'
    )

def page(title="Don Pasquale",composer="Gaetano Donizetti",dates=DATES,
         breadcrumb="Home / Spettacoli / Opera / Don Pasquale"):
    entries="".join(f"<h4>{day}</h4><p>ore {clock}</p>" for day,clock in dates)
    return (f'<div>{breadcrumb}</div><h1>{title}</h1>'
            f'<p>Musica di {composer}</p><p>Libretto di Giovanni Ruffini</p>'
            '<p>Prima rappresentazione 3 gennaio 1843</p>'
            "<h3>informazioni sull'evento</h3>"+entries+
            '<h3>TEATRO COCCIA</h3><a>Compra il biglietto</a>'
            '<footer>Fondazione Teatro Carlo Coccia di Novara</footer>')

class NovaraRollingOperaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads(CONFIG.read_text())

    def test_mixed_official_index_discovers_new_opera_cards_without_gala_and_ballet(self):
        expected=[NEW,RIGOLETTO]
        self.assertEqual(extract_index(listing(),url=INDEX,min_links=1),expected)
        self.assertEqual(extract("coccia-novara-rolling-opera",INDEX,listing(),1),expected)
        self.assertTrue(eligible("coccia-novara-rolling-opera",NEW))
        self.assertFalse(eligible("coccia-novara-opera-2027",NEW))
        for bad in (NEW+"?ref=1",
                    HOST+"/stagione-26-don-pasquale.html",
                    "http://www.fondazioneteatrococcia.it/stagione-27-don-pasquale.html",
                    HOST+"/stagione-27-opera-gala.html",
                    "https://other.example/stagione-27-don-pasquale.html"):
            self.assertFalse(eligible_detail(bad))
        with self.assertRaises(ValueError):
            extract_index(listing().replace("SPETTACOLI OPERA, DANZA, CONCERTI",
                                           "SPETTACOLI PROSA"),url=INDEX,min_links=1)

    def test_2027_new_opera_detail_requires_exact_source_credit_and_rows(self):
        self.assertEqual(parse_detail(page(),url=NEW),
                         ("Don Pasquale","Gaetano Donizetti","Teatro Coccia",
                          [("2027-01-29","20:30"),("2027-01-30","20:00")]))
        facts=parse_known_opera_detail("coccia-novara-rolling-opera",NEW,
                                      page(),REGISTRY)
        self.assertEqual([x["date"] for x in facts],["2027-01-29","2027-01-30"])
        unknown=parse_source_credited_opera_detail("coccia-novara-rolling-opera",
                                                   NEW,page())
        self.assertEqual(len(unknown),2)
        self.assertEqual({x["composer"] for x in unknown},{"Gaetano Donizetti"})
        self.assertEqual(parse_known_opera_detail("coccia-novara-rolling-opera",
                         NEW,page(),{"works":{}}),[])

    def test_first_party_natta_gardens_opera_keeps_its_real_venue(self):
        # The 2027 Il noce di Benevento is at Giardini di Palazzo Natta,
        # not the Teatro Coccia auditorium. Production credits list a
        # transcription after the original composer's first-party credit.
        url=HOST+"/stagione-27-il-noce-di-benevento.html"
        html=(
            "<div>Home / Spettacoli / Opera / Il noce di Benevento</div>"
            "<h1>Il noce di Benevento</h1>"
            "<p>Musica di Giuseppe Balducci</p>"
            "<p>Trascrizione per piccolo ensemble di Massimiliano Piscitello</p>"
            "<p>Cast Allievi Accademia Amo</p>"
            "<h3>informazioni sull'evento</h3>"
            "<h4>Giovedì 17 giugno 2027</h4><p>ore 21:00 opera fuori abbonamento</p>"
            "<h4>Venerdì 18 giugno 2027</h4><p>ore 21:00 opera fuori abbonamento</p>"
            "<h3>GIARDINI DI PALAZZO NATTA</h3>"
        )
        expected=("Il noce di Benevento","Giuseppe Balducci",
                  "Giardini di Palazzo Natta",
                  [("2027-06-17","21:00"),("2027-06-18","21:00")])
        self.assertEqual(parse_detail(html,url=url),expected)
        evidence=parse_source_credited_opera_detail(
            "coccia-novara-rolling-opera",url,html)
        self.assertEqual(len(evidence),2)
        self.assertEqual({x["venue"] for x in evidence},
                         {"Giardini di Palazzo Natta"})
        with self.assertRaises(ValueError):
            parse_detail(html.replace("GIARDINI DI PALAZZO NATTA",
                                      "SEDE NON VERIFICATA"),url=url)

    def test_2027_official_double_bill_never_becomes_one_work(self):
        url=HOST+"/stagione-27-l-amor-mio.html"
        html=page(title="L’amor mio / Il tabarro",
                  composer="Cristian Carrara / Giacomo Puccini",
                  breadcrumb="Home / Spettacoli / Opera / L’amor mio / Il tabarro")
        with self.assertRaisesRegex(ValueError,"multi-work programme"):
            parse_detail(html,url=url)

    def test_multiple_official_composers_with_school_recite_and_public_show(self):
        url=HOST+"/stagione-27-dove-nasce-il-melograno.html"
        html=(
            "<div>Home / Spettacoli / Opera / Dove nasce il melograno</div>"
            "<h1>Dove nasce il melograno</h1>"
            "<p>Musica di Arturo Dal Bianco, Giuseppe Guerrera, "
            "Massimiliano Piscitello (Accademia AMO)</p>"
            "<p>Libretto di Pietro Utili</p>"
            "<h3>informazioni sull'evento</h3>"
            "<h4>Giovedì 29 aprile 2027</h4>"
            "<p>ore 10:00 e 12:00 recite per le scuole</p>"
            "<h4>Venerdì 30 aprile 2027</h4><p>ore 20:00</p>"
            "<h3>TEATRO COCCIA</h3>"
        )
        parsed=parse_detail(html,url=url)
        self.assertEqual(parsed,(
            "Dove nasce il melograno",
            "Arturo Dal Bianco, Giuseppe Guerrera, Massimiliano Piscitello",
            "Teatro Coccia",[("2027-04-30","20:00")]))
        facts=parse_source_credited_opera_detail(
            "coccia-novara-rolling-opera",url,html)
        self.assertEqual(len(facts),1)
        self.assertEqual(facts[0]["date"],"2027-04-30")
        self.assertEqual(facts[0]["composer"],parsed[1])
        with self.assertRaises(ValueError):
            parse_detail(html.replace("ore 20:00</p>",
                                      "ore 20:00 e 21:00</p>"),url=url)
        with self.assertRaises(ValueError):
            parse_detail(html.replace("<h4>Venerdì 30 aprile 2027</h4><p>ore 20:00</p>",""),url=url)

    def test_unverified_genres_dates_and_composers_fail_closed(self):
        cases=[
            page(composer="Giacomo Puccini").replace("Musica di Giacomo Puccini",""),
            page(breadcrumb="Home / Spettacoli / Danza / Don Pasquale"),
            page(title="Don Pasquale - Il Musical",
                 breadcrumb="Home / Spettacoli / Opera / Don Pasquale - Il Musical"),
            page(dates=(DATES[0],DATES[0])),
            page(dates=(("Lunedì 29 gennaio 2027","20:30"),)),
            page(dates=(("Venerdì 29 gennaio 2028","20:30"),)),
            page(dates=(("Venerdì 29 gennaio 2027","non definito"),)),
            page().replace("informazioni sull'evento","note di regia"),
            page().replace("TEATRO COCCIA","PICCOLO COCCIA"),
            page().replace("ore 20:30","Annullato ore 20:30"),
        ]
        for html in cases:
            with self.subTest(case=html[-100:]),self.assertRaises(ValueError):
                parse_detail(html,url=NEW)
        for wrong_url in (NEW+"#date",NEW.replace(HOST,"https://example.org")):
            with self.assertRaises(ValueError):
                parse_detail(page(),url=wrong_url)

    def test_historical_three_operas_remain_unchanged(self):
        validate_config(self.config)
        rows={x["key"]:x for x in self.config["sources"]}
        self.assertEqual(rows["coccia-novara-opera-2027"]["url"],
                         HOST+"/spettacoli.html")
        self.assertEqual(rows["coccia-novara-rolling-opera"]["url"],INDEX)
        self.assertFalse(eligible("coccia-novara-opera-2027",NEW))
        self.assertTrue(eligible("coccia-novara-opera-2027",RIGOLETTO))

if __name__=="__main__":
    unittest.main()
