"""Source-bound authority and poster for a 2027 premiere, without invented shows."""
import json
import unittest
from pathlib import Path

from scripts.auto_catalogue import official_identity_candidates, verified_candidate_image

URL = "https://www.fondazioneteatrococcia.it/stagione-27-dove-nasce-il-melograno.html"
IMAGE = "https://www.fondazioneteatrococcia.it/images/spettacoli/stagione-27/1920x950_DOVE_NASCE_IL_MELOGRANO.png"
COMPOSER = "Arturo Dal Bianco, Giuseppe Guerrera, Massimiliano Piscitello"


class NovaraMelogranoAuthorityTests(unittest.TestCase):
    def test_official_authority_uses_three_composers_and_world_premiere(self):
        seed = next(row for row in json.loads(Path(
            "data/verified-work-authority-seeds.json").read_text())["works"]
                    if row["source_url"] == URL)
        self.assertEqual(seed["title"], "Dove nasce il melograno")
        self.assertEqual(seed["composer"], COMPOSER)
        self.assertEqual(seed["history"]["premiere_year"], 2027)
        self.assertEqual(seed["history"]["librettist"], "Pietro Utili")
        candidate_id = "oa-index-1bf92e353f6745bc2b3a"
        candidates = {"schema_version": 1, "candidates": [{
            "id": candidate_id, "source_key": "coccia-novara-rolling-opera",
            "official_url": URL, "status": "needs_review"}]}
        evidence = {"schema_version": 1, "evidence": [{
            "candidate_id": candidate_id, "source_key": "coccia-novara-rolling-opera",
            "source_url": URL, "status": "needs_editorial_review",
            "event_facts": [{
                "event_title": "DOVE NASCE IL MELOGRANO",
                "composer": "ARTURO DAL BIANCO, GIUSEPPE GUERRERA, MASSIMILIANO PISCITELLO",
                "venue": "Teatro Coccia", "date": "2027-04-30",
                "starts_at": "2027-04-30T20:00:00+02:00"}],
            "poster_evidence": {
                "image_url": IMAGE, "source_url": URL,
                "credit": "Immagine della produzione dal sito ufficiale del teatro",
                "alt": "Immagine della produzione di DOVE NASCE IL MELOGRANO",
                "kind": "official_production_image"
            }
        }]}
        work = official_identity_candidates(evidence, candidates,
                                            {"schema_version": 1, "works": []})["works"]
        self.assertEqual(len(work), 1)
        self.assertEqual(work[0]["title"], "Dove nasce il melograno")
        self.assertEqual(work[0]["composer"], COMPOSER)
        self.assertEqual(work[0]["history"]["premiere_venue"], "Teatro Coccia")
        self.assertEqual(verified_candidate_image(
            evidence["evidence"][0], title=work[0]["title"],
            composer=work[0]["composer"], url=URL)["image_url"], IMAGE)


if __name__ == "__main__":
    unittest.main()
