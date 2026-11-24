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

    def test_future_official_sources_associate_with_permanent_festivals(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from scripts import publish_catalog_v2 as publisher
        registry = json.loads(publisher.REGISTRY.read_text(encoding="utf-8"))
        cases = [
            ("puccini", "festival-puccini", "2028",
             "https://www.puccinifestival.it/en/74th-puccini-festival-2028/"),
            ("trapani", "luglio-musicale-trapanese", "2027",
             "https://www.lugliomusicale.it/it/luglio-musicale-stagioni/stagione-2027/tosca/"),
        ]
        for key, festival, year, url in cases:
            registry["stagings"]["test-" + key] = {
                "id": "test-" + key, "season": year, "source_url": url}
            registry["stagings"]["wrong-" + key] = {
                "id": "wrong-" + key, "season": "2029", "source_url": url}
        with tempfile.TemporaryDirectory() as folder:
            public = Path(folder)
            index = public / "festival-index.json"
            index.write_bytes((publisher.PUBLIC / index.name).read_bytes())
            with patch.object(publisher, "PUBLIC", public):
                publisher.sync_festival_index(registry)
                publisher.sync_festival_identities(registry)
                publisher.sync_festival_index(registry, check=True)
                publisher.sync_festival_identities(registry, check=True)
            directory = json.loads((public / "festival-directory.json").read_text())
            for key, festival, year, url in cases:
                record = next(f for f in directory["festivals"] if f["id"] == festival)
                edition = next(e for e in record["editions"] if e["edition"] == year)
                self.assertIn("test-" + key, edition["staging_ids"])
                self.assertNotIn("wrong-" + key, record["staging_ids"])
