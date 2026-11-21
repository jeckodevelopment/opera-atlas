"""Official-source-bound work identity cards for the Petruzzelli backlog."""
import json
import unittest
from scripts.auto_catalogue import official_identity_candidates
from scripts.collect_candidate_details import OUTPUT as DETAILS
from scripts.discover_season_indexes import OUTPUT as CANDIDATES
from scripts.auto_work_research import OUT as RESEARCH
from scripts.publish_work_posters import load_archival_art

CASES={
    "oa-index-207df538679e00657fe1":("Bona Sforza","Zygmunt Krauze",2024),
    "oa-index-663c5bda82d136bbbdcc":("Il gobbo del Califfo","Franco Casavola",1929),
    "oa-index-fcae59bb4ff1c5166bcc":("La Cecchina","Niccolò Piccinni",1760),
}

class PetruzzelliVerifiedCardsTests(unittest.TestCase):
    def test_identity_exact_official_source_and_composer(self):
        evidence=json.loads(DETAILS.read_text(encoding="utf-8"))
        candidates=json.loads(CANDIDATES.read_text(encoding="utf-8"))
        intelligence=json.loads(RESEARCH.read_text(encoding="utf-8"))
        cards=official_identity_candidates(evidence,candidates,intelligence)
        by_id={row["candidate_id"]:row for row in cards["works"]}
        by_candidate={row["id"]:row for row in candidates["candidates"]}
        for cid,(title,composer,year) in CASES.items():
            with self.subTest(candidate=cid):
                if by_candidate[cid]["status"]=="already_catalogued":
                    continue
                row=by_id[cid]
                self.assertEqual(row["title"].casefold(),title.casefold())
                self.assertEqual(row["composer"].casefold(),composer.casefold())
                self.assertEqual(row["official_authority_url"],by_candidate[cid]["official_url"])
                self.assertTrue(45<=len(row["synopsis"])<=300)
                self.assertEqual(row["history"]["premiere_year"],year)

    def test_two_original_opera_archival_images(self):
        images=load_archival_art({"la-cecchina","il-gobbo-del-califfo"})
        self.assertEqual(set(images),{"la-cecchina","il-gobbo-del-califfo"})
        for row in images.values():
            self.assertEqual(row["kind"],"archival_work_image")

if __name__=="__main__":
    unittest.main()
