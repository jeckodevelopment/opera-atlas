"""Publication diagnostics: only newly published work/staging identities notify."""
import json
import unittest
from unittest.mock import patch, MagicMock
from scripts.notify_publications import new_entities, send, parse_recipients


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
        self.assertEqual(json.loads(request.data)["to"], ["one@example.org", "two@example.org"])

    def test_multiple_secret_recipients_are_trimmed_and_deduplicated(self):
        self.assertEqual(parse_recipients(" one@example.org, two@example.org\nONE@example.org"),
                         ["one@example.org", "two@example.org"])

    def test_malformed_secret_recipients_are_rejected(self):
        with self.assertRaises(ValueError):
            parse_recipients("one@example.org, not-an-email")


if __name__ == "__main__":
    unittest.main()
