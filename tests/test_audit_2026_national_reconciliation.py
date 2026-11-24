"""Offline safeguards for national 2026 reconciliation."""
import unittest

from scripts.audit_2026_national_reconciliation import aggregate


def report(offset, facts):
    return {
        "year":2026,"read_only":True,"catalog_updated":False,
        "complete_seasons_certified":0,"archive_offset":offset,
        "checked_at":"2026-11-24T10:00:00+00:00",
        "unverified_2026_facts":facts,
        "seed_pages_attempted":1,"seed_pages_scanned":1,
        "historical_archives_attempted":2,"historical_archives_scanned":1,
        "detail_pages_attempted":3,"detail_pages_scanned":2,
    }


class NationalReconciliationTests(unittest.TestCase):
    def setup_reports(self):
        url="https://official.example/opera/macbeth"
        fact={"source_url":url,"source_key":"example-opera",
              "event_title":"Macbeth","date":"2026-05-04",
              "starts_at":"2026-05-04T20:00:00+02:00",
              "venue":"Teatro Esempio"}
        return [report(0,[fact]),report(240,[fact]),
                report(480,[]),report(720,[])], url

    def test_merges_and_deduplicates_without_publication(self):
        reports, url = self.setup_reports()
        catalog={"productions":[{"source_url":url,"title":"Macbeth",
                 "venue":"Teatro Esempio","municipality":"Torino",
                 "dates":[["2026-05-04","20:00"]]}]}
        full, summary=aggregate(reports,catalog,{"programs":[]},
                                {"records":[]},{"records":[]},{"decisions":[]})
        self.assertEqual(summary["raw_observation_count"],2)
        self.assertEqual(summary["unique_observation_count"],1)
        self.assertEqual(summary["duplicate_observations_collapsed"],1)
        self.assertEqual(summary["observation_counts"],
                         {"already_published_exact_source_day_work":1})
        self.assertEqual(summary["fetch_attempts"]["archives"]["attempts"],8)
        self.assertFalse(summary["catalog_updated"])
        self.assertEqual(full["complete_seasons_certified"],0)

    def test_missing_batch_or_wrong_offsets_fails_closed(self):
        reports,_=self.setup_reports()
        args=({},{"programs":[]},{"records":[]},{"records":[]},{"decisions":[]})
        with self.assertRaises(ValueError):
            aggregate(reports[:3],*args)
        reports[1]["archive_offset"]=0
        with self.assertRaises(ValueError):
            aggregate(reports,*args)

    def test_untrusted_publication_flags_fail_closed(self):
        reports,_=self.setup_reports()
        reports[2]["catalog_updated"]=True
        with self.assertRaises(ValueError):
            aggregate(reports,{},{"programs":[]},{"records":[]},
                      {"records":[]},{"decisions":[]})


if __name__=="__main__":
    unittest.main()
