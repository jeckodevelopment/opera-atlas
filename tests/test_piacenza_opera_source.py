"""Piacenza 2026/27 source: opera-only index and public recital evidence."""
import json
import unittest

from opera_atlas.piacenza_opera_parser import parse_detail
from scripts.discover_season_indexes import CONFIG,validate_config,eligible,extract
from scripts.collect_candidate_details import parse_source_credited_opera_detail

KEY="piacenza-opera-2026-27"
INDEX="https://teatripiacenza.it/stagioni/stagione-26-27/"
DETAIL="https://teatripiacenza.it/event/siberia/"

def page(*,dates=None,credit="UMBERTO GIORDANO"):
    if dates is None:
        dates=[
            ("Lunedì 14 Dicembre 2026Ore 15:30","Siberia | prova aperta alle scuole・ riservata agli studenti e docenti"),
            ("Mercoledì 16 Dicembre 2026Ore 19:00","Siberia | anteprima #Siberia18・ riservata ai giovani"),
            ("Venerdì 18 Dicembre 2026Ore 20:00","Acquista Biglietto"),
            ("Domenica 20 Dicembre 2026Ore 15:30","Acquista Biglietto")]
    return ('<html><section><h6>INAUGURAZIONE STAGIONE 26.27</h6>'
            f'<h6>{credit}</h6><h1>Siberia</h1><h6>Opera in tre atti</h6>'
            +''.join(f'<a>{date}</a><span>{label}</span>' for date,label in dates)+
            '<h3>INTERPRETI</h3><p>Cast e biglietteria</p>'
            '<h2>Stagione 2026 | 2027</h2><h3>Opera</h3>'
            '<a>La Cenerentola</a></section></html>')

class PiacenzaOperaSourceTests(unittest.TestCase):
    def test_six_explicit_opera_links_from_mixed_season(self):
        sources=validate_config(json.loads(CONFIG.read_text(encoding="utf-8")))
        src=next(s for s in sources if s["key"]==KEY)
        self.assertEqual(src["url"],INDEX)
        self.assertEqual(src["min_links"],6)
        self.assertTrue(eligible(KEY,DETAIL))
        self.assertFalse(eligible(KEY,"https://teatripiacenza.it/stagioni/stagione-26-27/"))
        slugs=["siberia","l-anno-che-verra","la-cenerentola-2",
               "la-clemenza-di-tito","simon-boccanegra","aida"]
        pagehtml="<h2>Opera</h2>"+''.join(
            f'<a href="/event/{s}/">Scopri di più</a>' for s in slugs)
        pagehtml+=('<h2>Concerti</h2><a href="/event/concerto-di-gala/">concert</a>'
                   '<h2>Young</h2><a href="/event/anteprima-scuole/">school</a>'
                   '<a href="https://other.invalid/event/evil/">external</a>')
        result=extract(KEY,INDEX,pagehtml,6)
        self.assertEqual(len(result),6)
        self.assertEqual(result[0],"https://teatripiacenza.it/event/aida/")

    def test_restricted_rehearsals_and_under18_preview_excluded(self):
        title,composer,venue,dates=parse_detail(page(),url=DETAIL)
        self.assertEqual((title,composer,venue),
                         ("Siberia","UMBERTO GIORDANO","Teatro Municipale"))
        self.assertEqual(dates,[("2026-12-18","20:00"),("2026-12-20","15:30")])
        facts=parse_source_credited_opera_detail(KEY,DETAIL,page())
        self.assertEqual(len(facts),2)
        self.assertEqual(facts[0]["starts_at"],"2026-12-18T20:00:00+01:00")

    def test_incomplete_source_and_untrusted_host_fail(self):
        with self.assertRaises(ValueError):
            parse_detail(page(dates=[("Venerdì 18 Dicembre 2026","Acquista Biglietto")]),url=DETAIL)
        with self.assertRaises(ValueError):
            parse_detail(page(credit=""),url=DETAIL)
        with self.assertRaises(ValueError):
            parse_detail(page(),url=DETAIL.replace("teatripiacenza.it","other.invalid"))
        with self.assertRaises(ValueError):
            parse_detail(page(dates=[
                ("Venerdì 18 Dicembre 2026Ore 20:00","Acquista Biglietto"),
                ("Venerdì 18 Dicembre 2026Ore 20:00","Acquista Biglietto")]),url=DETAIL)

if __name__=="__main__":
    unittest.main()
