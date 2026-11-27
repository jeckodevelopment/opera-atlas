import unittest
from opera_atlas.source_failure_history import with_history, outage

class FailureHistoryTests(unittest.TestCase):
    def test_two_distinct_failures_across_24h_and_recovery(self):
        bad={"status":"unavailable_or_invalid"}
        a=with_history(bad,{},checked_at="2026-11-27T10:00:00Z")
        self.assertEqual(a["consecutive_failures"],1)
        same=with_history(bad,a,checked_at="2026-11-27T10:00:00Z")
        self.assertEqual(same["consecutive_failures"],1)
        self.assertFalse(outage(same)["requires_technical_attention"])
        b=with_history(bad,a,checked_at="2026-11-28T09:59:59Z")
        self.assertFalse(outage(b)["requires_technical_attention"])
        c=with_history(bad,b,checked_at="2026-11-28T10:00:00Z")
        self.assertTrue(outage(c)["requires_technical_attention"])
        self.assertEqual(c["consecutive_failures"],3)
        ok=with_history({"status":"success"},c,checked_at="2026-11-28T11:00:00Z")
        self.assertIsNone(ok["first_failure_at"])
        self.assertEqual(ok["consecutive_failures"],0)
        new=with_history(bad,ok,checked_at="2026-11-28T12:00:00Z")
        self.assertFalse(outage(new)["requires_technical_attention"])

    def test_future_programme_unverified_is_not_technical_failure(self):
        r=with_history({"status":"unavailable_or_invalid",
                        "diagnostic":"future_official_programme_unverified"},
                       {},checked_at="2026-11-27T10:00:00Z")
        self.assertEqual(outage(r)["failure_state"],"none")

    def test_legacy_daily_snapshot_uses_observed_failure_not_success(self):
        bad={"outcome":"unavailable_or_invalid"}
        r=with_history(bad,bad,checked_at="2026-11-28T10:00:00Z",
                       previous_checked_at="2026-11-27T10:00:00Z",field="outcome")
        self.assertTrue(outage(r,field="outcome")["requires_technical_attention"])
        review=with_history({"outcome":"review_required"},r,
                            checked_at="2026-11-28T11:00:00Z",field="outcome")
        self.assertEqual(outage(review,field="outcome")["failure_state"],"none")

    def test_unverified_old_snapshot_does_not_invent_failure_duration(self):
        r=with_history({"status":"unavailable_or_invalid"},
                       {"status":"success","last_attempt_at":"2026-11-01T10:00:00Z"},
                       checked_at="2026-11-28T10:00:00Z")
        self.assertEqual(outage(r)["failure_hours"],0)
        self.assertFalse(outage(r)["requires_technical_attention"])
