"""21 official Catania showtimes (Aida, Lehár, Giordano) are safe to publish."""
import copy
import json
import unittest

from scripts.build_verified_catalog import MANIFEST, build
from scripts.publish_catalog_v2 import REGISTRY

APPROVED={
    "https://www.teatromassimobellini.it/eventi/aida-2026/":
        ("Aida","Giuseppe Verdi",7,"oa-w-000015"),
    "https://www.teatromassimobellini.it/eventi/la-vedova-allegra-2026/":
        ("La vedova allegra","Franz Lehár",7,"oa-w-000094"),
    "https://www.teatromassimobellini.it/eventi/andrea-chenier-2026/":
        ("Andrea Chénier","Umberto Giordano",7,"oa-w-000060"),
}


class CataniaBellini2026Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_three_distinct_stagings_21_showtimes_no_new_work_ids(self):
        rows=[p for p in self.manifest["productions"] if p["source_url"] in APPROVED]
        self.assertEqual(3,len(rows))
        self.assertEqual(21,sum(len(p["dates"]) for p in rows))
        for p in rows:
            title,composer,count,work_id=APPROVED[p["source_url"]]
            self.assertEqual(
                (title,composer,"Catania","Teatro Massimo Bellini","Sicilia"),
                (p["title"],p["composer"],p["municipality"],p["venue"],p["region"]))
            self.assertEqual(count,len(p["dates"]))
            self.assertEqual(count,len({tuple(d) for d in p["dates"]}))
            staging=self.registry["stagings"][p["key"]]
            self.assertEqual(work_id,staging["work_id"])
            self.assertEqual("oa-v-000028",staging["venue_id"])
        rows=build(self.manifest)["performances"]
        out=[x for x in rows if x["sources"][0] in APPROVED]
        self.assertEqual(21,len(out))
        self.assertTrue(all(x["time_known"] for x in out))

    def test_source_approvals_do_not_accept_changed_work_clock_date_or_venue(self):
        originals=[p for p in self.manifest["productions"] if p["source_url"] in APPROVED]
        for p in originals:
            for field,value in (
                ("title","Different opera"),
                ("venue","Teatro Sangiorgi"),
                ("dates",p["dates"]+[["2026-04-30","19:00"]]),
                ("dates",[["2026-01-01","20:00"]]+p["dates"][1:]),
            ):
                with self.subTest(title=p["title"],field=field):
                    manifest=copy.deepcopy(self.manifest)
                    item=next(x for x in manifest["productions"] if x["key"]==p["key"])
                    item[field]=value
                    with self.assertRaises(ValueError):
                        build(manifest)


if __name__=="__main__":
    unittest.main()
