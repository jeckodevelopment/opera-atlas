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

    def test_related_older_or_future_edition_does_not_override_article_year(self):
        # WordPress may show other edition links after a long artist biography.
        # These are not category metadata of the production being inspected.
        unrelated = ("<p>Unrelated artist biography.</p>" * 125
                     + '<a href="/category/vil/vicenza-in-lirica-2027/">'
                       'Edition 2027</a>')
        source = opera_page(edition="").replace(
            "<html>",
            '<html><a href="/category/vil/vicenza-in-lirica-2026/">'
            'Vicenza in Lirica 2026</a>')
        source = source.replace("</html>", unrelated + "</html>")
        self.assertEqual(parse_detail(source, url=BARBIERE)[3], [
            ("2026-09-10", "20:30"),
            ("2026-09-12", "20:30"),
            ("2026-09-13", "19:00")])

    def test_other_festival_venues_remain_excluded_from_olimpico(self):
        concert = opera_page(title="Le nozze di Figaro – Mozart",
                             venue="Castello di Romeo di Montecchio Maggiore",
                             genre="opera in 4 atti", composer="di W. A. MOZART",
                             when="Venerdì 21 agosto | ore 21.00")
        orfeo = opera_page(title="L'Orfeo – Monteverdi",
                           venue="Villa Pisani Bonetti di Bagnolo di Lonigo",
                           composer="di C. MONTEVERDI",
                           when="Domenica 20 settembre | ore 17.00")
        for html, url in ((concert, "https://www.vicenzainlirica.it/le-nozze-di-figaro-mozart/"),
                          (orfeo, "https://www.vicenzainlirica.it/lorfeo-monteverdi/")):
            with self.subTest(url=url), self.assertRaisesRegex(ValueError, "elsewhere"):
                parse_detail(html, url=url)

    def test_2026_official_ticket_office_corroborates_missing_article_year(self):
        # Official ticket-office records carry years and clock times; they
        # must exactly agree with the first-party production's own details.
        tickets = (
            "<html><h1>Biglietteria</h1>"
            "<p>10/09/2026 Il barbiere di Siviglia – Rossini "
            "(anteprima-prova generale), ore 20,30</p>"
            "<p>12 e 13/09/2026 Il barbiere di Siviglia – Rossini "
            "(prima e seconda recita), ore 20,30/19,00</p>"
            "<p>14/09/2026 Il filosofo di campagna – Galuppi, ore 20,30</p>"
            "<p>20/09/2026 L'Orfeo – Monteverdi, ore 17,00</p></html>")
        barbiere = opera_page(edition="")
        with self.assertRaisesRegex(ValueError, "year"):
            parse_detail(barbiere, url=BARBIERE)
        self.assertEqual(parse_detail(
            barbiere, url=BARBIERE, ticketing_html=tickets)[3], [
                ("2026-09-10", "20:30"),
                ("2026-09-12", "20:30"),
                ("2026-09-13", "19:00")])
        filosofo = opera_page(
            title="Il filosofo di campagna – Galuppi",
            composer="di Baldassare GALUPPI",
            genre="Prima rappresentazione: Venezia, Teatro di San Samuele",
            when="Lunedì 14 settembre | ore 20.30",
            edition="")
        self.assertEqual(parse_detail(
            filosofo,url=FILOSOFO,ticketing_html=tickets)[3],
            [("2026-09-14", "20:30")])

    def test_ticket_office_must_agree_and_offsite_still_excluded(self):
        tickets=("<p>10/09/2026 Il barbiere di Siviglia – Rossini, ore 20,30</p>"
                 "<p>12 e 13/09/2026 Il barbiere di Siviglia – Rossini, "
                 "ore 20,30/19,00</p>")
        with self.assertRaisesRegex(ValueError,"disagree"):
            parse_detail(opera_page(edition="",when="Domenica 13 settembre | ore 20.30"),
                         url=BARBIERE,ticketing_html=tickets)
        with self.assertRaisesRegex(ValueError, "elsewhere"):
            parse_detail(opera_page(edition="",venue="Villa Pisani Bonetti di Bagnolo"),
                         url=BARBIERE,ticketing_html=tickets)

    def test_official_showtimes_resolve_unrelated_category_year_links(self):
        tickets=("<p>10/09/2026 Il barbiere di Siviglia – Rossini "
                 "(anteprima-prova generale), ore 20,30</p>"
                 "<p>12 e 13/09/2026 Il barbiere di Siviglia – Rossini "
                 "(prima e seconda recita), ore 20,30/19,00</p>")
        # A WordPress menu linking to the 2027 festival is not evidence
        # that this 2026 opera has a 2027 performance.
        html=opera_page().replace(
            "<html>",'<html><a href="/category/vil/vicenza-in-lirica-2027/">'
                     'Other edition</a>')
        with self.assertRaisesRegex(ValueError,"year"):
            parse_detail(html,url=BARBIERE)
        self.assertEqual(parse_detail(
            html,url=BARBIERE,ticketing_html=tickets)[3],
            [("2026-09-10","20:30"),("2026-09-12","20:30"),
             ("2026-09-13","19:00")])
        # Unlike a related link, an explicitly contradictory year in the
        # article must not be overruled by the ticket-office archive.
        contradictory=opera_page(edition="Vicenza in Lirica 2027").replace(
            "<html>",'<html><a href="/category/vil/vicenza-in-lirica-2026/">'
                     'Vicenza in Lirica 2026</a>')
        with self.assertRaisesRegex(ValueError,"year"):
            parse_detail(contradictory,url=BARBIERE,ticketing_html=tickets)

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
