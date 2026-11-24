import unittest

from scripts.publish_catalog_v2 import build_festival_directory


class PermanentFestivalTests(unittest.TestCase):
    def setUp(self):
        self.identities = {"schema_version": 1, "festivals": [
            {"id": "festival-a", "name": "Festival A"},
            {"id": "festival-b", "name": "Festival B"},
        ]}
        self.editions = {"schema_version": 1, "festivals": [
            {"id": "festival-a-2026", "festival_id": "festival-a", "edition": "2026",
             "official_url": "https://example.org/2026", "staging_ids": ["s1"]},
            {"id": "festival-a-2027", "festival_id": "festival-a", "edition": "2027",
             "official_url": "https://example.org/2027", "staging_ids": ["s1", "s2"]},
        ]}
        self.registry = {"stagings": {"one": {"id": "s1"}, "two": {"id": "s2"}}}

    def test_stable_identity_and_history(self):
        result = build_festival_directory(self.identities, self.editions, self.registry)
        a, b = result["festivals"]
        self.assertEqual(a["id"], "festival-a")
        self.assertEqual(len(a["editions"]), 2)
        self.assertEqual(a["staging_ids"], ["s1", "s2"])
        self.assertEqual(b["editions"], [])
        self.assertEqual(b["staging_ids"], [])

    def test_unknown_staging_rejected(self):
        self.editions["festivals"][0]["staging_ids"] = ["unknown"]
        with self.assertRaises(ValueError):
            build_festival_directory(self.identities, self.editions, self.registry)

    def test_duplicate_edition_rejected(self):
        self.editions["festivals"].append(dict(self.editions["festivals"][0]))
        with self.assertRaises(ValueError):
            build_festival_directory(self.identities, self.editions, self.registry)
