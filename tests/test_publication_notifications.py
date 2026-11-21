"""Publication diagnostics: only newly published work/staging identities notify."""
import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from scripts.notify_publications import new_entities, send, parse_recipients
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

    def test_multiple_secret_recipients_are_trimmed_and_deduplicated(self):
        self.assertEqual(parse_recipients(" one@example.org, two@example.org\nONE@example.org"),
                         ["one@example.org", "two@example.org"])

    def test_malformed_secret_recipients_are_rejected(self):
        with self.assertRaises(ValueError):
            parse_recipients("one@example.org, not-an-email")


if __name__ == "__main__":
    unittest.main()
