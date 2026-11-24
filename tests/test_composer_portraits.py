import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.error import HTTPError
from scripts.refresh_composer_portraits import WD, COMMONS, portrait, find_person, refresh, WikimediaError, api, PUBLIC_DOMAIN_URL

def claim(value):
    return {"mainsnak":{"datavalue":{"value":value}}}

def person(name="Composer", occupation="Q36834"):
    return {"labels":{"en":{"value":name}}, "claims":{
        "P31":[claim({"id":"Q5"})], "P106":[claim({"id":occupation})],
        "P18":[claim("Portrait.jpg")]}}

def mock_call(entities=None, changes=None):
    entities = entities or {"Q123":person()}
    def call(endpoint, **params):
        if endpoint == WD:
            if params["action"] == "wbsearchentities":
                return {"search":[{"id":key} for key in entities]}
            return {"entities":entities}
        assert endpoint == COMMONS
        meta = {"LicenseShortName":"CC BY 4.0","LicenseUrl":"https://creativecommons.org/licenses/by/4.0/",
                "Artist":"<a>Author</a>","Copyrighted":"True"}
        meta.update(changes or {})
        return {"query":{"pages":{"1":{"imageinfo":[{"mime":"image/jpeg",
            "url":"https://upload.wikimedia.org/portrait.jpg",
            "descriptionurl":"https://commons.wikimedia.org/wiki/File:Portrait.jpg",
            "extmetadata":{k:{"value":v} for k,v in meta.items()}}]}}}}
    return call

class PortraitTests(unittest.TestCase):
    composer = {"id":"c1","name":"Composer"}

    def test_verified_license_and_attribution(self):
        record, reason = portrait(self.composer, mock_call())
        self.assertIsNone(reason)
        self.assertEqual(record["author"], "Author")
        self.assertEqual(record["license"], "CC-BY-4.0")
        self.assertEqual(record["wikidata_id"], "Q123")

    def test_ambiguous_identity(self):
        result, reason = find_person(self.composer, mock_call({"Q123":person(),"Q456":person()}))
        self.assertIsNone(result)
        self.assertEqual(reason,"ambiguous")

    def test_wrong_occupation(self):
        result, reason = find_person(self.composer, mock_call({"Q123":person(occupation="Q1")}))
        self.assertIsNone(result)
        self.assertEqual(reason,"identity_unconfirmed")

    def test_unverified_rights(self):
        for change in ({"LicenseShortName":"Public domain"},{"LicenseUrl":"https://example.org"},
                       {"Restrictions":"Some restriction"},{"Artist":"Unknown"}):
            record, reason = portrait(self.composer, mock_call(changes=change))
            self.assertIsNone(record)
            self.assertTrue(reason)

    def test_explicit_public_domain_mark(self):
        changes = {"LicenseShortName":"Public domain","LicenseUrl":PUBLIC_DOMAIN_URL,
                   "Copyrighted":"False"}
        record, reason = portrait(self.composer, mock_call(changes=changes))
        self.assertIsNone(reason)
        self.assertEqual(record["license"], "Public Domain")
        for change in ({"Copyrighted":"True"}, {"LicenseUrl":""}, {"Restrictions":"Restricted"}):
            record, reason = portrait(self.composer, mock_call(changes=dict(changes, **change)))
            self.assertIsNone(record)

    def test_transient_http_retry(self):
        failure = HTTPError(WD, 503, "temporary", {}, None)
        with patch("scripts.refresh_composer_portraits.urlopen", side_effect=[failure, failure, failure]) as call, patch("scripts.refresh_composer_portraits.time.sleep"):
            with self.assertRaises(WikimediaError):
                api(WD, action="wbsearchentities")
            self.assertEqual(call.call_count, 3)

    def test_wikidata_search_busy_retry(self):
        from io import BytesIO
        busy = json.dumps({"error":{"code":"cirrussearch-too-busy-error"}}).encode()
        success = json.dumps({"search":[]}).encode()
        with patch("scripts.refresh_composer_portraits.urlopen", side_effect=[BytesIO(busy), BytesIO(success)]) as call, patch("scripts.refresh_composer_portraits.time.sleep"):
            self.assertEqual(api(WD, action="wbsearchentities"), {"search":[]})
            self.assertEqual(call.call_count, 2)

    def test_partial_progress_survives_api_error(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "data"
            data.mkdir()
            composers = [dict(id="c1", name="Composer"), dict(id="c2", name="Other"),
                         dict(id="c3", name="Third")]
            (data / "composer-registry.json").write_text(json.dumps({"composers":composers}))
            path = data / "composer-portraits.json"
            path.write_text(json.dumps({"schema_version":1,"portraits":{}}))
            def call(endpoint, **params):
                if params.get("search") == "Other":
                    self.assertIn("c1", json.loads(path.read_text())["portraits"])
                    raise WikimediaError("temporary")
                if params.get("search") == "Third":
                    return {"search":[]}
                return mock_call()(endpoint, **params)
            refresh(root, call)
            report = json.loads((data / "composer-portrait-review.json").read_text())
            self.assertEqual(report["verified"], 1)
            self.assertEqual(report["total"], 3)
            self.assertEqual(report["unresolved"]["c2"]["reason"], "api_error")
            self.assertEqual(report["unresolved"]["c3"]["reason"], "not_found")
            self.assertIn("c1", json.loads(path.read_text())["portraits"])

if __name__ == "__main__":
    unittest.main()
