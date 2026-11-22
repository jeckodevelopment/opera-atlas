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
        self.assertEqual(report["totals"]["facts_resolved"],2)
        self.assertEqual(report["totals"]["translated_facts_resolved"],1)
        self.assertEqual(report["totals"]["unmatched_groups"],3)
        self.assertEqual(report["totals"]["unmatched_facts"],4)
        groups={x["category"]:x for x in report["groups"]}
        self.assertEqual(groups["new_work_candidate"]["recite_observed"],2)
        self.assertEqual(groups["new_work_candidate"]["candidate_ids"],["3","4"])
        self.assertEqual(groups["composer_credit_to_review"]["title"],"La traviata")
        self.assertEqual(groups["missing_composer"]["title"],"Il barbiere di Siviglia")
    def test_contaminated_composer_produces_review_hint_not_auto_match(self):
        evidence={"schema_version":1,"evidence":[
            candidate("a","La traviata","Giuseppe Verdi Opera"),
            candidate("b","La traviata","Giuseppe Verdi (1813–1901)"),
            candidate("c","La traviata","Giuseppe Verdi Coro"),
            candidate("d","Opera sconosciuta","Giuseppe Verdi Opera"),
        ]}
        report=evaluate(evidence,REG)
        rows={e["composer"]+"|"+e["title"]:e for e in report["groups"]}
        for credit in ("Giuseppe Verdi Opera","Giuseppe Verdi (1813–1901)"):
            item=rows[credit+"|La traviata"]
            self.assertEqual(item["possible_canonical_match"]["work_id"],"w3")
            self.assertEqual(item["category"],"composer_credit_to_review")
        self.assertIsNone(rows["Giuseppe Verdi Coro|La traviata"]["possible_canonical_match"])
        self.assertIsNone(rows["Giuseppe Verdi Opera|Opera sconosciuta"]["possible_canonical_match"])
        self.assertEqual(report["totals"]["facts_resolved"],0)

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
