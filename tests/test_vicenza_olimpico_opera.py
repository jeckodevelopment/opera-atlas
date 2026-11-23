"""Safety tests for evergreen official Vicenza in Lirica opera intake."""
import json
import unittest

from opera_atlas.vicenza_olimpico_opera import (
    KEY, INDEX, eligible_detail, extract_index, parse_detail,
)
from scripts.discover_season_indexes import CONFIG, validate_config, eligible, extract
from scripts.collect_candidate_details import parse_source_credited_opera_detail

BARBIERE="https://www.vicenzainlirica.it/il-barbiere-di-siviglia-rossini/"
FILOSOFO="https://www.vicenzainlirica.it/il-filosofo-di-campagna-galuppi/"
ORFEO="https://www.vicenzainlirica.it/l-orfeo-monteverdi/"

def opera_page(title="Il barbiere di Siviglia – Rossini",
               edition="Vicenza in Lirica 2026",
               venue="Teatro Olimpico di Vicenza",
               genre="opera buffa in 2 atti",
               composer="musica di G. ROSSINI",
               when="Giovedì 10 settembre | ore 20.30 Sabato 12 settembre | ore 20.30 Domenica 13 settembre | ore 19.00"):
    return f"<html><h1>{title}</h1><p>{edition}</p><section><p>{when}</p><p>{venue}</p><p>{genre}</p><p>{composer}</p></section></html>"

class VicenzaOlimpicoOfficialSource(unittest.TestCase):
    def test_approved_index_exact_and_evergreen(self):
        data=json.loads(CONFIG.read_text(encoding="utf-8"))
        source=next(v for v in validate_config(data) if v["key"]==KEY)
        self.assertEqual(source["url"],INDEX)
        self.assertTrue(eligible(KEY,BARBIERE))
        for value in (
            INDEX,"http://www.vicenzainlirica.it/il-barbiere-di-siviglia-rossini/",
            "https://evil.example/il-barbiere-di-siviglia-rossini/",
            BARBIERE+"?query=other",BARBIERE+"#foo",
            "https://www.vicenzainlirica.it/concerto-gala-2026/",
        ):
            self.assertFalse(eligible_detail(value))

    def test_first_party_homepage_discovers_candidates_not_events(self):
        html=('<a href="/il-barbiere-di-siviglia-rossini/">opera</a>'
              '<a href="/il-filosofo-di-campagna-galuppi/">opera</a>'
              '<a href="/petite-messe-solennelle-rossini/">concerto</a>'
              '<a href="https://evil.example/il-barbiere-di-siviglia/">bad</a>')
        expected=sorted([BARBIERE,FILOSOFO])
        self.assertEqual(extract_index(html),expected)
        self.assertEqual(extract(KEY,INDEX,html,1),expected)

    def test_complete_rossini_recitals_and_composer(self):
        title,composer,venue,rows=parse_detail(opera_page(),url=BARBIERE)
        self.assertEqual((title,composer,venue),
                         ("Il barbiere di Siviglia","Gioachino Rossini","Teatro Olimpico"))
        self.assertEqual(rows,[("2026-09-10","20:30"),("2026-09-12","20:30"),
                               ("2026-09-13","19:00")])
        facts=parse_source_credited_opera_detail(KEY,BARBIERE,opera_page())
        self.assertEqual(len(facts),3)
        self.assertEqual(facts[0]["starts_at"],"2026-09-10T20:30:00+02:00")

    def test_official_wordpress_category_supplies_year_outside_event_header(self):
        # The live site puts the festival year in the WordPress category
        # above the main event heading; a strict category is authoritative.
        html=opera_page(edition="").replace(
            "<html>",'<html><a href="https://www.vicenzainlirica.it/category/vicenza-in-lirica-2026/">Vicenza in Lirica 2026</a>')
        title,composer,venue,rows=parse_detail(html,url=BARBIERE)
        self.assertEqual((title,composer,venue),
                         ("Il barbiere di Siviglia","Gioachino Rossini",
                          "Teatro Olimpico"))
        self.assertEqual(len(rows),3)
        with self.assertRaisesRegex(ValueError,"conflicting"):
            parse_detail(opera_page().replace(
                "<html>",'<html><a href="/category/vicenza-in-lirica-2027/">Vicenza in Lirica 2027</a>'),
                url=BARBIERE)
        with self.assertRaisesRegex(ValueError,"year"):
            parse_detail(opera_page(edition="").replace(
                "<html>",'<html><a href="/category/press2026/">Vicenza in Lirica 2026</a>'),
                url=BARBIERE)

    def test_real_wordpress_nested_festival_category_supplies_year(self):
        # The live WordPress category URL is /category/vil/vicenza-in-lirica-2026/
        # rather than the older flat path supported by the parser.
        html=opera_page(edition="").replace(
            "<html>",
            '<html><a href="https://www.vicenzainlirica.it/category/vil/vicenza-in-lirica-2026/">Vicenza in Lirica 2026</a>')
        self.assertEqual(parse_detail(html,url=BARBIERE)[3][0],
                         ("2026-09-10","20:30"))
        with self.assertRaisesRegex(ValueError,"conflicting"):
            parse_detail(opera_page().replace(
                "<html>",
                '<html><a href="/category/vil/vicenza-in-lirica-2027/">Vicenza in Lirica 2027</a>'),
                url=BARBIERE)
        with self.assertRaisesRegex(ValueError,"year"):
            parse_detail(opera_page(edition="").replace(
                "<html>",
                '<html><a href="/category/vil/press-2026/">Vicenza in Lirica 2026</a>'),
                url=BARBIERE)

    def test_2027_edition_without_hardcoded_calendar_year(self):
        html=opera_page(edition="Vicenza in Lirica 2027",
                        when="Sabato 11 settembre | ore 20.30")
        self.assertEqual(parse_detail(html,url=BARBIERE)[3],[("2027-09-11","20:30")])

    def test_galuppi_credit_and_separate_physical_venue(self):
        html=opera_page(title="Il filosofo di campagna – Galuppi",
                        composer="di Baldassare GALUPPI",
                        genre="Prima rappresentazione: Venezia, Teatro di San Samuele",
                        when="Lunedì 14 settembre | ore 20.30")
        self.assertEqual(parse_detail(html,url=FILOSOFO)[:3],
                         ("Il filosofo di campagna","Baldassare Galuppi","Teatro Olimpico"))

    def test_nonopera_or_other_venue_never_promotes(self):
        samples=(
            opera_page(title="Petite Messe Solennelle – Rossini"),
            opera_page(title="Concerto di gala Rossini"),
            opera_page(venue="Villa Pisani Bonetti a Bagnolo di Lonigo"),
            opera_page(venue="Castello della Villa Montecchio Maggiore"),
            opera_page(genre="concerto sinfonico"),
            opera_page(composer="Direzione artistica del festival"),
            opera_page(edition="Festival 2026"),
            opera_page(when="Domenica 39 settembre | ore 21.00"),
            opera_page(when="Domenica 20 settembre"),
        )
        for html in samples:
            with self.subTest(html=html[:85]),self.assertRaises(ValueError):
                parse_detail(html,url=BARBIERE)

if __name__=="__main__":
    unittest.main()
