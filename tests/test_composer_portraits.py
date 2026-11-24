import unittest
from scripts.refresh_composer_portraits import WD, COMMONS, portrait, find_person

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

if __name__ == "__main__":
    unittest.main()
