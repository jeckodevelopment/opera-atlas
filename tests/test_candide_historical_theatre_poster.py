"""Verified original 1956 Candide venue flyer, separate from the 2027 staging."""
import json
import unittest
from unittest.mock import patch
from opera_atlas.verified_historical_theatre_posters import (
    REGISTRY,SOURCE,PROVENANCE,IMAGE,verified_theatre_poster,is_verified_theatre_poster)
from scripts.auto_catalogue import verified_candidate_image

class CandideHistoricalTheatrePosterTests(unittest.TestCase):
    def test_exact_archival_poster_from_original_producing_theatre(self):
        proof=verified_theatre_poster(
            source_url=SOURCE,title="Candide",composer="Leonard Bernstein")
        self.assertIsNotNone(proof)
        self.assertEqual(proof["image_url"],IMAGE)
        self.assertEqual(proof["provenance_url"],PROVENANCE)
        self.assertEqual(proof["kind"],"verified_historical_theatre_poster")
        self.assertTrue(is_verified_theatre_poster(
            proof,title="Candide",composer="Leonard Bernstein"))
        self.assertEqual(verified_candidate_image(
            {},title="Candide",composer="Leonard Bernstein",url=SOURCE),proof)

    def test_other_compositions_and_venues_cannot_reuse_flyer(self):
        self.assertIsNone(verified_theatre_poster(
            source_url=SOURCE,title="Candide",composer="Different Composer"))
        self.assertIsNone(verified_theatre_poster(
            source_url=SOURCE,title="L'anno che verrà",composer="Leonard Bernstein"))
        self.assertIsNone(verified_theatre_poster(
            source_url="https://example.org/evento/candide/",
            title="Candide",composer="Leonard Bernstein"))

    def test_tampered_poster_fails_independent_validation(self):
        doc=json.loads(REGISTRY.read_text(encoding="utf-8"))
        doc["images"][0]["image_url"]="https://res.cloudinary.com/dwzhqvxaz/image/upload/other.jpg"
        with patch.object(type(REGISTRY),"read_text",return_value=json.dumps(doc)):
            self.assertIsNone(verified_theatre_poster(
                source_url=SOURCE,title="Candide",composer="Leonard Bernstein"))
        valid=verified_theatre_poster(
            source_url=SOURCE,title="Candide",composer="Leonard Bernstein")
        self.assertFalse(is_verified_theatre_poster(
            {**valid,"source_url":"https://example.org/evento/candide/"},
            title="Candide",composer="Leonard Bernstein"))

if __name__=="__main__":
    unittest.main()
