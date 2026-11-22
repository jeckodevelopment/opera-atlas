"""Reggio Emilia Teatro Valli 2026/27 Opera-only connector regressions."""
import json
import unittest
from opera_atlas.reggio_opera_parser import parse_detail
from scripts.discover_season_indexes import CONFIG,validate_config,eligible,extract
from scripts.collect_candidate_details import parse_source_credited_opera_detail

KEY="reggio-valli-opera-2026-27"
INDEX="https://www.iteatri.re.it/tipo/opera/"
DETAIL="https://www.iteatri.re.it/spettacolo/macbeth-2/"

def page(*,tickets=None,kind="Opera",venue="Teatro Municipale Valli",credit="Giuseppe Verdi"):
    if tickets is None:
        tickets=[
            ("20/11/2026","20:00","da € 35,00"),
            ("22/11/2026","15:30","da € 35,00"),
            ("18/11/2026","15:30","da € 0,00")]
    rows=" ".join(f"{day} | {clock} | {price} | Acquista" for day,clock,price in tickets)
    return ('<html><h1>Macbeth</h1><p>Musica di '+credit+'</p>'
            '<nav>Cast Descrizione Extra Acquista</nav>'
            '<p>Mercoledì 18 Novembre – ore 15:30</p>'
            '<p>Venerdì 20 Novembre – ore 20:00</p>'
            '<p>Domenica 22 Novembre – ore 15:30</p>'
            f'<p>{venue}</p><a>{kind}</a>'
            '<h2>Cast</h2><p>Prova generale riservata agli under 28</p>'
            '<h2>Biglietti</h2><p>'+rows+'</p>'
            '<h2>Riduzioni</h2><h2>Opera -</h2>'
            '<p>20 novembre 2026 Macbeth</p><p>19 marzo 2027 Simon Boccanegra</p>'
            '</html>')

class ReggioSourceTests(unittest.TestCase):
    def test_four_opera_productions_only(self):
        document=json.loads(CONFIG.read_text(encoding="utf-8"))
        sources=validate_config(document)
        item=next(x for x in sources if x["key"]==KEY)
        self.assertEqual(item["url"],INDEX)
        self.assertEqual(len(sources),38)
        self.assertTrue(eligible(KEY,DETAIL))
        self.assertFalse(eligible(KEY,"https://www.iteatri.re.it/2026/09/abbonati-allopera/"))
        slugs=["macbeth-2","death-in-venice","simon-boccanegra-2","la-clemenza-di-tito-2"]
        html='<h1>Opera Stagione -</h1><h2>PREZZI ABBONAMENTI 26-27</h2>'
        html+=''.join(f'<a href="/spettacolo/{slug}/">Scopri di più</a>' for slug in slugs)
        html+='<h2>In evidenza</h2><a href="/spettacolo/concerto/">Concert</a>'
        html+='<a href="https://other.invalid/spettacolo/fake/">Offsite</a>'
        self.assertEqual(len(extract(KEY,INDEX,html,4)),4)

    def test_paid_macbeth_dates_not_reserved_dress_rehearsal(self):
        title,composer,venue,days=parse_detail(page(),url=DETAIL)
        self.assertEqual((title,composer,venue),("Macbeth","Giuseppe Verdi","Teatro Valli"))
        self.assertEqual(days,[("2026-11-20","20:00"),("2026-11-22","15:30")])
        facts=parse_source_credited_opera_detail(KEY,DETAIL,page())
        self.assertEqual(facts[0]["starts_at"],"2026-11-20T20:00:00+01:00")
        self.assertEqual(len(facts),2)

    def test_chamber_opera_at_teatro_ariosto_is_not_excluded(self):
        url="https://www.iteatri.re.it/spettacolo/veleno/"
        html=('<h1>Veleno</h1><p>Opera da camera</p>'
              '<p>Musica di Gaia Aloisi</p>'
              '<p>Libretto e regia di Stefano Simone Pintor</p>'
              '<nav>Cast Descrizione Acquista</nav>'
              '<p>Teatro Ariosto</p><a>Opera</a>'
              '<h2>Biglietti</h2>'
              '<p>28/04/2027 | 20:00 | da € 20,00 | Acquista</p>'
              '<p>30/04/2027 | 20:00 | da € 20,00 | Acquista</p>'
              '<h2>Riduzioni</h2>')
        title,composer,venue,days=parse_detail(html,url=url)
        self.assertEqual((title,composer,venue),
                         ("Veleno","Gaia Aloisi","Teatro Ariosto"))
        self.assertEqual(days,[("2027-04-28","20:00"),
                               ("2027-04-30","20:00")])
        rows=parse_source_credited_opera_detail(KEY,url,html)
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]["composer"],"Gaia Aloisi")
        for corrupt in (html.replace("Musica di Gaia Aloisi","Musica di"),
                        html.replace("Teatro Ariosto","Teatro Cavallerizza")):
            with self.subTest(corrupt=corrupt[:100]),self.assertRaises(ValueError):
                parse_detail(corrupt,url=url)

    def test_partial_ticket_calendar_duplicate_and_invalid_origin_rejected(self):
        for html in [
            page(tickets=[("20/11/2026","20:00","da € 35,00"),
                          ("20/11/2026","20:00","da € 35,00")]),
            page(credit=""),
            page(kind="Musical"),
            page(venue="Teatro Cavallerizza"),
            page(tickets=[]),
        ]:
            with self.subTest(html=html[:60]):
                with self.assertRaises(ValueError):
                    parse_detail(html,url=DETAIL)
        with self.assertRaises(ValueError):
            parse_detail(page(),url=DETAIL.replace("www.iteatri.re.it","other.invalid"))

if __name__=="__main__":
    unittest.main()
