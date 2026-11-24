import unittest
from scripts.audit_2026_residual_catalog_check import check

def g(title, day="2026-10-30", clock="21:00",venue="Teatro A",urls=None):
    return {"event_title":title,"date":day,"time":clock,"venue":venue,
            "source_key":"test-opera","source_urls":urls or ["https://official.example/season"],
            "bucket":"unclassified_requires_source_review"}

def inp(groups):
    return {"year":2026,"read_only":True,"catalog_updated":False,
            "complete_seasons_certified":0,
            "event_groups":len(groups),"review_groups":groups}

def prod(title, day="2026-10-30", clock="20:00", venue="Teatro A"):
    return {"title":title,"venue":venue,"dates":[[day,clock]],
            "source_url":"https://official.example/detail"}

class ResidualTests(unittest.TestCase):
    def test_composer_heading_same_date_venue_preserves_clock_discrepancy(self):
        x=check(inp([g("Giuseppe Verdi – Macbeth")]),
                {"productions":[prod("Macbeth")]})
        self.assertEqual(x["counts"],{"catalog_same_work_day_venue_clock_discrepancy":1})
        self.assertFalse(x["observations"][0]["automatic_publication"])

    def test_different_venue_is_not_a_match(self):
        x=check(inp([g("Giuseppe Verdi – Macbeth",venue="Teatro B")]),
                {"productions":[prod("Macbeth")]})
        self.assertEqual(x["counts"],{"requires_official_genre_and_catalog_review":1})

    def test_work_same_clock_matches_without_duplicate_publication(self):
        x=check(inp([g("Siberia",clock="20:00")]),
                {"productions":[prod("Siberia")]})
        self.assertEqual(x["counts"],{"catalog_same_work_day_venue_exact_clock":1})
        self.assertFalse(x["observations"][0]["automatic_publication"])

    def test_official_nonopera_exact_url_day(self):
        x=check(inp([g("Opera Guccini",day="2026-10-29",
                       urls=["https://www.tcbo.it/evento/speciale/opera-guccini-2026/"])]),
                {"productions":[]})
        self.assertEqual(x["counts"],{"official_nonopera_source_scoped":1})
        self.assertFalse(x["observations"][0]["automatic_exclusion"])

    def test_official_nonopera_does_not_apply_to_future(self):
        x=check(inp([g("Opera Guccini",day="2027-10-29",
                       urls=["https://www.tcbo.it/evento/speciale/opera-guccini-2026/"])]),
                {"productions":[]})
        self.assertEqual(x["counts"],{"requires_official_genre_and_catalog_review":1})

    def test_input_security(self):
        q=inp([])
        q["catalog_updated"]=True
        with self.assertRaises(ValueError): check(q,{"productions":[]})

if __name__=="__main__":
    unittest.main()
