"""Spoleto first-party opera: unique venue panel, dates and annual rollover."""
import json
import unittest
from datetime import date
from opera_atlas.spoleto_tls_parser import parse_program
from scripts.discover_season_indexes import CONFIG,validate_config,eligible,extract
from scripts.rollover_season_indexes import next_index
from scripts.collect_candidate_details import parse_known_opera_detail
from scripts.publish_catalog_v2 import REGISTRY

SOURCE="spoleto-tls-lirica-2026"
URL="https://www.tls-belli.it/stagione-lirica-2026/"
PAGE="""<h2>DIDO AND AENEAS</h2><p>musica Henry Purcell</p>
<p>SPOLETO Teatro Caio Melisso</p><p>venerdi 7 agosto, ore 20.30</p>
<h2>L'ELISIR D'AMORE</h2>
<p>musica Gaetano Donizetti</p>
<p>regia Laura Cosso</p>
<p>📍 SPOLETO Teatro Nuovo</p>
<p>mercoledì 16 e giovedì 17 settembre, ore 9.30 (recite scuole)</p>
<p>venerdì 18 settembre, ore 20.30</p>
<p>sabato 19 settembre, ore 18.00</p>
<p>domenica 20 settembre, ore 17.00</p>
<p>L’elisir d’amore è un melodramma giocoso in due atti</p>
<h2>CAMPAGNA ABBONAMENTI SPOLETO - 4 SPETTACOLI</h2>
<p>Dido and Aeneas | Una promessa infranta | La cantatrice calva | L’elisir d’amore</p>
<h2>STAGIONE REGIONALE</h2>
<p>L’ELISIR D’AMORE ASSISI Teatro Lyrick - lunedì 21 settembre, ore 20.30</p>
<p>PERUGIA Teatro Morlacchi - mercoledì 23 settembre, ore 20.30</p>"""

class SpoletoOperaTests(unittest.TestCase):
    def test_source_extracts_only_three_spoleto_public_recite(self):
        entries=validate_config(json.loads(CONFIG.read_text(encoding="utf-8")))
        source=next(x for x in entries if x["key"]==SOURCE)
        self.assertEqual(source["url"],URL)
        self.assertEqual(extract(SOURCE,URL,PAGE,1),[URL])
        self.assertEqual(parse_program(PAGE,url=URL),[
            ("L’elisir d’amore","Gaetano Donizetti",
             "Teatro Nuovo Gian Carlo Menotti","2026-09-18","20:30"),
            ("L’elisir d’amore","Gaetano Donizetti",
             "Teatro Nuovo Gian Carlo Menotti","2026-09-19","18:00"),
            ("L’elisir d’amore","Gaetano Donizetti",
             "Teatro Nuovo Gian Carlo Menotti","2026-09-20","17:00"),
        ])
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        facts=parse_known_opera_detail(SOURCE,URL,PAGE,registry)
        self.assertEqual(len(facts),3)
        self.assertEqual({x["venue"] for x in facts},
                         {"Teatro Nuovo Gian Carlo Menotti"})

    def test_wrong_author_composer_venue_calendar_fails(self):
        for changed in (
            PAGE.replace("musica Gaetano Donizetti","musica Giacomo Puccini"),
            PAGE.replace("SPOLETO Teatro Nuovo","SPOLETO Teatro Caio Melisso"),
            PAGE.replace("venerdì 18 settembre","giovedì 18 settembre"),
            PAGE.replace("sabato 19 settembre, ore 18.00",""),
        ):
            with self.subTest(changed=changed[:80]):
                with self.assertRaises(ValueError):
                    parse_program(changed,url=URL)
        for bad in (URL.replace("https://","http://"),
                    URL.replace("tls-belli.it","untrusted.invalid"),URL+"?q=1"):
            with self.assertRaises(ValueError):
                parse_program(PAGE,url=bad)

    def test_rollover_requires_verification_of_next_official_year(self):
        cfg=validate_config(json.loads(CONFIG.read_text(encoding="utf-8")))
        source=next(x for x in cfg if x["key"]==SOURCE)
        self.assertIsNone(next_index(source,today=date(2026,9,30)))
        self.assertEqual(next_index(source,today=date(2026,10,1)),
                         "https://www.tls-belli.it/stagione-lirica-2027/")
        self.assertTrue(eligible(SOURCE,"https://www.tls-belli.it/stagione-lirica-2027/"))
        self.assertFalse(eligible(SOURCE,"https://untrusted.invalid/stagione-lirica-2027/"))

if __name__=="__main__":
    unittest.main()
