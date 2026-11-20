"""Narrative opera history and autonomous completeness guarantees."""
import copy
import json
import unittest
from unittest.mock import patch
from scripts.publish_work_editorial import EDITORIAL,HISTORY,MANIFEST,REGISTRY,build_editorial,validate_history
from scripts.auto_work_research import make_history
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class FakeResponse:
    status=200
    def __init__(self,data):self.data=data
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,size):return self.data
    @property
    def headers(self):return {"Content-Type":"application/json"}

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

    def test_model_history_must_quote_literal_supporting_evidence(self):
        source=("Il libretto di Anna Bolena è di Giovanni Testa. "
                "La prima rappresentazione assoluta avvenne il 5 aprile 1830 "
                "al Teatro Carcano di Milano. "
                "L'opera fu composta nel 1829.")
        identity={"title":"Anna Bolena","composer":"Gaetano Donizetti",
                  "authority_url":"https://www.wikidata.org/wiki/Q42",
                  "wikipedia_url":"https://it.wikipedia.org/wiki/Anna_Bolena"}
        output={"supported":True,"librettist":"Giovanni Testa","premiere_year":1830,
                "premiere_venue":"Teatro Carcano","premiere_city":"Milano",
                "composition_year":1829,
                "libretto_evidence":"Il libretto di Anna Bolena è di Giovanni Testa.",
                "premiere_evidence":"La prima rappresentazione assoluta avvenne il 5 aprile 1830 al Teatro Carcano di Milano.",
                "composition_evidence":"L'opera fu composta nel 1829."}
        def response(payload):
            return FakeResponse(json.dumps({"output":[{"content":[{"type":"output_text",
                "text":json.dumps(payload)}]}]}).encode())
        with patch("scripts.auto_work_research.urlopen",return_value=response(output)):
            history=make_history(identity,source,api_key="test")
        self.assertEqual(history["premiere_year"],1830)
        self.assertEqual(history["composition_year"],1829)
        self.assertTrue(validate_history(history))
        bad=copy.deepcopy(output)
        bad["premiere_evidence"]="The opera premiered at an invented venue in 1830."
        with patch("scripts.auto_work_research.urlopen",return_value=response(bad)):
            self.assertIsNone(make_history(identity,source,api_key="test"))
        bad=copy.deepcopy(output)
        bad["composition_evidence"]=""
        with patch("scripts.auto_work_research.urlopen",return_value=response(bad)):
            self.assertIsNone(make_history(identity,source,api_key="test"))

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
