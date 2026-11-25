"""Validate found vs published coverage without counting duplicate works."""
import unittest
from scripts.recite_coverage import detect


class ReciteCoverageTests(unittest.TestCase):
    def test_independent_missing_showtime(self):
        published = {"reviewed_on": "2026-11-21", "productions": [
            {"venue": "Teatro Regio", "municipality": "Torino", "region": "Piemonte",
             "dates": [["2027-01-10", "20:00"], ["2027-01-11", "15:00"]]}
        ]}
        observations = {"evidence": [
            {"status": "needs_editorial_review", "event_facts": [
                {"venue": "Teatro Regio di Torino", "date": "2027-01-10",
                 "starts_at": "2027-01-10T20:00:00+01:00"},
                {"venue": "Teatro Regio di Torino", "date": "2027-01-12",
                 "starts_at": "2027-01-12T20:00:00+01:00"}]}
        ]}
        venue = detect(published, observations)["venues"][0]
        self.assertEqual((venue["published"], venue["found"], venue["missing"]),
                         (2, 3, 1))
        self.assertEqual(venue["percent"], 66.7)

    def test_excluded_candidate_not_counted_despite_stale_evidence(self):
        published = {"reviewed_on": "x", "productions": [
            {"venue": "Teatro Giglio", "municipality": "Lucca", "region": "Toscana",
             "dates": [["2027-01-22", "20:30"]]}]}
        observations = {"evidence": [{"candidate_id": "concert",
            "status": "needs_editorial_review", "event_facts": [
                {"venue": "Teatro Giglio", "date": "2027-03-12",
                 "starts_at": "2027-03-12T21:00:00+01:00"}]}]}
        candidates = {"candidates": [{"id": "concert", "status": "excluded_nonopera"}]}
        row = detect(published, observations, candidates=candidates)["venues"][0]
        self.assertEqual((row["published"], row["found"], row["missing"]), (1, 1, 0))

    def test_multi_work_same_evening_is_one_recita(self):
        facts = [{"venue": "Teatro Grande", "date": "2026-12-11",
                  "starts_at": "2026-12-11T20:00:00+01:00",
                  "event_title": title} for title in
                 ("Cavalleria rusticana", "Pagliacci")]
        report = detect({"reviewed_on": "x", "productions": []},
                        {"evidence": [{"event_facts": facts}]})
        self.assertEqual(report["venues"][0]["found"], 1)
        self.assertEqual(report["venues"][0]["missing"], 1)

    def test_torino_and_parma_not_merged(self):
        published = {"reviewed_on": "x", "productions": [
            {"venue": name, "municipality": city, "region": "x",
             "dates": [["2027-01-01", "20:00"]]}
            for name, city in (("Teatro Regio", "Torino"),
                               ("Teatro Regio di Parma", "Parma"))
        ]}
        rows = detect(published, {"evidence": []})["venues"]
        self.assertEqual(len(rows), 2)

    def test_no_published_data_can_still_have_verified_found(self):
        rows = detect({"reviewed_on": "x", "productions": []},
                      {"evidence": [{"status": "needs_editorial_review",
                                     "event_facts": [{"venue": "Teatro Grande",
                                                     "date": "2027-03-01",
                                                     "starts_at": "2027-03-01T20:00:00+01:00"}]}]})["venues"]
        self.assertEqual((rows[0]["published"], rows[0]["found"], rows[0]["percent"]),
                         (0, 1, 0.0))


if __name__ == "__main__":
    unittest.main()
