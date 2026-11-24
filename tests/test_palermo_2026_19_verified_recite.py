"""Strict publication safeguards for 19 2026 Palermo opera showtimes."""
import copy
import json
import unittest

from scripts.build_verified_catalog import MANIFEST, build
from scripts.publish_catalog_v2 import REGISTRY
from scripts.publish_work_posters import load_archival_art
from scripts.publish_work_editorial import HISTORY, EDITORIAL

OFFICIAL = {
 "https://www.teatromassimo.it/event/dido-and-aeneas-2/": ("Dido and Æneas","Henry Purcell",4),
 "https://www.teatromassimo.it/event/semiramide/": ("Semiramide","Gioachino Rossini",7),
 "https://www.teatromassimo.it/event/aida/": ("Aida","Giuseppe Verdi",8),
}


class PalermoVerified2026Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_full_19_exact_general_public_representations(self):
        entries=[p for p in self.manifest["productions"] if p["source_url"] in OFFICIAL]
        self.assertEqual(3,len(entries))
        self.assertEqual(19,sum(len(p["dates"]) for p in entries))
        for p in entries:
            title,composer,count=OFFICIAL[p["source_url"]]
            self.assertEqual((title,composer,"Palermo","Teatro Massimo","Sicilia"),
                             (p["title"],p["composer"],p["municipality"],p["venue"],p["region"]))
            self.assertEqual(count,len(p["dates"]))
            self.assertEqual(count,len({tuple(d) for d in p["dates"]}))
        aida=next(p for p in entries if p["title"]=="Aida")
        self.assertNotIn(["2026-05-26","18:30"],aida["dates"],"School-only showtime must remain excluded")
        self.assertEqual("oa-w-000134",self.registry["works"]["semiramide|gioachino rossini"]["id"])
        self.assertEqual(19,len([
            k for k in self.registry["performances"]
            if k.startswith("historical-2026-palermo-massimo-")
        ]))

    def test_new_bounded_approval_rejects_all_source_mutations(self):
        originals=[p for p in self.manifest["productions"] if p["source_url"] in OFFICIAL]
        for p in originals:
            for field,value in (
                ("title","Unrelated opera"),
                ("venue","Teatro Inventato"),
                ("municipality","Messina"),
                ("dates",p["dates"]+[["2026-05-26","18:30"]]),
            ):
                with self.subTest(title=p["title"],field=field):
                    changed=copy.deepcopy(self.manifest)
                    target=next(x for x in changed["productions"] if x["key"]==p["key"])
                    target[field]=value
                    with self.assertRaises(ValueError):
                        build(changed)

    def test_compiled_feed_art_and_historical_editorial(self):
        items=build(self.manifest)["performances"]
        selected=[p for p in items if p["sources"][0] in OFFICIAL]
        self.assertEqual(19,len(selected))
        self.assertTrue(all(p["time_known"] for p in selected))
        art=load_archival_art({"semiramide"})["semiramide"]
        self.assertEqual("archival_work_image",art["kind"])
        history=json.loads(HISTORY.read_text(encoding="utf-8"))["works"]["semiramide"]
        self.assertEqual(1823,history["premiere_year"])
        syn=json.loads(EDITORIAL.read_text(encoding="utf-8"))["synopses"]["semiramide"]
        self.assertGreater(len(syn),80)


if __name__=="__main__":
    unittest.main()
