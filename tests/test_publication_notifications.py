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
        self.assertEqual([n["kind"] for n in notices], ["Nuova opera", "Nuova produzione"])
        self.assertEqual(notices[0]["url"], "https://opera.plus/atlas/opere/la-traviata/")
        self.assertEqual(notices[1]["url"], "https://opera.plus/atlas/torino/teatro-regio/la-traviata/")

    def test_no_repeat_for_updated_existing_entity(self):
        before = {key: dict(value) for key, value in self.after.items()}
        self.assertEqual(new_entities(before, self.after), [])

    def test_new_production_of_existing_opera(self):
        before = {key: dict(value) for key, value in self.after.items()}
        before["stagings"] = {}
        notices = new_entities(before, self.after)
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0]["kind"], "Nuova produzione")

    def test_resend_request_has_idempotency_key(self):
        notice = new_entities(self.before, self.after)[0]
        response = MagicMock()
        response.status = 200
        response.__enter__.return_value = response
        with patch("scripts.notify_publications.urllib.request.urlopen", return_value=response) as call:
            send(notice, "fake-api-key", "Atlas <atlas@example.org>", ["one@example.org", "two@example.org"])
        request = call.call_args.args[0]
        self.assertEqual(request.get_header("Idempotency-key"), "atlas-published-oa-w-1")
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

    def test_direct_merged_feed_notifications_are_enabled(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/notify-catalog-publications.yml").read_text(encoding="utf-8")
        self.assertIn("public/catalog/v2/manifest.json", workflow)
        self.assertIn("fetch-depth: 0", workflow)
        self.assertIn("github.event.before", workflow)
        self.assertIn("secrets.ATLAS_NOTIFICATION_TO", workflow)
        self.assertIn("--only-ids", workflow)

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
