import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.error import HTTPError
from scripts.refresh_composer_portraits import WD, COMMONS, portrait, find_person, refresh, WikimediaError, api, PUBLIC_DOMAIN_URL, WIKIPEDIA, ENTITY_DATA

def claim(value):
    return {"mainsnak":{"datavalue":{"value":value}}}

def person(name="Composer", occupation="Q36834"):
    return {"labels":{"en":{"value":name}}, "claims":{
        "P31":[claim({"id":"Q5"})], "P106":[claim({"id":occupation})],
        "P18":[claim("Portrait.jpg")]}}

def mock_call(entities=None, changes=None, categories=(), image_changes=None):
    entities = entities or {"Q123":person()}
    def call(endpoint, **params):
        if endpoint in WIKIPEDIA:
            return {"query":{"pages":{}}}
        if endpoint == WD:
            if params["action"] == "wbsearchentities":
                return {"search":[{"id":key} for key in entities]}
            return {"entities":entities}
        assert endpoint == COMMONS
        if params.get("list") == "search":
            return {"query":{"search":[]}}
        meta = {"LicenseShortName":"CC BY 4.0","LicenseUrl":"https://creativecommons.org/licenses/by/4.0/",
                "Artist":"<a>Author</a>","Copyrighted":"True"}
        meta.update(changes or {})
        image = {"mime":"image/jpeg", "url":"https://upload.wikimedia.org/portrait.jpg",
                 "descriptionurl":"https://commons.wikimedia.org/wiki/File:Portrait.jpg",
                 "extmetadata":{k:{"value":v} for k,v in meta.items()}}
        image.update(image_changes or {})
        return {"query":{"pages":{"1":{"imageinfo":[image], "categories":[{"title":x} for x in categories]}}}}
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

    def test_combined_public_domain_evidence_without_license_url(self):
        changes = {"LicenseShortName":"Public domain","LicenseUrl":"",
                   "Copyrighted":"False","License":"pd"}
        record, reason = portrait(self.composer, mock_call(changes=changes,
                                  categories=["Category:PD-old-100-expired"]))
        self.assertIsNone(reason)
        self.assertEqual(record["license"], "Public Domain")
        self.assertEqual(record["rights_evidence"], "commons_combined_public_domain_category")
        self.assertEqual(record["license_url"], record["source_url"])
        for categories in ([], ["Category:PD US expired"],
                           ["Category:PD-old-100-expired", "Category:Copyright violations"]):
            self.assertIsNone(portrait(self.composer, mock_call(changes=changes, categories=categories))[0])
        for change in ({"Copyrighted":"True"}, {"License":"unknown"}, {"Restrictions":"Restricted"},
                       {"LicenseUrl":"https://evil.example/"}):
            self.assertIsNone(portrait(self.composer, mock_call(changes=dict(changes, **change),
                                      categories=["Category:PD-old-100-expired"]))[0])

    def test_cc_deed_and_older_free_license(self):
        record, reason = portrait(self.composer, mock_call(changes={
            "LicenseShortName":"CC BY-SA 2.5",
            "LicenseUrl":"http://creativecommons.org/licenses/by-sa/2.5/deed.it"}))
        self.assertIsNone(reason)
        self.assertEqual(record["license"], "CC-BY-SA-2.5")
        self.assertEqual(record["license_url"], "https://creativecommons.org/licenses/by-sa/2.5/")
        for url in ("https://creativecommons.org.evil.example/licenses/by-sa/2.5/",
                    "https://creativecommons.org/licenses/by-nc/2.5/"):
            self.assertIsNone(portrait(self.composer, mock_call(changes={
                "LicenseShortName":"CC BY-SA 2.5","LicenseUrl":url}))[0])

    def test_commons_urls_and_raster_thumbnails(self):
        changes = {"mime":"image/tiff","url":"https://upload.wikimedia.org/original.tiff",
                   "thumburl":"https://upload.wikimedia.org/Foto d’autore.jpg?utm_source=commons",
                   "descriptionurl":"https://commons.wikimedia.org/wiki/File:Foto d’autore.tiff"}
        record, reason = portrait(self.composer, mock_call(image_changes=changes))
        self.assertIsNone(reason)
        self.assertIn("%20", record["url"])
        self.assertNotIn("utm_source", record["url"])
        self.assertIsNone(portrait(self.composer, mock_call(image_changes=dict(changes, thumburl=None)))[0])
        self.assertIsNone(portrait(self.composer, mock_call(image_changes=dict(changes, thumburl="https://evil.example/file.jpg")))[0])

    def test_official_thumbnail_host_and_original_fallback(self):
        thumb = "https://thumb.wikimedia.org/wikipedia/commons/thumb/a/ab/Portrait.jpg/960px-Portrait.jpg"
        record, reason = portrait(self.composer, mock_call(image_changes={"thumburl":thumb}))
        self.assertIsNone(reason)
        self.assertEqual(record["url"], thumb)
        for invalid in ("https://thumb.wikimedia.org.evil.example/image.jpg",
                        "https://thumb.wikimedia.org@evil.example/image.jpg"):
            record, reason = portrait(self.composer, mock_call(image_changes={"thumburl":invalid}))
            self.assertIsNone(reason)
            self.assertEqual(record["url"], "https://upload.wikimedia.org/portrait.jpg")

    def test_explicit_commons_pd_mark_and_other_expiry_categories(self):
        changes = {"LicenseShortName":"Public domain","LicenseUrl":"",
                   "Copyrighted":"False","License":"pd"}
        for category in ("Category:CC-PD-Mark", "Category:PD-old-80-expired",
                         "Category:PD-scan (PD-old-95-expired)"):
            record, reason = portrait(self.composer, mock_call(changes=changes, categories=[category]))
            self.assertIsNone(reason)
            self.assertEqual(record["license"], "Public Domain")
        for extra in ("Category:Template Unknown (source)", "Category:Template Unknown (author)"):
            self.assertIsNone(portrait(self.composer, mock_call(changes=changes,
                categories=["Category:CC-PD-Mark", extra]))[0])
        for author in ("Unknown author Unknown author", "Anonymous Unknown author", "Unattributed"):
            self.assertIsNone(portrait(self.composer, mock_call(changes=dict(changes, Artist=author),
                categories=["Category:CC-PD-Mark"]))[0])

    def test_german_ported_license(self):
        record, reason = portrait(self.composer, mock_call(changes={
            "LicenseShortName":"CC BY-SA 3.0 de",
            "LicenseUrl":"https://creativecommons.org/licenses/by-sa/3.0/de/deed.en"}))
        self.assertIsNone(reason)
        self.assertEqual(record["license"], "CC-BY-SA-3.0-DE")
        self.assertEqual(record["license_url"], "https://creativecommons.org/licenses/by-sa/3.0/de/")

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

    def test_exact_wikipedia_lookup_bypasses_search(self):
        def call(endpoint, **params):
            if endpoint in WIKIPEDIA:
                self.assertIn("Composer (composer)", params["titles"].split("|"))
                return {"query":{"pages":{"1":{"pageprops":{"wikibase_item":"Q123"}}}}}
            self.assertNotEqual(params.get("action"), "wbsearchentities")
            return mock_call()(endpoint, **params)
        record, reason = portrait(self.composer, call)
        self.assertIsNone(reason)
        self.assertEqual(record["wikidata_id"], "Q123")

    def test_entity_data_fallback_for_known_identifier(self):
        def call(endpoint, **params):
            if endpoint == WD:
                self.assertEqual(params["action"], "wbgetentities")
                raise WikimediaError("maxlag")
            if endpoint == ENTITY_DATA:
                self.assertEqual(params["qid"], "Q123")
                return {"entities":{"Q123":person()}}
            return mock_call()(endpoint, **params)
        record, reason = portrait(dict(self.composer, wikidata_id="Q123"), call)
        self.assertIsNone(reason)
        self.assertEqual(record["wikidata_id"], "Q123")

    def test_wikipedia_disambiguation_is_not_identity(self):
        def call(endpoint, **params):
            if endpoint in WIKIPEDIA:
                return {"query":{"pages":{"1":{"pageprops":{"wikibase_item":"Q123","disambiguation":""}}}}}
            if params.get("action") == "wbsearchentities":
                return {"search":[]}
            self.fail("Disambiguation item must not be read as a composer")
        self.assertEqual(find_person(self.composer, call), (None, "not_found"))

    def test_multiple_portraits_try_verified_alternative(self):
        entity = person()
        entity["claims"]["P18"].append(claim("Alternative.jpg"))
        def call(endpoint, **params):
            if endpoint == COMMONS and params["titles"] == "File:Portrait.jpg":
                return mock_call(changes={"LicenseShortName":"Unknown"})(endpoint, **params)
            return mock_call({"Q123":entity})(endpoint, **params)
        record, reason = portrait(self.composer, call)
        self.assertIsNone(reason)
        self.assertEqual(record["commons_file"], "Alternative.jpg")

    def test_structured_depicts_fallback(self):
        entity = person()
        entity["claims"].pop("P18")
        def call(endpoint, **params):
            if endpoint == COMMONS and params.get("list") == "search":
                self.assertEqual(params["srsearch"], "haswbstatement:P180=Q123")
                return {"query":{"search":[{"title":"File:Alternative.jpg","pageid":42},
                                           {"title":"File:Wrong.jpg","pageid":43},
                                           {"title":"File:Group.jpg","pageid":44}]}}
            if endpoint == COMMONS and params.get("action") == "wbgetentities":
                return {"entities":{
                    "M42":{"statements":{"P180":[claim({"id":"Q123"})]}},
                    "M43":{"statements":{"P180":[claim({"id":"Q999"})]}},
                    "M44":{"statements":{"P180":[claim({"id":"Q123"}),claim({"id":"Q999"})]}}}}
            if endpoint == COMMONS:
                self.assertEqual(params["titles"], "File:Alternative.jpg")
            return mock_call({"Q123":entity})(endpoint, **params)
        record, reason = portrait(self.composer, call)
        self.assertIsNone(reason)
        self.assertEqual(record["identity_evidence"], "commons_depicts_p180")

    def test_candidate_error_does_not_prevent_alternative(self):
        entity = person()
        entity["claims"]["P18"].append(claim("Alternative.jpg"))
        def call(endpoint, **params):
            if endpoint == COMMONS and params.get("titles") == "File:Portrait.jpg":
                raise WikimediaError("maxlag")
            return mock_call({"Q123":entity})(endpoint, **params)
        record, reason = portrait(self.composer, call)
        self.assertIsNone(reason)
        self.assertEqual(record["commons_file"], "Alternative.jpg")

    def test_linked_category_requires_exact_depiction(self):
        entity = person()
        entity["claims"].pop("P18")
        entity["claims"]["P373"] = [claim("Composer")]
        def call(endpoint, **params):
            if endpoint == COMMONS and params.get("list") == "categorymembers":
                self.assertEqual(params["cmtitle"], "Category:Composer")
                return {"query":{"categorymembers":[{"title":"File:Wrong.jpg","pageid":41},
                                                     {"title":"File:Correct.jpg","pageid":42}]}}
            if endpoint == COMMONS and params.get("action") == "wbgetentities":
                return {"entities":{"M41":{"statements":{"P180":[claim({"id":"Q999"})]}},
                                    "M42":{"statements":{"P180":[claim({"id":"Q123"})]}}}}
            if endpoint == COMMONS and params.get("titles"):
                self.assertEqual(params["titles"], "File:Correct.jpg")
            return mock_call({"Q123":entity})(endpoint, **params)
        record, reason = portrait(self.composer, call)
        self.assertIsNone(reason)
        self.assertEqual(record["identity_evidence"], "commons_category_verified_depicts")

    def test_multilingual_identity_alias(self):
        entity = person("Different spelling")
        entity["aliases"] = {"de":[{"value":"Composer"}]}
        match, reason = find_person(self.composer, mock_call({"Q123":entity}))
        self.assertIsNone(reason)
        self.assertEqual(match[0], "Q123")

    def test_cached_identity_survives_rights_review(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "data"
            data.mkdir()
            (data / "composer-registry.json").write_text(json.dumps({"composers":[self.composer]}))
            (data / "composer-portraits.json").write_text(json.dumps({"schema_version":1,"portraits":{}}))
            refresh(root, mock_call(changes={"LicenseShortName":"Unknown"}))
            report = json.loads((data / "composer-portrait-review.json").read_text())
            self.assertEqual(report["identities"]["c1"]["wikidata_id"], "Q123")
            self.assertEqual(report["status"], "completed")
            def call(endpoint, **params):
                self.assertNotIn(endpoint, WIKIPEDIA)
                self.assertNotEqual(params.get("action"), "wbsearchentities")
                return mock_call()(endpoint, **params)
            refresh(root, call)
            self.assertEqual(json.loads((data / "composer-portrait-review.json").read_text())["verified"], 1)

    def test_blocked_run_and_next_batch(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "data"
            data.mkdir()
            composers = [dict(id=f"c{i}", name=f"Composer {i}") for i in range(5)]
            (data / "composer-registry.json").write_text(json.dumps({"composers":composers}))
            (data / "composer-portraits.json").write_text(json.dumps({"schema_version":1,"portraits":{}}))
            def unavailable(endpoint, **params):
                raise WikimediaError("maxlag")
            refresh(root, unavailable)
            report = json.loads((data / "composer-portrait-review.json").read_text())
            self.assertEqual(report["status"], "blocked")
            self.assertEqual(report["api_errors"], 3)
            self.assertEqual(report["unresolved"]["c3"]["reason"], "not_attempted")
            refresh(root, unavailable)
            report = json.loads((data / "composer-portrait-review.json").read_text())
            self.assertEqual(report["unresolved"]["c3"]["reason"], "api_error")
            self.assertEqual(report["unresolved"]["c4"]["reason"], "api_error")

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
            self.assertEqual(report["status"], "partial")
            self.assertEqual(report["total"], 3)
            self.assertEqual(report["unresolved"]["c2"]["reason"], "api_error")
            self.assertEqual(report["unresolved"]["c3"]["reason"], "not_found")
            self.assertIn("c1", json.loads(path.read_text())["portraits"])

if __name__ == "__main__":
    unittest.main()
