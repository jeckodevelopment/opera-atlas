"""Narrative opera history and autonomous completeness guarantees."""
import copy
import json
import unittest
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
        self.assertTrue(all(validate_history(e["history"]) for e in entries))
        missing=copy.deepcopy(history)
        missing["works"].pop(entries[0]["slug"])
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
