"""Historical 2026 H1 recite: immutable, source-scoped canonical publication."""
import copy
import json
import unittest
from scripts.build_verified_catalog import MANIFEST, approved_historical_h1, build
from scripts.publish_catalog_v2 import REGISTRY, assemble


class HistoricalH1PublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.approved=approved_historical_h1()

    def test_exact_111_dated_showtimes_and_stable_ids(self):
        self.assertEqual(20,len(self.approved))
        records=[p for p in self.manifest["productions"] if p["source_url"] in self.approved]
        self.assertEqual(20,len(records))
        self.assertEqual(111,sum(len(p["dates"]) for p in records))
        self.assertEqual(111,sum(len(a["dates"]) for a in self.approved.values()))
        canonical=assemble(self.manifest,self.registry)
        published=[p for p in canonical["performances"]
                   if p["source_url"] in self.approved]
        self.assertEqual(111,len(published))
        self.assertEqual(111,len({p["id"] for p in published}))
        self.assertTrue(all(p["time_known"] and p["starts_at"]
                            for p in published))

    def test_reject_changed_venue_title_or_time(self):
        for field,replacement in (("title","La traviata"),("venue","Teatro Inventato")):
            manifest=copy.deepcopy(self.manifest)
            p=next(p for p in manifest["productions"] if p["source_url"] in self.approved)
            p[field]=replacement
            with self.assertRaises(ValueError):
                build(manifest)
        manifest=copy.deepcopy(self.manifest)
        p=next(p for p in manifest["productions"] if p["source_url"] in self.approved)
        p["dates"][0][1]="22:30"
        with self.assertRaises(ValueError):
            build(manifest)

    def test_regio_2025_26_is_source_verified_and_youth_previews_excluded(self):
        urls=[x for x in self.approved.values() if x["city"]=="Torino"]
        self.assertEqual(4,len(urls))
        self.assertEqual(25,sum(len(x["dates"]) for x in urls))
        self.assertTrue(all(x["source_venue"]=="Teatro Regio di Torino" for x in urls))
        # No historic opera source may be approved through a wildcard URL.
        self.assertTrue(all(x["source_url"].startswith(
            "https://www.teatroregio.torino.it/opera-e-balletto-2025-2026/")
            for x in urls))

    def test_2026_ring_aliases_canonicalized_without_duplicate_works(self):
        w=self.registry["works"]
        for title in ("Das Rheingold","Die Walküre","Siegfried","Götterdämmerung"):
            found=[x for x in w.values() if x["title"]==title and x["composer"]=="Richard Wagner"]
            self.assertEqual(1,len(found),title)
        official=[x for x in self.approved.values() if "Der Ring des Nibelungen" in x["official_source_title"]]
        self.assertEqual(4,len(official))
        self.assertTrue(all(x["canonical_title"] in
            {"Das Rheingold","Die Walküre","Siegfried","Götterdämmerung"}
            for x in official))

    def test_seven_new_historical_works_have_history_plot_and_copyright_safe_image(self):
        from scripts.publish_work_editorial import HISTORY, EDITORIAL
        from scripts.publish_work_posters import load_archival_art
        history=json.loads(HISTORY.read_text(encoding="utf-8"))["works"]
        summaries=json.loads(EDITORIAL.read_text(encoding="utf-8"))["synopses"]
        slugs={"das-rheingold","die-walkure","siegfried","gotterdammerung",
               "pelleas-et-melisande","enrico-di-borgogna","ottone-in-villa"}
        images=load_archival_art(slugs)
        for slug in slugs:
            self.assertGreaterEqual(len(summaries[slug]),50)
            self.assertTrue(history[slug]["sources"])
            self.assertIn(slug,images)
            self.assertEqual("archival_work_image",images[slug]["kind"])

    def test_nabucodonosor_is_explicit_alias_only(self):
        rows=[x for x in self.approved.values()
              if x["official_source_title"]=="Nabucodonosor"]
        self.assertEqual(1,len(rows))
        self.assertEqual(("Nabucco","Nabucodonosor","Giuseppe Verdi"),
                         (rows[0]["canonical_title"],rows[0]["official_source_title"],
                          rows[0]["composer"]))
        self.assertEqual(9,len(rows[0]["dates"]))

    def test_existing_2027_routes_remain_unchanged(self):
        fenice=[s for s in self.registry["stagings"].values()
                if s["source_url"] in self.approved
                and s["source_url"].startswith("https://www.teatrolafenice.it/")
                and s["slug"]=="carmen"]
        self.assertEqual(1,len(fenice))
        self.assertEqual("carmen-2025-2026",fenice[0]["route_slug"])
        self.assertIn("fenice-carmen-2027",self.registry["stagings"])


if __name__=="__main__":
    unittest.main()
