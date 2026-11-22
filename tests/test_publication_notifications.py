"""Publication diagnostics: only newly published work/staging identities notify."""
import json
import io
import urllib.error
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from scripts.notify_publications import new_entities, send, parse_recipients, safe_resend_error
from scripts.notification_email import render_email


class PublicationNotificationsTest(unittest.TestCase):
    def setUp(self):
        self.work = {"id": "oa-w-1", "title": "La traviata", "composer": "Giuseppe Verdi", "slug": "la-traviata"}
        self.venue = {"id": "oa-v-1", "name": "Teatro Regio", "city": "Torino", "slug": "teatro-regio", "city_slug": "torino"}
        self.staging = {"id": "oa-s-1", "work_id": "oa-w-1", "venue_id": "oa-v-1"}
        self.before = {"works": {}, "venues": {}, "stagings": {}}
        self.after = {
            "works": {"oa-w-1": self.work},
            "venues": {"oa-v-1": self.venue},
            "stagings": {"oa-s-1": self.staging},
        }

    def test_new_work_and_production(self):
        notices = new_entities(self.before, self.after)
        self.assertEqual([n["kind"] for n in notices], ["Nuova opera", "Nuovo teatro", "Nuova produzione"])
        self.assertEqual(notices[0]["url"], "https://opera.plus/atlas/opere/la-traviata/")
        self.assertEqual(notices[1]["url"], "https://opera.plus/atlas/torino/teatro-regio/")
        self.assertEqual(notices[2]["url"], "https://opera.plus/atlas/torino/teatro-regio/la-traviata/")

    def test_no_repeat_for_updated_existing_entity(self):
        before = {key: dict(value) for key, value in self.after.items()}
        self.assertEqual(new_entities(before, self.after), [])

    def test_new_production_of_existing_opera(self):
        before = {key: dict(value) for key, value in self.after.items()}
        before["stagings"] = {}
        notices = new_entities(before, self.after)
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0]["kind"], "Nuova produzione")

    def test_production_email_contains_sorted_upcoming_recite_and_known_times(self):
        self.after["performances"] = {
            "r2": {"id": "r2", "staging_id": "oa-s-1", "local_date": "2099-12-15",
                   "starts_at": "2099-12-15T20:30:00+01:00", "time_known": True, "status": "announced"},
            "r1": {"id": "r1", "staging_id": "oa-s-1", "local_date": "2099-12-12",
                   "starts_at": "2099-12-12T18:00:00+01:00", "time_known": False, "status": "announced"},
            "other": {"id": "other", "staging_id": "unrelated", "local_date": "2099-12-11",
                      "time_known": False, "status": "announced"},
            "past": {"id": "past", "staging_id": "oa-s-1", "local_date": "2020-01-03",
                     "time_known": False, "status": "announced"},
            "cancelled": {"id": "cancelled", "staging_id": "oa-s-1", "local_date": "2099-12-13",
                          "time_known": False, "status": "cancelled"},
        }
        notice = new_entities(self.before, self.after)[2]
        html, plain = render_email(notice)
        self.assertIn("12 dicembre 2099", plain)
        self.assertIn("15 dicembre 2099 · ore 20:30", plain)
        self.assertLess(plain.index("12 dicembre"), plain.index("15 dicembre"))
        self.assertNotIn("18:00", plain)
        self.assertNotIn("11 dicembre", plain)
        self.assertIn("13 dicembre 2099", plain)
        self.assertIn("3 gennaio 2020", html)
        self.assertIn("Recite censite", html)
        self.assertIn("15 dicembre 2099", html)

    def test_production_without_public_recite_shows_explicit_absence(self):
        notice = new_entities(self.before, self.after)[1]
        html, plain = render_email(notice)
        self.assertIn("Recite censite:", plain)
        self.assertIn("Nessuna recita censita", plain)
        self.assertIn("Nessuna recita censita", html)

    def test_new_work_mail_does_not_show_performance_dates(self):
        notice = new_entities(self.before, self.after)[0]
        html, plain = render_email(notice)
        self.assertNotIn("Recite censite:", plain)
        self.assertNotIn("Nessuna recita censita", html)

    def test_new_venue_email_contains_location_and_canonical_link(self):
        notice = new_entities(self.before, self.after)[1]
        html, plain = render_email(notice)
        self.assertEqual(notice["kind"], "Nuovo teatro")
        self.assertIn("Teatro Regio", plain)
        self.assertIn("Città: Torino", plain)
        self.assertIn("https://opera.plus/atlas/torino/teatro-regio/", html)
        self.assertNotIn("Recite censite", plain)

    def test_existing_venue_does_not_trigger_when_new_staging_published(self):
        before = {key: dict(value) for key, value in self.after.items()}
        before["stagings"] = {}
        notices = new_entities(before, self.after)
        self.assertEqual([n["kind"] for n in notices], ["Nuova produzione"])

    def test_historical_only_staging_shows_all_known_dates(self):
        self.after["performances"] = {
            "past1": {"id": "past1", "staging_id": "oa-s-1",
                      "local_date": "2026-10-18", "starts_at": "2026-10-18T18:00:00+02:00",
                      "time_known": True, "status": "announced"},
            "past2": {"id": "past2", "staging_id": "oa-s-1",
                      "local_date": "2026-10-20", "starts_at": "2026-10-20T21:00:00+02:00",
                      "time_known": True, "status": "announced"},
        }
        notice = new_entities(self.before, self.after)[2]
        html, plain = render_email(notice)
        self.assertIn("18 ottobre 2026 · ore 18:00", plain)
        self.assertIn("20 ottobre 2026 · ore 21:00", html)
        self.assertNotIn("Nessuna recita censita", plain)

    def test_resend_request_has_idempotency_key(self):
        notice = new_entities(self.before, self.after)[0]
        response = MagicMock()
        response.status = 200
        response.__enter__.return_value = response
        with patch("scripts.notify_publications.urllib.request.urlopen", return_value=response) as call:
            send(notice, "fake-api-key", "Atlas <atlas@example.org>", ["one@example.org", "two@example.org"])
        request = call.call_args.args[0]
        self.assertEqual(request.get_header("Idempotency-key"), "atlas-published-oa-w-1")
        self.assertEqual(request.get_header("User-agent"), "OperaAtlas-Notifications/1.0 (GitHub Actions; jeckodevelopment/opera-atlas)")
        self.assertIn(b"Nuova opera", request.data)
        body = json.loads(request.data)
        self.assertEqual(body["to"], ["one@example.org", "two@example.org"])
        self.assertIn("OPERA", body["html"])
        self.assertIn("Nuova opera", body["text"])
        self.assertIn("Apri la scheda", body["text"])

    def test_branded_template_escapes_catalog_values(self):
        notice = new_entities(self.before, self.after)[0]
        notice["title"] = '<script>alert("bad")</script>'
        notice["details"] = '<img src=x onerror=bad()>'
        html, plain = render_email(notice)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;img", html)
        self.assertIn("OPERA", html)
        self.assertIn("+ ATLAS", html)
        self.assertIn("background:#151515", html)
        self.assertIn("Notifica diagnostica", plain)

    def test_branded_template_rejects_offsite_link(self):
        notice = new_entities(self.before, self.after)[0]
        notice["url"] = "https://example.org/phishing"
        with self.assertRaises(ValueError):
            render_email(notice)

    def test_durable_worker_covers_merges_refresh_dispatch_and_scheduled_retries(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/deliver-publication-notifications.yml").read_text(encoding="utf-8")
        refresh = (root / ".github/workflows/refresh-catalog.yml").read_text(encoding="utf-8")
        legacy = (root / ".github/workflows/notify-catalog-publications.yml").read_text(encoding="utf-8")
        self.assertIn("public/catalog/v2/manifest.json", workflow)
        self.assertIn("atlas-notification-reconcile", workflow)
        self.assertIn("schedule:", workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertIn("scripts.process_notification_outbox", workflow)
        self.assertEqual(refresh.count("event_type=atlas-notification-reconcile"), 2)
        self.assertNotIn("python -m scripts.notify_publications", refresh)
        self.assertNotIn("  push:", legacy)
        self.assertIn("--only-ids", legacy)

    def test_durable_outbox_retries_only_unaccepted_new_entities(self):
        from scripts.process_notification_outbox import pending_notices
        notices = pending_notices(self.before, self.after, {"oa-w-1"})
        self.assertEqual([n["id"] for n in notices], ["oa-v-1", "oa-s-1"])
        self.assertEqual(pending_notices(self.before, self.after, {"oa-w-1", "oa-v-1", "oa-s-1"}), [])
        self.assertEqual(pending_notices(self.after, self.after, set()), [])

    def test_outbox_state_uses_private_branch_not_main(self):
        from scripts.process_notification_outbox import LEDGER_BRANCH, LEDGER_PATH
        self.assertEqual(LEDGER_BRANCH, "atlas-notification-ledger")
        self.assertEqual(LEDGER_PATH, "data/notification-ledger.json")

    def test_replay_filter_only_selects_existing_published_entities(self):
        notice = new_entities(self.before, self.after)
        selected = {"oa-w-1", "oa-w-unpublished"}
        self.assertEqual([n["id"] for n in notice if n["id"] in selected], ["oa-w-1"])

    def test_resend_403_reports_structured_code_but_never_message_or_email(self):
        body = json.dumps({
            "name": "validation_error",
            "message": "Cannot send from private@example.org with bearer re_SECRET",
        }).encode("utf-8")
        error = urllib.error.HTTPError(
            "https://api.resend.com/emails", 403, "Forbidden", {}, io.BytesIO(body)
        )
        diagnosis = safe_resend_error(error)
        self.assertIn("403", diagnosis)
        self.assertIn("validation_error", diagnosis)
        self.assertNotIn("private@example.org", diagnosis)
        self.assertNotIn("re_SECRET", diagnosis)

    def test_resend_error_ignores_untrusted_or_malformed_code(self):
        error = urllib.error.HTTPError(
            "https://api.resend.com/emails", 403, "Forbidden", {},
            io.BytesIO(b'{"name":"sensitive@example.org"}')
        )
        diagnosis = safe_resend_error(error)
        self.assertIn("403", diagnosis)
        self.assertNotIn("sensitive@example.org", diagnosis)

    def test_resend_error_handles_non_json_body(self):
        error = urllib.error.HTTPError(
            "https://api.resend.com/emails", 403, "Forbidden", {},
            io.BytesIO(b"some raw private content")
        )
        self.assertIn("body-format=text", safe_resend_error(error))

    def test_html_403_classified_without_leaking_response_content(self):
        error = urllib.error.HTTPError(
            "https://api.resend.com/emails", 403, "Forbidden",
            {"Content-Type": "text/html; charset=utf-8", "CF-Ray": "trace-private@example.org"},
            io.BytesIO(b"<html>Bearer re_SECRET private@example.org</html>")
        )
        diagnosis = safe_resend_error(error)
        self.assertIn("response-type=text/html", diagnosis)
        self.assertIn("body-format=html", diagnosis)
        self.assertIn("edge-header-present=yes", diagnosis)
        self.assertNotIn("private@example.org", diagnosis)
        self.assertNotIn("re_SECRET", diagnosis)
        self.assertNotIn("trace-", diagnosis)

    def test_nested_api_error_code_and_unknown_content_type(self):
        error = urllib.error.HTTPError(
            "https://api.resend.com/emails", 403, "Forbidden",
            {"Content-Type": "text/custom-private@example.org"},
            io.BytesIO(b'{"error":{"code":"restricted_api_key","message":"private@example.org"}}')
        )
        diagnosis = safe_resend_error(error)
        self.assertIn("response-type=other/unknown", diagnosis)
        self.assertIn("body-format=json", diagnosis)
        self.assertIn("error-code=restricted_api_key", diagnosis)
        self.assertNotIn("private@example.org", diagnosis)

    def test_multiple_secret_recipients_are_trimmed_and_deduplicated(self):
        self.assertEqual(parse_recipients(" one@example.org, two@example.org\nONE@example.org"),
                         ["one@example.org", "two@example.org"])

    def test_malformed_secret_recipients_are_rejected(self):
        with self.assertRaises(ValueError):
            parse_recipients("one@example.org, not-an-email")


if __name__ == "__main__":
    unittest.main()
