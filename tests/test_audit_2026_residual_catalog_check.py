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

    def test_first_party_ballet_all_six_days_venue_scoped(self):
        days=[f"2026-12-{x:02d}" for x in range(1,7)]
        groups=[dict(g("La bella addormentata",day,clock=None,
                       venue="Teatro Metropolitan.",
                       urls=["https://www.teatromassimobellini.it/calendario/"]),
                     source_key="bellini-catania-opera-2026-27") for day in days]
        x=check(inp(groups),{"productions":[]})
        self.assertEqual(x["counts"],{"official_nonopera_first_party_detail":6})
        self.assertTrue(all(v["official_nonopera_evidence"]["genre"]=="ballet"
                            and not v["automatic_exclusion"] for v in x["observations"]))
        different=dict(groups[0],venue="Teatro Sangiorgi")
        future=dict(groups[0],date="2027-12-01")
        y=check(inp([different,future]),{"productions":[]})
        self.assertEqual(y["counts"],{"requires_official_genre_and_catalog_review":2})

    def test_pierino_five_dates_only_not_all_child_events(self):
        days=["2026-10-10","2026-10-17","2026-11-21","2026-11-28","2026-12-12"]
        groups=[dict(g("Pierino e il lupo",day,clock="11:00",venue=None,
                       urls=["https://www.tcbo.it/stagione-presente/?vista=calendario"]),
                     source_key="bologna-comunale-opera-2027") for day in days]
        x=check(inp(groups),{"productions":[]})
        self.assertEqual(x["counts"],{"official_nonopera_first_party_detail":5})
        self.assertTrue(all(not row["automatic_publication"] for row in x["observations"]))
        wrong_venue=dict(groups[0],venue="Teatro Auditorium Manzoni")
        wrong_source=dict(groups[0],source_key="another-company")
        self.assertEqual(check(inp([wrong_venue,wrong_source]),{"productions":[]})["counts"],
                         {"requires_official_genre_and_catalog_review":2})

    def test_input_security(self):
        q=inp([])
        q["catalog_updated"]=True
        with self.assertRaises(ValueError): check(q,{"productions":[]})

if __name__=="__main__":
    unittest.main()
