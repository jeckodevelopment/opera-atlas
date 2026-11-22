"""Catania: official original artwork for precisely the same work."""
import json
import unittest
from unittest.mock import patch
from opera_atlas.verified_original_work_art import (
    REGISTRY,verified_original_art,is_verified_original_art)
from scripts.auto_catalogue import verified_candidate_image
from scripts.collect_candidate_details import OUTPUT as DETAILS

URL="https://www.teatromassimobellini.it/eventi/il-quinto-moschettiere-2/"
class SourceBoundOriginalArtTests(unittest.TestCase):
    def test_identical_work_is_credited_to_original_premiere_art(self):
        proof=verified_original_art(source_url=URL,
            title="Il quinto moschettiere",composer="Matteo Musumeci")
        self.assertEqual(proof["kind"],"official_original_work_artwork")
        self.assertEqual(proof["original_source_url"],
                         "https://www.teatromassimobellini.it/eventi/il-quinto-moschettiere/")
        self.assertTrue(proof["image_url"].endswith("/il-quinto-moschettiere.png"))
        self.assertTrue(is_verified_original_art(
            proof,title="Il quinto moschettiere",composer="Matteo Musumeci"))
        self.assertIsNone(verified_original_art(source_url=URL,
            title="Il quinto moschettiere",composer="Giuseppe Verdi"))

    def test_exact_current_official_candidate_is_eligible(self):
        doc=json.loads(DETAILS.read_text(encoding="utf-8"))
        row=next(x for x in doc["evidence"]
                 if x.get("candidate_id")=="oa-index-8bc8b40e1da92efab27d")
        image=verified_candidate_image(row,title="Il quinto moschettiere",
                    composer="Matteo Musumeci",url=URL)
        self.assertEqual(image["kind"],"official_original_work_artwork")

    def test_never_substitute_another_opera_or_tampered_image(self):
        self.assertIsNone(verified_original_art(
            source_url="https://www.teatromassimobellini.it/eventi/le-nozze-dellorso/",
            title="Le nozze dell’orso",composer="Joe Schittino"))
        doc=json.loads(REGISTRY.read_text(encoding="utf-8"))
        doc["art"][0]["image_url"]="https://www.teatromassimobellini.it/media/unrelated.jpg"
        with patch.object(type(REGISTRY),"read_text",return_value=json.dumps(doc)):
            self.assertIsNone(verified_original_art(source_url=URL,
                title="Il quinto moschettiere",composer="Matteo Musumeci"))

if __name__=="__main__":
    unittest.main()
