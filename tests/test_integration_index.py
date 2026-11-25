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

    def test_editorial_image_does_not_become_default_image(self):
        photo = {"name": "Composer", "url": "https://www.quirinale.it/APIRed/api/media/static/6080",
                 "alt": "Photo", "source_url": "https://www.quirinale.it/it/foto/example",
                 "author": "Quirinale", "credit": "Quirinale — non-commercial",
                 "license": "Institutional non-commercial editorial use",
                 "license_url": "https://www.quirinale.it/it/pagine/guida-navigazione",
                 "media_kind": "documentary_photo", "usage": "noncommercial_public_interest_information",
                 "preserve_integrity": True}
        self.write("data/composer-editorial-images.json", {"schema_version": 1, "images": {"c1": photo}})
        entities = build(self.root, REV)["entities"]
        composer = next(e for e in entities if e["type"] == "composer")
        self.assertIsNone(composer["image"])
        self.assertEqual(composer["editorial_image"]["url"], photo["url"])
        self.assertTrue(composer["editorial_image"]["preserve_integrity"])
        self.assertNotIn("editorial_image", next(e for e in entities if e["type"] == "opera"))
        photo["url"] = "https://evil.example/image.jpg"
        self.write("data/composer-editorial-images.json", {"schema_version": 1, "images": {"c1": photo}})
        with self.assertRaises(ValueError):
            build(self.root, REV)

    def test_archival_document_is_composer_only(self):
        photo = {"verified": True, "url": "https://upload.wikimedia.org/example.jpg",
                 "alt": "Historical score, not a portrait",
                 "source_url": "https://commons.wikimedia.org/wiki/File:Example.jpg",
                 "author": "Composer", "license": "Public Domain",
                 "license_url": "https://creativecommons.org/publicdomain/mark/1.0/",
                 "credit": "Autograph score", "media_kind": "archival_document"}
        self.write("data/composer-portraits.json", {"schema_version": 1, "portraits": {"c1": photo}})
        entities = build(self.root, REV)["entities"]
        self.assertEqual(next(e for e in entities if e["type"] == "composer")["image"]["media_kind"], "archival_document")
        self.assertIsNone(next(e for e in entities if e["type"] == "opera")["image"])

    def test_gai_editorial_derivative_query_is_pinned(self):
        photo = {"name": "Composer", "url": "https://www.giovaniartisti.it/sites/default/files/styles/artisti_full/public/artisti/aloisi-gaia/gaia-aloisi0.png?h=5871340f&itok=uJcpNeYj",
                 "alt": "Profile portrait", "source_url": "https://www.giovaniartisti.it/artista/aloisi-gaia",
                 "author": "Not specified", "credit": "GAI",
                 "license": "GAI reproduction terms",
                 "license_url": "https://www.giovaniartisti.it/note-legali",
                 "media_kind": "portrait", "usage": "gai_noncommercial_editorial",
                 "preserve_integrity": True}
        self.write("data/composer-editorial-images.json", {"schema_version": 1, "images": {"c1": photo}})
        composer = next(e for e in build(self.root, REV)["entities"] if e["type"] == "composer")
        self.assertIsNone(composer["image"])
        self.assertEqual(composer["editorial_image"]["url"], photo["url"])
        photo["url"] += "&redirect=evil.example"
        self.write("data/composer-editorial-images.json", {"schema_version": 1, "images": {"c1": photo}})
        with self.assertRaises(ValueError):
            build(self.root, REV)

    def test_source_reference_is_link_only(self):
        ref = {"name": "Composer", "source_url": "https://example.org/artist",
               "source": "Artist site", "kind": "portrait",
               "image_url": "https://example.org/portrait.jpg", "author": "Photographer",
               "usage": "external_link_only", "rights_status": "reuse_not_established"}
        self.write("data/composer-source-references.json", {"schema_version": 1, "references": {"c1": ref}})
        entities = build(self.root, REV)["entities"]
        composer = next(e for e in entities if e["type"] == "composer")
        self.assertIsNone(composer["image"])
        self.assertNotIn("editorial_image", composer)
        self.assertEqual(composer["source_reference"]["image_url"], ref["image_url"])
        self.assertNotIn("source_reference", next(e for e in entities if e["type"] == "opera"))
        ref["image_url"] = "javascript:alert(1)"
        self.write("data/composer-source-references.json", {"schema_version": 1, "references": {"c1": ref}})
        with self.assertRaises(ValueError):
            build(self.root, REV)

    def test_fenice_press_photo_is_pinned_to_composer(self):
        from scripts.publish_integration_index import load_editorial_media
        image = {"name": "Davide Tramontano", "url": "https://www.teatrolafenice.it/wp-content/uploads/2026/05/IMG_8887-scaled.jpg",
                 "source_url": "https://www.teatrolafenice.it/event/premio-una-vita-nella-musica-2026/",
                 "alt": "Award ceremony", "author": "Ufficio stampa Fondazione Teatro La Fenice",
                 "license": "Press material (editorial source)",
                 "license_url": "https://www.teatrolafenice.it/en/press-lafenice/",
                 "credit": "Press office", "media_kind": "documentary_photo",
                 "usage": "fenice_press_material_editorial", "preserve_integrity": True}
        composers = {"oa-c-000018": {"name": "Davide Tramontano"}}
        self.write("data/composer-editorial-images.json", {"schema_version": 1, "images": {"oa-c-000018": image}})
        self.assertEqual(load_editorial_media(self.root, composers)["oa-c-000018"]["url"], image["url"])
        image["url"] += ".jpg"
        self.write("data/composer-editorial-images.json", {"schema_version": 1, "images": {"oa-c-000018": image}})
        with self.assertRaises(ValueError):
            load_editorial_media(self.root, composers)

    def test_pinned_municipal_image(self):
        from scripts.publish_integration_index import PALERMO_MEDIA, verified_image
        photo = dict(PALERMO_MEDIA, verified=True, alt="Cerimonia di consegna",
                     author="Ufficio Stampa del Comune di Palermo", credit="Comune di Palermo — CC BY 4.0")
        self.assertEqual(verified_image(photo, "oa-c-000065")["rights_source_url"],
                         photo["rights_source_url"])
        self.assertIsNone(verified_image(photo, "oa-c-000002"))
        for key in PALERMO_MEDIA:
            self.assertIsNone(verified_image(dict(photo, **{key: "https://evil.example/"}),
                                             "oa-c-000065"))

    def test_furlati_press_photo_is_pinned_to_composer_and_asset(self):
        from scripts.publish_integration_index import load_editorial_media
        source = "https://www.unionesarda.it/cultura/creuza-de-ma-chiude-la-sua-19-edizione-a-cagliari-due-giorni-di-cinema-muto-e-musica-dal-vivo-f1duczxa"
        image = {"name": "Daniele Furlati", "url": "https://immagini.unionesarda.it/version/c%3AZDhmNzY0ODctMTg0MS00%3AMTkzOWEyZTAtY2I4OC00/image.webp?f=3%3A2&q=0.75&w=3840",
                 "source_url": source, "alt": "Press photo", "author": "Ufficio stampa",
                 "license": "Press material (editorial source)", "license_url": source,
                 "credit": "Press office; no open license declared", "media_kind": "portrait",
                 "usage": "furlati_press_material_editorial", "preserve_integrity": True}
        composers = {"oa-c-000016": {"name": "Daniele Furlati"}, "c1": {"name": "Daniele Furlati"}}
        self.write("data/composer-editorial-images.json", {"schema_version": 1, "images": {"oa-c-000016": image}})
        self.assertEqual(load_editorial_media(self.root, composers)["oa-c-000016"]["url"], image["url"])
        for field in ("url", "source_url", "license_url", "license"):
            self.write("data/composer-editorial-images.json", {"schema_version": 1, "images": {"oa-c-000016": dict(image, **{field: image[field] + "x"})}})
            with self.assertRaises(ValueError):
                load_editorial_media(self.root, composers)
        self.write("data/composer-editorial-images.json", {"schema_version": 1, "images": {"c1": image}})
        with self.assertRaises(ValueError):
            load_editorial_media(self.root, composers)

    def test_public_source_editorial_link_is_exact_and_not_open_license(self):
        from scripts.publish_integration_index import load_editorial_media
        photo = {"name":"Alessandro Solbiati","url":"https://levivier.ca/sites/default/files/styles/mt_member_photo/public/fiches-individuelles/Alessandro%20Solbiati.jpg.webp?itok=sA4aMc_A","alt":"Fotografia di Alessandro Solbiati pubblicata dalla fonte","source_url":"https://levivier.ca/en/artists/alessandro-solbiati","author":"Fotografo non indicato","license":"External editorial photograph — reuse rights not established","license_url":"https://levivier.ca/en/artists/alessandro-solbiati","credit":"Fotografo non indicato — Le Vivier. Immagine collegata alla fonte originale, nessuna licenza di riproduzione accertata.","media_kind":"portrait","usage":"public_source_editorial_link","preserve_integrity": True}
        composers = {"oa-c-000002": {"name": "Alessandro Solbiati"}, "c1": {"name": "Alessandro Solbiati"}}
        self.write("data/composer-editorial-images.json", {"schema_version": 1, "images": {"oa-c-000002": photo}})
        entry = load_editorial_media(self.root, composers)["oa-c-000002"]
        self.assertEqual(entry["rights_status"], "reuse_not_established")
        for field in ("url", "source_url", "author", "license", "license_url"):
            self.write("data/composer-editorial-images.json", {"schema_version": 1, "images": {"oa-c-000002": dict(photo, **{field: photo[field] + "x"})}})
            with self.assertRaises(ValueError):
                load_editorial_media(self.root, composers)
        self.write("data/composer-editorial-images.json", {"schema_version": 1, "images": {"c1": photo}})
        with self.assertRaises(ValueError):
            load_editorial_media(self.root, composers)

    def test_combined_media_coverage_does_not_count_source_links(self):
        ref = {"name": "Composer", "source_url": "https://example.org/artist",
               "source": "Artist site", "kind": "profile",
               "usage": "external_link_only", "rights_status": "reuse_not_established"}
        self.write("data/composer-source-references.json", {"schema_version": 1, "references": {"c1": ref}})
        coverage = build(self.root, REV)["diagnostics"]["composer_media_coverage"]
        self.assertEqual(coverage, {"total": 1, "with_image": 0, "default_image": 0,
                                    "editorial_image": 0, "missing": ["c1"]})
        photo = {"verified": True, "url": "https://upload.wikimedia.org/example.jpg",
                 "alt": "Portrait", "source_url": "https://commons.wikimedia.org/wiki/File:Example.jpg",
                 "author": "Photographer", "license": "CC-BY-4.0",
                 "license_url": "https://creativecommons.org/licenses/by/4.0/", "credit": "Credit"}
        self.write("data/composer-portraits.json", {"schema_version": 1, "portraits": {"c1": photo}})
        coverage = build(self.root, REV)["diagnostics"]["composer_media_coverage"]
        self.assertEqual(coverage, {"total": 1, "with_image": 1, "default_image": 1,
                                    "editorial_image": 0, "missing": []})

    def test_unknown_portrait_id_rejected(self):
        self.write("data/composer-portraits.json", {"schema_version":1,"portraits":{"unknown":{}}})
        with self.assertRaises(ValueError):
            build(self.root, REV)

if __name__ == "__main__":
    unittest.main()
