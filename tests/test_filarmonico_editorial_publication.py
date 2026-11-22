"""The Filarmonico's four pending operas must have source-bound editorial authority."""
import json
import unittest
from pathlib import Path
from scripts.publish_work_editorial import validate_history
from scripts.publish_work_posters import load_archival_art

ROOT=Path(__file__).resolve().parents[1]
SOURCE="filarmonico-verona-opera-2027"
BASE="https://www.arena.it/teatro-filarmonico-verona/2027/"
CASES={
    "alzira":("Alzira","Giuseppe Verdi","alzira"),
    "il-ratto-dal-serraglio":("Il ratto dal serraglio","Wolfgang Amadeus Mozart","il-ratto-dal-serraglio"),
    "il-signor-bruschino":("Il signor Bruschino","Gioachino Rossini","il-signor-bruschino"),
    "cristoforo-colombo":("Cristoforo Colombo","Alberto Franchetti","cristoforo-colombo"),
}

class FilarmonicoPublicationGateTests(unittest.TestCase):
    def test_all_four_have_real_verified_editorial_records_and_archival_art(self):
        seeds=json.loads((ROOT/"data/verified-work-authority-seeds.json").read_text(encoding="utf-8"))
        entries={(x["source_key"],x["source_url"]):x for x in seeds["works"]}
        art=load_archival_art({case[2] for case in CASES.values()})
        for suffix,(title,composer,slug) in CASES.items():
            with self.subTest(title=title):
                row=entries[(SOURCE,BASE+suffix+"/")]
                self.assertEqual((row["title"],row["composer"]),(title,composer))
                self.assertTrue(validate_history(row["history"]))
                self.assertTrue(45<=len(row["synopsis"].strip())<=300)
                self.assertFalse(row["synopsis"].endswith("Consulta le rappresentazioni verificate in programma nei teatri italiani."))
                self.assertIn(slug,art)
                self.assertEqual(art[slug]["kind"],"archival_work_image")

    def test_official_findings_have_exact_credited_four_showtimes_each(self):
        evidence=json.loads((ROOT/"data/candidate-detail-evidence.json").read_text(encoding="utf-8"))
        records={x["source_url"]:x for x in evidence.get("evidence",[]) if x.get("source_key")==SOURCE}
        for suffix,(title,composer,_) in CASES.items():
            with self.subTest(title=title):
                record=records[BASE+suffix+"/"]
                rows=record["event_facts"]
                self.assertEqual(len(rows),4)
                self.assertEqual({(x["event_title"],x["composer"],x["venue"]) for x in rows},
                                 {(title,composer,"Teatro Filarmonico")})
                self.assertEqual(len({x["date"] for x in rows}),4)

if __name__=="__main__":
    unittest.main()
