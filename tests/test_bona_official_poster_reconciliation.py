"""Official portrait poster with source- and composer-bound validation."""
import json
import unittest
from unittest.mock import patch

from opera_atlas.verified_coproduction_posters import (
    REGISTRY,verified_coproduction_poster,is_verified_coproduction_poster)
from scripts.auto_catalogue import verified_candidate_image
from scripts.collect_candidate_details import OUTPUT as DETAILS

SOURCE="https://www.fondazionepetruzzelli.it/eventi/bona-sforza-krautze-14-20-settembre/"

class BonaOfficialPosterTests(unittest.TestCase):
    def test_official_page_proves_both_composer_and_original_poster(self):
        proof=verified_coproduction_poster(
            source_url=SOURCE,title="BONA SFORZA",composer="Zygmunt Krauze")
        self.assertEqual(proof["kind"],"official_coproduction_poster")
        self.assertEqual(proof["image_url"],
                         "https://opera.krakow.pl/media/spectacle_image/bona-finalny_detail_poster.jpg")
        self.assertTrue(is_verified_coproduction_poster(
            proof,title="BONA SFORZA",composer="Zygmunt Krauze"))
        self.assertIsNone(verified_coproduction_poster(
            source_url=SOURCE,title="BONA SFORZA",composer="Giuseppe Verdi"))
        self.assertIsNone(verified_coproduction_poster(
            source_url="https://other.example/bona",title="Bona Sforza",
            composer="Zygmunt Krauze"))

    def test_central_candidate_uses_coproduction_art(self):
        rows=json.loads(DETAILS.read_text(encoding="utf-8"))["evidence"]
        observation=next(x for x in rows if x.get("candidate_id")==
                         "oa-index-207df538679e00657fe1")
        proof=verified_candidate_image(observation,title="BONA SFORZA",
                 composer="Zygmunt Krauze",url=SOURCE)
        self.assertEqual(proof["kind"],"official_coproduction_poster")

    def test_rejects_unverified_image_substitution(self):
        original=json.loads(REGISTRY.read_text(encoding="utf-8"))
        forged=json.loads(json.dumps(original))
        forged["posters"][0]["image_url"]="https://opera.krakow.pl/media/spectacle_image/unrelated.jpg"
        with patch.object(type(REGISTRY),"read_text",return_value=json.dumps(forged)):
            self.assertIsNone(verified_coproduction_poster(
                source_url=SOURCE,title="BONA SFORZA",composer="Zygmunt Krauze"))

if __name__=="__main__":
    unittest.main()
