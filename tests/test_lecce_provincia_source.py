"""Province of Lecce first-party fallback: six exact opera performances."""
import unittest
import json
from scripts.publish_catalog_v2 import REGISTRY
from scripts.collect_candidate_details import parse_known_opera_detail
from opera_atlas.lecce_provincia_parser import URL,parse_program
from scripts.discover_season_indexes import extract,eligible

HTML="""<h1>51^ Stagione lirica della Provincia di Lecce</h1>
<p>Teatro Politeama Greco a Lecce, tre opere in abbonamento.</p>
<p>La Stagione 2026 si aprirà venerdì 13 novembre (ore 20.45), con Turandot di Giacomo Puccini,
di cui quest'anno ricorre il centenario, con replica domenica 15 (ore 18).</p>
<p>Il secondo titolo in cartellone sarà L’elisir d’amore di Gaetano Donizetti,
in scena venerdì 27 (ore 20.45) e domenica 29 novembre (ore 18).</p>
<p>Per la terza serata, Nabucco di Giuseppe Verdi, in programma venerdì 11 (ore 20.45)
e domenica 13 dicembre (ore 18).</p>
<p>Al via, dunque, la campagna abbonamenti.</p>
<p>Le Avventure di Pinocchio al Teatro Apollo il 30 dicembre.</p>
"""

class LecceProvinciaTests(unittest.TestCase):
    def test_exact_url_and_six_showtimes(self):
        self.assertTrue(eligible("lecce-provincia-politeama-2026",URL))
        self.assertFalse(eligible("lecce-provincia-politeama-2026",URL+"?preview=1"))
        rows=parse_program(HTML,url=URL)
        self.assertEqual(len(rows),6)
        self.assertEqual([row[0] for row in rows],["Turandot"]*2+["L'elisir d'amore"]*2+["Nabucco"]*2)
        self.assertEqual(rows[0][-2:],("2026-11-13","20:45"))
        self.assertEqual(rows[-1][-2:],("2026-12-13","18:00"))
        self.assertEqual(extract("lecce-provincia-politeama-2026",URL,HTML,1),[URL])
    def test_canonical_registry_resolves_all_six_recite(self):
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        facts=parse_known_opera_detail("lecce-provincia-politeama-2026",URL,HTML,registry)
        self.assertEqual(len(facts),6)
        self.assertEqual([x["event_title"] for x in facts],
                         ["Turandot"]*2+["L’elisir d’amore"]*2+["Nabucco"]*2)
        self.assertEqual(len({(x["event_title"],x["date"]) for x in facts}),6)

    def test_fail_closed_on_changed_title_date_venue_and_cancellation(self):
        for broken in (
            HTML.replace("Gaetano Donizetti","Gioachino Rossini"),
            HTML.replace("domenica 29 novembre","domenica 30 novembre"),
            HTML.replace("Teatro Politeama Greco","Teatro Apollo"),
            HTML.replace("2026","2025"),
            HTML.replace("Nabucco di Giuseppe Verdi","Nabucco di Giuseppe Verdi annullato"),
        ):
            with self.assertRaises(ValueError):
                parse_program(broken,url=URL)
        with self.assertRaises(ValueError):
            parse_program(HTML,url=URL+"?tracking=1")

if __name__=="__main__":
    unittest.main()
