"""No-cost identity review diagnostics use existing official evidence only."""
import unittest
from scripts.work_identity_review import evaluate

REG={"schema_version":1,"works":{
 "die zauberflöte|mozart":{"id":"w1","title":"Die Zauberflöte","composer":"Wolfgang Amadeus Mozart"},
 "barbiere|rossini":{"id":"w2","title":"Il barbiere di Siviglia","composer":"Gioachino Rossini"},
 "traviata|verdi":{"id":"w3","title":"La traviata","composer":"Giuseppe Verdi"},
}}
def candidate(cid,title,composer,*,date="2027-01-01",status="needs_editorial_review"):
    return {"candidate_id":cid,"source_key":"official-theatre","source_url":"https://teatro.example/opera",
            "status":status,"checked_at":"2026-11-22T01:00:00+00:00",
            "event_facts":[{"event_title":title,"composer":composer,"date":date}]}
class IdentityReviewTests(unittest.TestCase):
    def test_group_unmatched_and_distinguish_known_alias(self):
        evidence={"schema_version":1,"evidence":[
          candidate("1","Il flauto magico","Wolfgang Amadeus Mozart"),
          candidate("2","La traviata","Giuseppe Verdi"),
          candidate("3","L'occasione fa il ladro","Gioachino Rossini"),
          candidate("4","L'occasione fa il ladro","Gioachino Rossini",date="2027-01-03"),
          candidate("5","La traviata","Giuseppe Verdi Opera"),
          candidate("6","Il barbiere di Siviglia",""),
          candidate("7","Altra opera","Giuseppe Verdi",status="out_of_monitored_season"),
        ]}
        report=evaluate(evidence,REG)
        self.assertEqual(report["totals"]["facts_resolved"],3)
        self.assertEqual(report["totals"]["translated_facts_resolved"],1)
        self.assertEqual(report["totals"]["unmatched_groups"],2)
        self.assertEqual(report["totals"]["unmatched_facts"],3)
        groups={x["category"]:x for x in report["groups"]}
        self.assertEqual(groups["new_work_candidate"]["recite_observed"],2)
        self.assertEqual(groups["new_work_candidate"]["candidate_ids"],["3","4"])
        self.assertEqual(groups["missing_composer"]["title"],"Il barbiere di Siviglia")
    def test_contaminated_composer_produces_review_hint_not_auto_match(self):
        evidence={"schema_version":1,"evidence":[
            candidate("a","La traviata","Giuseppe Verdi Opera"),
            candidate("b","La traviata","Giuseppe Verdi (1813–1901)"),
            candidate("c","La traviata","Giuseppe Verdi Coro"),
            candidate("d","Opera sconosciuta","Giuseppe Verdi Opera"),
        ]}
        report=evaluate(evidence,REG)
        self.assertEqual(report["totals"]["facts_resolved"],2)
        rows={e["composer"]+"|"+e["title"]:e for e in report["groups"]}
        self.assertEqual(len(rows),2)
        self.assertIsNone(rows["Giuseppe Verdi Coro|La traviata"]["possible_canonical_match"])
        self.assertIsNone(rows["Giuseppe Verdi Opera|Opera sconosciuta"]["possible_canonical_match"])
        self.assertEqual(report["totals"]["unmatched_facts"],2)
        self.assertTrue(all(e["category"] == "new_work_candidate" for e in rows.values()))

    def test_new_composer_not_misclassified_as_contaminated_credit(self):
        evidence={"schema_version":1,"evidence":[
            candidate("new1","La vedova allegra","Franz Lehár"),
            candidate("new2","L'esecuzione","Salvatore Passantino"),
            candidate("new3","Don Pasquale","Gaetano Donizetti"),
            candidate("same","La traviata","Giuseppe Verdi Orchestra"),
        ]}
        report=evaluate(evidence,REG)
        self.assertEqual(report["totals"]["unmatched_groups"],4)
        self.assertTrue(all(g["category"] == "new_work_candidate"
                            for g in report["groups"]))
        self.assertTrue(all(g["possible_canonical_match"] is None
                            for g in report["groups"]))

    def test_diagnostics_exclude_ballets_and_published_mixed_programs(self):
        evidence={"schema_version":1,"evidence":[
            candidate("ballet","La bella addormentata",""),
            candidate("program","A Giacomo Leopardi","Pietro Mascagni",
                      status="needs_program_review"),
            candidate("new","L'esecuzione","Salvatore Passantino"),
        ]}
        evidence["evidence"][1]["source_key"]="ancona-cavalleria-program-2026"
        evidence["evidence"][1]["source_url"]="https://example.org/program"
        states={"schema_version":1,"candidates":[
            {"id":"ballet","status":"excluded_nonopera"},
            {"id":"program","status":"already_catalogued"},
            {"id":"new","status":"needs_review"}]}
        programs={"programs":[{"source_key":"ancona-cavalleria-program-2026",
                                "source_url":"https://example.org/program"}]}
        result=evaluate(evidence,REG,states,programs)
        self.assertEqual(result["totals"]["unmatched_groups"],1)
        self.assertEqual(result["groups"][0]["title"],"L'esecuzione")

    def test_never_auto_assign_by_title_or_different_composer(self):
        r=evaluate({"schema_version":1,"evidence":[
            candidate("x","Il barbiere di Siviglia","Giovanni Paisiello"),
            candidate("y","Il flauto magico","Gioachino Rossini"),
        ]},REG)
        self.assertEqual(r["totals"]["facts_resolved"],0)
        self.assertEqual(r["totals"]["unmatched_groups"],2)
        self.assertEqual(r["totals"]["unmatched_facts"],2)
    def test_skips_out_of_season_and_deduplicates_identical_sources(self):
        c=candidate("repeat","Nuova opera","Gioachino Rossini")
        c["event_facts"]=c["event_facts"]*3
        report=evaluate({"schema_version":1,"evidence":[c]},REG)
        self.assertEqual(report["groups"][0]["recite_observed"],3)
        self.assertEqual(len(report["groups"][0]["sources"]),1)
        self.assertEqual(report["groups"][0]["candidate_ids"],["repeat"])
    def test_validates_schema_and_blocks_unsafe_links(self):
        with self.assertRaises(ValueError):
            evaluate({"schema_version":5,"evidence":[]},REG)
        with self.assertRaises(ValueError):
            evaluate({"schema_version":1,"evidence":[]},{"schema_version":1,"works":[]})
        c=candidate("unsafe","Nuova opera","Gioachino Rossini")
        c["source_url"]="javascript:alert(1)"
        report=evaluate({"schema_version":1,"evidence":[c]},REG)
        self.assertIsNone(report["groups"][0]["sources"][0]["url"])

if __name__=="__main__":
    unittest.main()
