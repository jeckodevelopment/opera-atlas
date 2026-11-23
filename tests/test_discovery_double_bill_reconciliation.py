"""Cross-source discovery must not duplicate an already published double bill."""
import copy
import json
import unittest

from scripts.discovery_queue import reconcile_published_programs, ROOT


class DiscoveryDoubleBillTests(unittest.TestCase):
    def setUp(self):
        self.programs=json.loads(
            (ROOT/"public"/"catalog"/"programs.json").read_text(encoding="utf-8"))
        self.brescia=next(x for x in self.programs["programs"]
                          if x["municipality"]=="Brescia"
                          and x["title"]=="Cavalleria rusticana / Pagliacci")
        self.queue=json.loads(
            (ROOT/"data"/"discovery-candidates.json").read_text(encoding="utf-8"))
        self.candidates=[copy.deepcopy(x) for x in self.queue["candidates"]
                         if x["city"]=="Brescia"]

    def test_complete_brescia_components_resolve_to_one_published_bill(self):
        self.assertEqual(len(self.candidates),2)
        reconcile_published_programs(self.candidates,self.programs)
        self.assertEqual({x["status"] for x in self.candidates},
                         {"already_catalogued"})
        self.assertEqual({x["program_id"] for x in self.candidates},
                         {self.brescia["id"]})

    def test_partial_wrong_date_or_wrong_venue_must_stay_open(self):
        for change in (
            lambda rows: rows.pop(),
            lambda rows: rows[0]["dates"].append({"date":"2026-12-15","time":None}),
            lambda rows: rows[0].update(venue="Different Theatre"),
            lambda rows: rows[0].update(composer="Giuseppe Verdi"),
            lambda rows: rows[1]["dates"][0].update(time="22:30"),
        ):
            rows=copy.deepcopy(self.candidates)
            change(rows)
            reconcile_published_programs(rows,self.programs)
            self.assertFalse(any(x["status"]=="already_catalogued" for x in rows))

    def test_invalid_program_schema_is_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_published_programs(self.candidates,{"schema_version":1})


if __name__=="__main__":
    unittest.main()
