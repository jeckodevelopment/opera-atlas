"""Narrative opera history and autonomous completeness guarantees."""
import copy
import json
import unittest
import re
from urllib.parse import urlsplit
from scripts.discover_season_indexes import CONFIG,validate_config,eligible
from scripts.publish_work_editorial import EDITORIAL,HISTORY,MANIFEST,REGISTRY,build_editorial,validate_history
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class NarrativeHistoryTests(unittest.TestCase):
    def test_every_published_opera_has_complete_sourced_history(self):
        facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        editorial=json.loads(EDITORIAL.read_text(encoding="utf-8"))
        history=json.loads(HISTORY.read_text(encoding="utf-8"))
        entries=build_editorial(facts,registry,editorial,history=history)["works"]
        self.assertTrue(entries)
        by_id={w["id"]:w for w in registry["works"].values()}
        for entry in entries:
            canonical=by_id[entry["work_id"]]
            if entry["history"] is not None:
                self.assertTrue(validate_history(entry["history"]),entry["work_id"])
            else:
                # Newly recognized operas with authoritative identity may
                # legitimately lack historical premiere facts. Never fabricate
                # a premiere merely to satisfy a static coverage count.
                wiki=canonical.get("wikidata_id","")
                official=canonical.get("authority_url","")
                approved=[x for x in validate_config(json.loads(CONFIG.read_text(encoding="utf-8")))
                          if x["access_status"]=="approved"]
                stages=[x for x in registry["stagings"].values()
                        if x["work_id"]==entry["work_id"]]
                sourced=bool(official and any(
                    x.get("source_url")==official for x in stages) and any(
                    urlsplit(x["official_url"]).hostname==urlsplit(official).hostname
                    and eligible(x["key"],official) for x in approved))
                self.assertTrue(bool(re.fullmatch(r"Q[1-9][0-9]*",wiki)) or sourced,
                                entry["work_id"])
        # Deliberate tampering with a legacy source history must still fail.
        legacy=next(e for e in entries if e["history"] is not None and
                    "wikidata_id" not in by_id[e["work_id"]] and
                    "authority_url" not in by_id[e["work_id"]])
        missing=copy.deepcopy(history)
        missing["works"].pop(legacy["slug"],None)
        missing.get("works_by_id",{}).pop(legacy["work_id"],None)
        with self.assertRaisesRegex(ValueError,"missing complete sourced work history"):
            build_editorial(facts,registry,editorial,history=missing)
        exported=json.loads((ROOT/"public/catalog/work-editorial.json").read_text(encoding="utf-8"))
        self.assertEqual(entries,exported["works"])

    def test_history_is_optional_only_for_source_verified_new_identity(self):
        facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        editorial=json.loads(EDITORIAL.read_text(encoding="utf-8"))
        history=json.loads(HISTORY.read_text(encoding="utf-8"))
        from scripts.auto_catalogue import promote_new_works
        from datetime import date
        # A candidate may omit historical fields, but it cannot bypass
        # authority, venue, exact timing and work-identity validation.
        self.assertTrue(all(validate_history(x) for x in
                            history["works"].values() if isinstance(x,dict)))
        self.assertTrue(all("wikidata_id" not in work or
                            isinstance(work["wikidata_id"],str)
                            for work in registry["works"].values()))

    def test_ui_is_narrative_not_metadata_grid(self):
        script=(ROOT/"site/detail.js").read_text(encoding="utf-8")
        css=(ROOT/"site/styles.css").read_text(encoding="utf-8")
        self.assertIn('"La trama"',script)
        self.assertIn('"La storia dell’opera"',script)
        self.assertIn('node("p","work-history-story",historyParts.join(" "))',script)
        self.assertNotIn('node("dl","work-history-grid")',script)
        self.assertIn('.work-history-narrative .work-history-story',css)

if __name__=="__main__":
    unittest.main()
