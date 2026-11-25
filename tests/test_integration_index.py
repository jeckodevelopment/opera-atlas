import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.publish_integration_index import build, publish

REV = "a" * 40

class IntegrationIndexTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.catalog = self.root / "public/catalog"
        self.base = self.catalog / "v2"
        self.files = {}
        self.channel("works", [{"id":"w1","title":"Opera","composer":"Composer","slug":"opera"}])
        self.channel("venues", [{"id":"v1","name":"Teatro","city":"Roma","city_slug":"roma","slug":"teatro"}])
        self.channel("stagings", [{"id":"s1","work_id":"w1","venue_id":"v1","url":"/roma/teatro/opera/"}])
        self.channel("performances", [{"id":"p1","staging_id":"s1"}])
        self.manifest()
        self.write("public/catalog/venue-directory.json", {"venues":[]})
        self.write("public/catalog/v2/production-groups.json", {"groups":[]})
        self.write("public/catalog/v2/festival-index.json", {"festivals":[{"id":"fest-2026","festival_id":"fest","name":"Festival","edition":"2026","city":"Roma"}]})
        self.write("public/catalog/programs.json", {"programs":[]})
        self.write("data/composer-registry.json", {"schema_version":1,"composers":[{"id":"c1","name":"Composer"}],"work_composers":{"w1":["c1"]}})

    def write(self, path, data):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data), encoding="utf-8")
        return p

    def channel(self, key, records):
        raw = json.dumps({key:records}).encode()
        digest = hashlib.sha256(raw).hexdigest()
        path = f"data/{key}.{digest[:16]}.json"
        p = self.base / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
        self.files[key] = {"path":path,"sha256":digest,"count":len(records)}

    def manifest(self):
        self.write("public/catalog/v2/manifest.json", {"schema_version":2,"reviewed_on":"2026-11-24","files":self.files})

    def snapshot(self):
        return {p.relative_to(self.catalog):p.read_bytes() for p in self.catalog.rglob("*") if p.is_file()}

    def test_determinism_and_read_only(self):
        before = self.snapshot()
        self.assertEqual(build(self.root, REV), build(self.root, REV))
        self.assertEqual(publish(self.root, REV), 5)
        target = self.root / "public/integrations/v1/entities.json"
        first = target.read_bytes()
        publish(self.root, REV)
        self.assertEqual(target.read_bytes(), first)
        self.assertEqual(before, self.snapshot())
        entities = json.loads(first)["entities"]
        self.assertEqual({e["type"] for e in entities}, {"opera","composer","theatre","production","festival"})
        self.assertIsNone(next(e for e in entities if e["type"]=="composer")["url"])
        self.assertEqual(next(e for e in entities if e["type"]=="opera")["composer_ids"], ["c1"])

    def test_invalid_digest_preserves_previous_export(self):
        publish(self.root, REV)
        target = self.root / "public/integrations/v1/entities.json"
        previous = target.read_bytes()
        (self.base / self.files["works"]["path"]).write_bytes(b"{}")
        with self.assertRaises(ValueError):
            publish(self.root, REV)
        self.assertEqual(target.read_bytes(), previous)

    def test_unsafe_route_rejected(self):
        self.channel("stagings", [{"id":"s1","work_id":"w1","venue_id":"v1","url":"//example.org/"}])
        self.manifest()
        with self.assertRaises(ValueError):
            build(self.root, REV)

    def test_duplicate_work_rejected(self):
        self.channel("works", [{"id":"w1"},{"id":"w1"}])
        self.manifest()
        with self.assertRaises(ValueError):
            build(self.root, REV)

    def test_exact_alias_and_unknown_composer(self):
        self.write("data/composer-registry.json", {"schema_version":1,"composers":[{"id":"c1","name":"Composer","aliases":["Alias"]}],"work_composers":{}})
        self.channel("works", [{"id":"w1","title":"Opera","composer":"  ALIAS ","slug":"opera"},{"id":"w2","title":"New","composer":"Unknown","slug":"new"}])
        self.manifest()
        result = build(self.root, REV)
        works = {e["id"]: e for e in result["entities"] if e["type"]=="opera"}
        self.assertEqual(works["w1"]["composer_ids"], ["c1"])
        self.assertEqual(works["w2"]["composer_ids"], [])
        self.assertEqual(result["diagnostics"]["unresolved_composer_works"], [{"work_id":"w2","composer":"Unknown"}])

    def test_ambiguous_alias_not_guessed(self):
        self.write("data/composer-registry.json", {"schema_version":1,"composers":[{"id":"c1","name":"Composer"},{"id":"c2","name":"Other","aliases":["Composer"]}],"work_composers":{}})
        result = build(self.root, REV)
        self.assertEqual(next(e for e in result["entities"] if e["type"]=="opera")["composer_ids"], [])
        self.assertEqual(len(result["diagnostics"]["unresolved_composer_works"]), 1)

    def test_verified_portrait_and_unsafe_url(self):
        portrait = {"verified":True,"url":"https://upload.wikimedia.org/example.jpg","alt":"Portrait","source_url":"https://commons.wikimedia.org/wiki/File:Example.jpg","author":"Example author","license":"CC-BY-4.0","license_url":"https://creativecommons.org/licenses/by/4.0/","credit":"Example credit"}
        for change, expected in [({}, True), ({"license":"CC-BY-SA-2.5","license_url":"https://creativecommons.org/licenses/by-sa/2.5/"}, True), ({"license":"CC-BY-SA-3.0-DE","license_url":"https://creativecommons.org/licenses/by-sa/3.0/de/"}, True), ({"url":"https://thumb.wikimedia.org/wikipedia/commons/thumb/a/ab/example.jpg/960px-example.jpg"}, True), ({"url":"https://thumb.wikimedia.org.evil.example/image.jpg"}, False), ({"license":"Public Domain","license_url":"https://commons.wikimedia.org/wiki/File:Example.jpg"}, True), ({"verified":False}, False), ({"url":"https://evil.example/image.jpg"}, False), ({"license":"Unknown"}, False), ({"author":""}, False), ({"url":"https://upload.wikimedia.org@evil.example/image.jpg"}, False)]:
            self.write("data/composer-portraits.json", {"schema_version":1,"portraits":{"c1":dict(portrait, **change)}})
            entities = build(self.root, REV)["entities"]
            for kind in ("composer","opera"):
                image = next(e for e in entities if e["type"]==kind)["image"]
                self.assertEqual(image is not None, expected)
                if expected:
                    self.assertEqual(image["credit"], "Example credit")

    def test_documentary_image_kind_is_preserved(self):
        photo = {"verified": True, "url": "https://upload.wikimedia.org/example.jpg",
                 "alt": "Two performers in concert",
                 "source_url": "https://commons.wikimedia.org/wiki/File:Example.jpg",
                 "author": "Photographer", "license": "CC-BY-SA-3.0",
                 "license_url": "https://creativecommons.org/licenses/by-sa/3.0/",
                 "credit": "Photographer — documentary photograph",
                 "media_kind": "documentary_photo"}
        self.write("data/composer-portraits.json", {"schema_version": 1, "portraits": {"c1": photo}})
        result = build(self.root, REV)["entities"]
        self.assertEqual(next(e for e in result if e["type"] == "composer")["image"]["media_kind"], "documentary_photo")
        photo["media_kind"] = "unknown"
        self.write("data/composer-portraits.json", {"schema_version": 1, "portraits": {"c1": photo}})
        self.assertIsNone(next(e for e in build(self.root, REV)["entities"] if e["type"] == "composer")["image"])

    def test_unknown_portrait_id_rejected(self):
        self.write("data/composer-portraits.json", {"schema_version":1,"portraits":{"unknown":{}}})
        with self.assertRaises(ValueError):
            build(self.root, REV)

if __name__ == "__main__":
    unittest.main()
