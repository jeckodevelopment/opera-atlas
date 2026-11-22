"""Modena municipal Opera 2026/27 connector: strict source and showtime gates."""
import json
import unittest
from opera_atlas.modena_opera_parser import parse_detail,exact_day
from scripts.discover_season_indexes import CONFIG,validate_config,eligible,extract
from scripts.collect_candidate_details import parse_source_credited_opera_detail

KEY="modena-opera-2026-27"
INDEX="https://www.comune.modena.it/vivere-modena/eventi/2026/stagione-opera-2026-2027"
DETAIL=INDEX+"/siberia-di-umberto-giordano"

def fixture(*,venue="Teatro Comunale Pavarotti-Freni",times=None,
            title="Siberia di Umberto Giordano"):
    if times is None:
        times="venerdì 8 gennaio ore 20.00; domenica 10 gennaio ore 15.30"
    return ('<html><header>Comune di Modena</header>'
            f'<h1>{title}</h1><p>Stagione Opera 2026/2027 del Teatro Comunale</p>'
            '<h2>Cos’è</h2><p>Una produzione lirica.</p>'
            f'<h2>Luogo</h2><a>{venue}</a><p>Corso Canal Grande 85 - Modena - 41121</p>'
            '<h2>Date e orari</h2><h3>Orari</h3>'
            f'<p>{times}</p><h2>Costi</h2>'
            '<p>Si veda la biglietteria ufficiale.</p></html>')

class ModenaSourceTests(unittest.TestCase):
    def test_allowlist_exact_official_index_and_production_urls(self):
        sources=validate_config(json.loads(CONFIG.read_text(encoding="utf-8")))
        index=next(x for x in sources if x["key"]==KEY)
        self.assertEqual(index["url"],INDEX)
        self.assertEqual(index["min_links"],9)
        self.assertTrue(eligible(KEY,DETAIL))
        self.assertFalse(eligible(KEY,INDEX))
        # Exact host is enforced by extraction and the detail parser.
        self.assertFalse(eligible(KEY,"https://www.comune.modena.it/vivere-modena/eventi/2026/stagione-musical-2026-2027/foo"))
        self.assertEqual(len(sources),37)

    def test_exact_origin_discovery_without_extra_sites(self):
        html="".join(f'<a href="{INDEX.replace("https://www.comune.modena.it","")}/{x}">Opera</a>'
          for x in ["macbeth-di-giuseppe-verdi","l-olandese-volante-di-richard-wagner",
                    "l-esecuzione","i-salvatori-della-mezzanotte",
                    "siberia-di-umberto-giordano","vanishings","l-anno-che-verra",
                    "la-cenerentola","simon-boccanegra-di-giuseppe-verdi",
                    "le-convenienze-ed-inconvenienze-teatrali","veleno"])
        html+='<a href="https://example.org/vivere-modena/eventi/2026/stagione-opera-2026-2027/evil">offsite</a>'
        self.assertEqual(len(extract(KEY,INDEX,html,9)),11)

    def test_exact_two_siberia_recitals_and_timezone(self):
        title,composer,venue,recite=parse_detail(fixture(),url=DETAIL)
        self.assertEqual((title,composer,venue),("Siberia","Umberto Giordano",
                                                  "Teatro Comunale Pavarotti-Freni"))
        self.assertEqual(recite,[("2027-01-08","20:00"),("2027-01-10","15:30")])
        facts=parse_source_credited_opera_detail(KEY,DETAIL,fixture())
        self.assertEqual(facts[0]["starts_at"],"2027-01-08T20:00:00+01:00")

    def test_verified_weekday_disambiguates_year(self):
        self.assertEqual(exact_day("venerdì","8","gennaio",None),"2027-01-08")
        self.assertEqual(exact_day("domenica","1","novembre","2026"),"2026-11-01")
        with self.assertRaises(ValueError):
            exact_day("martedì","8","gennaio",None)

    def test_mismatched_venue_unknown_author_and_bad_times_fail(self):
        with self.assertRaises(ValueError):
            parse_detail(fixture(venue="Teatro Michelangelo"),url=DETAIL)
        with self.assertRaises(ValueError):
            parse_detail(fixture(title="Siberia"),url=DETAIL)
        with self.assertRaises(ValueError):
            parse_detail(fixture(times="venerdì 8 gennaio ore 20.00; domenica 10 gennaio"),url=DETAIL)
        with self.assertRaises(ValueError):
            parse_detail(fixture(times="venerdì 8 gennaio ore 20.00; venerdì 8 gennaio ore 18.00"),url=DETAIL)
        with self.assertRaises(ValueError):
            parse_detail(fixture(),url=DETAIL.replace("www.comune.modena.it","bad.example"))

if __name__=="__main__":
    unittest.main()
