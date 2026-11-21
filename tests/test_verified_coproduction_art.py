"""Official first-party coproduction art is bound to exact work identity."""
import json
import unittest
from unittest.mock import patch

from opera_atlas.verified_coproduction_art import (
    REGISTRY, verified_coproduction_image, is_verified_coproduction_poster)
from scripts.auto_catalogue import verified_candidate_image
from scripts.collect_candidate_details import OUTPUT as DETAILS


class OfficialCoproductionArtworkTests(unittest.TestCase):
    def test_exact_bona_source_and_composer(self):
        url="https://www.fondazionepetruzzelli.it/eventi/bona-sforza-krautze-14-20-settembre/"
        proof=verified_coproduction_image(
            source_url=url,title="BONA SFORZA",composer="Zygmunt Krauze")
        self.assertEqual(proof["kind"],"official_coproduction_poster")
        self.assertEqual(proof["coproduction_page_url"],
                         "https://opera.krakow.pl/en/spectacles/bona-sforza-1")
        self.assertTrue(is_verified_coproduction_poster(
            proof,title="Bona Sforza",composer="Zygmunt Krauze"))
        self.assertIsNone(verified_coproduction_image(
            source_url=url,title="Bona Sforza",composer="Different Composer"))
        self.assertIsNone(verified_coproduction_image(
            source_url="https://other.example/event/bona-sforza",
            title="Bona Sforza",composer="Zygmunt Krauze"))
        self.assertFalse(is_verified_coproduction_poster(
            {**proof,"image_url":"https://example.com/wrong.jpg"},
            title="Bona Sforza",composer="Zygmunt Krauze"))

    def test_cached_official_candidate_uses_verified_coproduction_art(self):
        details=json.loads(DETAILS.read_text(encoding="utf-8"))["evidence"]
        cid="oa-index-207df538679e00657fe1"
        item=next(x for x in details if x["candidate_id"]==cid)
        proof=verified_candidate_image(item,title="Bona Sforza",
                    composer="Zygmunt Krauze",url=item["source_url"])
        self.assertEqual(proof["kind"],"official_coproduction_poster")
        self.assertTrue(proof["image_url"].endswith("bona-finalny_detail_poster.jpg"))

    def test_untrusted_registry_cannot_replace_official_poster(self):
        doc=json.loads(REGISTRY.read_text(encoding="utf-8"))
        doc["images"][0]["image_url"]="https://evil.example/forged.jpg"
        with patch.object(type(REGISTRY),"read_text",
                          return_value=json.dumps(doc)):
            image=verified_coproduction_image(
                source_url=doc["images"][0]["source_url"],
                title="Bona Sforza",composer="Zygmunt Krauze")
        self.assertIsNone(image)


if __name__=="__main__":
    unittest.main()
