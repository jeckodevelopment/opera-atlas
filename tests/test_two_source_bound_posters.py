"""Original first-party posters: Bellini 2026 and Veleno co-production."""
import json
import unittest
from unittest.mock import patch

from opera_atlas.verified_original_work_art import (
    REGISTRY as BELLINI, verified_original_art, is_verified_original_art)
from opera_atlas.verified_coproduction_posters import (
    REGISTRY as COPRODUCED, verified_coproduction_poster,
    is_verified_coproduction_poster)
from scripts.auto_catalogue import verified_candidate_image
from scripts.collect_candidate_details import OUTPUT as DETAILS

CATANIA="https://www.teatromassimobellini.it/eventi/le-nozze-dellorso/"
REGGIO="https://www.iteatri.re.it/spettacolo/veleno/"

class OriginalOperaArtworkBatchTests(unittest.TestCase):
    def test_bellini_nozze_real_first_party_poster(self):
        actual=verified_original_art(
            source_url=CATANIA,title="LE NOZZE DELL’ORSO",composer="Joe Schittino")
        self.assertEqual(actual["kind"],"official_original_work_artwork")
        self.assertEqual(actual["image_url"],
          "https://www.teatromassimobellini.it/media/2026/11/PHOTO-2026-Orso.jpg")
        self.assertTrue(is_verified_original_art(
            actual,title="Le nozze dell’orso",composer="Joe Schittino"))
        self.assertIsNone(verified_original_art(
            source_url=CATANIA,title="Le nozze dell’orso",composer="Gaetano Donizetti"))

    def test_reggio_veleno_requires_exact_coproducer_art(self):
        actual=verified_coproduction_poster(
            source_url=REGGIO,title="Veleno",composer="Gaia Aloisi")
        self.assertEqual(actual["kind"],"official_coproduction_poster")
        self.assertEqual(actual["provenance_url"],
                         "https://teatroregioparma.it/spettacolo/veleno/")
        self.assertTrue(actual["image_url"].endswith("1080x1080-VELENO.png"))
        self.assertTrue(is_verified_coproduction_poster(
            actual,title="Veleno",composer="Gaia Aloisi"))
        self.assertIsNone(verified_coproduction_poster(
            source_url=REGGIO,title="Veleno",composer="Franco Casavola"))

    def test_existing_bona_coproduction_remains_verified(self):
        source="https://www.fondazionepetruzzelli.it/eventi/bona-sforza-krautze-14-20-settembre/"
        actual=verified_coproduction_poster(
            source_url=source,title="Bona Sforza",composer="Zygmunt Krauze")
        self.assertIsNotNone(actual)
        self.assertTrue(is_verified_coproduction_poster(
            actual,title="Bona Sforza",composer="Zygmunt Krauze"))

    def test_real_candidate_gate_uses_both_posters(self):
        evidence=json.loads(DETAILS.read_text(encoding="utf-8"))["evidence"]
        for cid,url,title,composer,kind in [
          ("oa-index-d54e9b021b5167cfb735",CATANIA,
           "Le nozze dell’orso","Joe Schittino","official_original_work_artwork"),
          ("oa-index-a98083086627ce6e0225",REGGIO,
           "Veleno","Gaia Aloisi","official_coproduction_poster")]:
            with self.subTest(candidate=cid):
                row=next(x for x in evidence if x["candidate_id"]==cid)
                self.assertEqual(verified_candidate_image(
                    row,title=title,composer=composer,url=url)["kind"],kind)

    def test_tampered_image_is_not_reused(self):
        for registry,key,fn,source,title,composer in [
          (BELLINI,"art",verified_original_art,CATANIA,"Le nozze dell’orso","Joe Schittino"),
          (COPRODUCED,"posters",verified_coproduction_poster,REGGIO,"Veleno","Gaia Aloisi")]:
            with self.subTest(registry=str(registry)):
                doc=json.loads(registry.read_text(encoding="utf-8"))
                row=next(x for x in doc[key] if x["source_url"]==source)
                row["image_url"]="https://unrelated.example/other-production.jpg"
                with patch.object(type(registry),"read_text",return_value=json.dumps(doc)):
                    self.assertIsNone(fn(source_url=source,title=title,composer=composer))

if __name__=="__main__":
    unittest.main()
