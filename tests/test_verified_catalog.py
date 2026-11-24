"""The first published catalog must match reviewed official observations."""
import json
import unittest
from pathlib import Path
from scripts.build_verified_catalog import ROOT, build, MANIFEST, OUTPUT

class VerifiedCatalogTests(unittest.TestCase):
    def test_modena_costanza_trionfante_one_semiscenic_opera_no_unverified_dates(self):
        from scripts.build_verified_catalog import build
        from scripts.publish_catalog_v2 import assemble
        from pathlib import Path
        import copy, json
        root=Path(__file__).resolve().parents[1]
        facts=json.loads((root/"data/verified-launch-catalog.json").read_text(encoding="utf-8"))
        registry=json.loads((root/"data/identity-registry.json").read_text(encoding="utf-8"))
        candidates=[p for p in facts["productions"] if p["key"]==
                     "historical-2026-modena-belcanto-la-costanza-trionfante"]
        self.assertEqual(1,len(candidates))
        item=candidates[0]
        self.assertEqual([["2026-09-25","20:30"]],item["dates"])
        self.assertEqual("semiscenica_musica_superstite_parti_mancanti_narrate",
                         item["performance_format"])
        self.assertEqual("oa-w-000136",registry["works"][
                         "la costanza trionfante|antonio vivaldi"]["id"])
        catalog=assemble(facts,registry)
        rows=[x for x in catalog["performances"] if x["id"]=="oa-r-001270"]
        self.assertEqual(1,len(rows))
        self.assertEqual("2026-09-25T20:30:00+02:00",rows[0]["starts_at"])
        stagings=[x for x in catalog["stagings"] if x["id"]=="oa-s-000319"]
        self.assertEqual("Modena Belcanto Festival 2026",stagings[0]["festival"])
        self.assertEqual(item["performance_format"],stagings[0]["performance_format"])
        for k,value in (("composer","Gioachino Rossini"),
                        ("venue","Altro Teatro"),("performance_format","integrale")):
            changed=copy.deepcopy(facts)
            target=next(x for x in changed["productions"] if x["key"]==item["key"])
            target[k]=value
            with self.assertRaises(ValueError):build(changed)
        changed=copy.deepcopy(facts)
        next(x for x in changed["productions"] if x["key"]==item["key"])["dates"].append(
            ["2026-09-26","20:30"])
        with self.assertRaises(ValueError):build(changed)

    def test_published_catalog_is_reproducible(self):
        manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
        generated=build(manifest)
        actual=json.loads(OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(generated,actual)
        self.assertGreaterEqual(len(actual["performances"]),19)
        self.assertGreaterEqual(sum(bool(e["time_known"]) for e in actual["performances"]),17)
        self.assertGreaterEqual(sum(not e["time_known"] for e in actual["performances"]),2)
        self.assertEqual(len(set(e["id"] for e in actual["performances"])),len(actual["performances"]))

    def test_no_artificial_midnight_or_source_without_evidence(self):
        events=json.loads(OUTPUT.read_text(encoding="utf-8"))["performances"]
        for event in events:
            self.assertTrue(event["sources"][0].startswith("https://"))
            self.assertTrue(event["title"] and event["venue"] and event["municipality"])
            if event["time_known"]:
                self.assertEqual(event["starts_at"][11:16], event["time_label"])
            else:
                self.assertIsNone(event["starts_at"])
                self.assertEqual(event["time_label"],"Orario da confermare")

    def test_unauthorized_page_fails_build(self):
        manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
        manifest["productions"][0]["source_url"]="https://other.example/shows"
        with self.assertRaises(ValueError):
            build(manifest)

    def test_duplicate_reviewed_observation_fails_build(self):
        manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
        manifest["productions"][0]["dates"].append(manifest["productions"][0]["dates"][0])
        with self.assertRaises(ValueError):
            build(manifest)

if __name__=="__main__":
    unittest.main()
