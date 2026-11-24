"""First Italian staging of Venere e Adone: five official showtimes, one identity."""
import copy
import json
import unittest

from scripts.build_verified_catalog import MANIFEST, build
from scripts.publish_catalog_v2 import REGISTRY, assemble
from scripts.publish_work_editorial import EDITORIAL, HISTORY
from scripts.publish_work_posters import load_archival_art

KEY = "historical-2026-venezia-fenice-venere-e-adone"
SOURCE = "https://www.teatrolafenice.it/event/stagione-25-26-venere-e-adone/"
EXPECTED = [
    ["2026-06-26", "19:00"],
    ["2026-06-27", "17:00"],
    ["2026-06-28", "17:00"],
    ["2026-06-30", "19:00"],
    ["2026-07-01", "19:00"],
]

class VenereAdoneFeniceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.matches=[p for p in cls.manifest["productions"]
                     if p["source_url"]==SOURCE]

    def test_exact_five_general_public_operatic_showtimes_and_identity(self):
        self.assertEqual(1,len(self.matches))
        p=self.matches[0]
        self.assertEqual(KEY,p["key"])
        self.assertEqual(("Venere e Adone","Salvatore Sciarrino","Venezia",
                          "Teatro La Fenice","Veneto"),
                         (p["title"],p["composer"],p["municipality"],p["venue"],p["region"]))
        self.assertEqual(EXPECTED,p["dates"])
        self.assertEqual(len(p["dates"]),len({(d[0],d[1]) for d in p["dates"]}))
        self.assertEqual("oa-w-000133",self.registry["works"]["venere e adone|salvatore sciarrino"]["id"])
        self.assertEqual("oa-s-000309",self.registry["stagings"][KEY]["id"])
        self.assertEqual("oa-v-000008",self.registry["stagings"][KEY]["venue_id"])
        self.assertEqual(5,len([k for k in self.registry["performances"] if k.startswith(KEY+"|")]))

    def test_exact_url_does_not_authorize_extra_date_clock_or_venue(self):
        for field,value in (
            ("venue","Teatro Malibran"),
            ("title","Venus and Adonis"),
            ("composer","Salvatore Other"),
            ("municipality","Rome"),
            ("region","Lazio"),
            ("dates",EXPECTED+[["2026-07-02","19:00"]]),
            ("dates",EXPECTED[:4]),
            ("dates",[["2026-06-26","20:00"]]+EXPECTED[1:]),
        ):
            with self.subTest(field=field,value=value):
                manifest=copy.deepcopy(self.manifest)
                row=next(p for p in manifest["productions"] if p["key"]==KEY)
                row[field]=value
                with self.assertRaises(ValueError):
                    build(manifest)

    def test_full_catalog_and_editorial_material_are_supported(self):
        events=build(self.manifest)["performances"]
        published=[e for e in events if e["title"]=="Venere e Adone"
                   and e["composer"]=="Salvatore Sciarrino"
                   and e["municipality"]=="Venezia"]
        self.assertEqual(5,len(published))
        self.assertEqual({r["local_date"] for r in published},{d for d,_ in EXPECTED})
        self.assertTrue(all(r["sources"]==[SOURCE] and r["time_known"] for r in published))
        history=json.loads(HISTORY.read_text(encoding="utf-8"))["works"]["venere-e-adone"]
        self.assertEqual(2023,history["premiere_year"])
        self.assertEqual("Amburgo",history["premiere_city"])
        self.assertTrue(history["sources"])
        synopsis=json.loads(EDITORIAL.read_text(encoding="utf-8"))["synopses"]["venere-e-adone"]
        self.assertGreater(len(synopsis),100)
        image=load_archival_art({"venere-e-adone"})["venere-e-adone"]
        self.assertEqual("archival_work_image",image["kind"])
        self.assertIn("non immagine dell'opera",image["alt"])


if __name__=="__main__":
    unittest.main()
