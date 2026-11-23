"""Strict first-party artwork identity: opaque filenames must not block valid operas."""
import unittest
from scripts.publish_work_posters import extract_official_poster
from scripts.auto_catalogue import verified_candidate_image

URL="https://theatre.example/opera/ghost-cafe/"
IMAGE="https://theatre.example/wp-content/uploads/2026/11/image_9241.jpg"

class OpaqueArtworkTests(unittest.TestCase):
    def evidence(self, title="Ghost Cafè", alt="Locandina di Ghost Cafè di Carlo Galante"):
        html=(f'<meta property="og:image" content="{IMAGE}">'
              f'<meta property="og:image:alt" content="{alt}">')
        return extract_official_poster(html,URL,title,verified_event_page=True)

    def test_same_first_party_page_and_original_title_alt(self):
        evidence=self.evidence()
        self.assertIsNotNone(evidence)
        self.assertEqual(evidence["source_image_alt"],
                         "Locandina di Ghost Cafè di Carlo Galante")
        result=verified_candidate_image(
            {"source_key":"trapani-luglio-musicale-2026",
             "source_url":URL,"poster_evidence":evidence},
            title="Ghost Cafè",composer="Carlo Galante",url=URL)
        self.assertEqual(result["image_url"],IMAGE)

    def test_unrelated_image_is_never_accepted(self):
        self.assertIsNone(self.evidence(alt="Logo della stagione teatrale"))
        self.assertIsNone(self.evidence(alt="Locandina di Tosca di Puccini"))
        good=self.evidence()
        for altered in (
            {**good,"source_image_alt":"Locandina di Tosca"},
            {**good,"source_image_alt":""},
            {**good,"source_url":"https://other.example/spettacolo"},
            {**good,"image_url":"https://untrusted.example/asset.jpg"},
        ):
            with self.subTest(altered=altered):
                self.assertIsNone(verified_candidate_image(
                    {"source_key":"trapani-luglio-musicale-2026",
                     "source_url":URL,"poster_evidence":altered},
                    title="Ghost Cafè",composer="Carlo Galante",url=URL))

    def test_season_page_never_uses_title_alt_exception(self):
        html=(f'<meta property="og:image" content="{IMAGE}">'
              f'<meta property="og:image:alt" content="Ghost Cafè">')
        self.assertIsNone(extract_official_poster(html,URL,"Ghost Cafè"))

if __name__=="__main__":
    unittest.main()
