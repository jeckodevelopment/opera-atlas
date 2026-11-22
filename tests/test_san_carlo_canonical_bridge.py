"""San Carlo candidate-to-canonical gate: only fully corroborated productions."""
import hashlib
import unittest

from scripts.scan_san_carlo_secondary import build_secondary_checkpoint, URL
from scripts.corroborate_san_carlo_secondary import compare
from scripts.apply_san_carlo_corroborated import apply, SOURCE_KEY


def item(title, composer, slug, rows):
    return {
        "title": title, "composer": composer,
        "venue": "Teatro di San Carlo", "city": "Napoli",
        "secondary_source": URL,
        "official_event_url": "https://www.teatrosancarlo.it/spettacoli/" + slug + "/",
        "review_status": "needs_primary_corroboration",
        "performances": [{"date": d, "time": t} for d, t in rows],
    }


def sources():
    records = [
        item("Luisa Miller", "Giuseppe Verdi", "luisa-miller", [
            ("2026-12-02", "20:00"), ("2026-12-03", "20:00")]),
        item("Otto mesi in due ore o sia Gli esiliati in Siberia",
             "Gaetano Donizetti", "otto-mesi-in-due-ore", [
                 ("2027-04-17", "20:00"), ("2027-04-21", "18:00"),
                 ("2027-04-23", "19:00")]),
    ]
    checkpoint, _ = build_secondary_checkpoint(
        records, checked_at="2026-11-22T22:00:00Z", incomplete=[]
    )
    independent = {
        "luisa miller": {"title": "Luisa Miller",
                         "dates": {"2026-12-02": "20:00", "2026-12-03": "20:00"}},
        "otto mesi in due ore o sia gli esiliati in siberia": {
            "title": "Otto mesi in due ore o sia Gli esiliati in Siberia",
            "dates": {"2027-04-17": "20:00", "2027-04-21": "20:00",
                      "2027-04-23": "20:00"}},
    }
    return checkpoint, compare(checkpoint, independent)


def empty():
    return {"schema_version": 1, "candidates": []}, {
        "schema_version": 1, "evidence": []}


class SanCarloCanonicalBridgeTests(unittest.TestCase):
    def test_only_whole_matching_productions_enter_canonical_queue(self):
        c, r = sources()
        index, detail = empty()
        index, detail, results = apply(
            c, r, index, detail, checked_at="2026-11-22T22:10:00Z")
        self.assertEqual(len(index["candidates"]), 1)
        self.assertEqual(len(detail["evidence"]), 1)
        self.assertEqual(len(detail["evidence"][0]["event_facts"]), 2)
        self.assertEqual({x["status"] for x in results},
                         {"canonical_candidate_evidence_ready",
                          "recite_conflict_or_incomplete"})
        self.assertEqual(index["candidates"][0]["source_key"], SOURCE_KEY)
        self.assertEqual(index["candidates"][0]["official_url"],
                         "https://www.teatrosancarlo.it/spettacoli/luisa-miller/")
        evidence = detail["evidence"][0]
        self.assertEqual(evidence["status"], "needs_editorial_review")
        self.assertFalse(evidence["corroboration"]["official_event_page_retrieved"])
        self.assertEqual(evidence["corroboration"]["showtimes_confirmed"], 2)
        self.assertEqual(len(index["candidates"]), len({
            x["id"] for x in index["candidates"]}))

    def test_repeated_scan_does_not_duplicate_ids(self):
        c, r = sources()
        index, detail = empty()
        index, detail, _ = apply(c, r, index, detail, checked_at="2026-11-22T22:10:00Z")
        again, details_again, _ = apply(c, r, index, detail,
                                       checked_at="2026-11-23T22:10:00Z")
        self.assertEqual([x["id"] for x in index["candidates"]],
                         [x["id"] for x in again["candidates"]])
        self.assertEqual(len(details_again["evidence"]), 1)

    def test_existing_first_party_evidence_wins(self):
        c, r = sources()
        index, detail = empty()
        url = c["productions"][0]["official_event_url"]
        cid = "oa-index-" + hashlib.sha256((SOURCE_KEY+"|"+url).encode()).hexdigest()[:20]
        index["candidates"] = [{"id": cid, "status": "needs_review",
                                "source_key": SOURCE_KEY, "official_url": url}]
        detail["evidence"] = [{"candidate_id": cid, "source_key": SOURCE_KEY,
                               "source_url": url, "status": "needs_editorial_review",
                               "event_facts": [{"first_party": True}]}]
        _, out, statuses = apply(c, r, index, detail, checked_at="now")
        self.assertEqual(out["evidence"][0]["event_facts"], [{"first_party": True}])
        self.assertIn("stronger_primary_preserved", {x["status"] for x in statuses})

    def test_unapproved_identity_or_secondary_report_fails_closed(self):
        c, r = sources()
        index, detail = empty()
        c["productions"][0]["official_event_url"] = "https://untrusted.example/opera/"
        with self.assertRaisesRegex(ValueError, "untrusted repertoire"):
            apply(c, r, index, detail, checked_at="now")
        c, r = sources()
        r["second_source"] = "https://untrusted.example/"
        with self.assertRaisesRegex(ValueError, "untrusted second publisher"):
            apply(c, r, index, detail, checked_at="now")

    def test_no_partial_production_publication(self):
        c, r = sources()
        r["productions"][0]["unmatched_clocks"] = [
            {"date": "2026-12-03", "candidate": "20:00"}]
        r["productions"][0]["confirmed_matching_clocks"] = [
            {"date": "2026-12-02", "time": "20:00"}]
        r["productions"][0]["status"] = "incomplete_second_source"
        index, detail = empty()
        index, detail, outcomes = apply(c, r, index, detail, checked_at="now")
        self.assertEqual(len(index["candidates"]), 0)
        self.assertTrue(all(x["status"] == "recite_conflict_or_incomplete"
                            for x in outcomes))


if __name__ == "__main__":
    unittest.main()
