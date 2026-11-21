"""A fully verified candidate must not wait for unrelated national scans."""
from pathlib import Path
import unittest

class FastCandidatePublication(unittest.TestCase):
    def test_cache_and_authority_promotion_precede_network(self):
        workflow=(Path(__file__).resolve().parents[1]/
                  ".github/workflows/refresh-catalog.yml").read_text()
        early=workflow.index("      - name: Early publish previously verified known-opera recite")
        crawl=workflow.index("      - name: Incrementally scan only explicitly approved official pages")
        section=workflow[early:crawl]
        self.assertIn("python -m scripts.publish_cached_known",section)
        self.assertIn("python -m scripts.auto_catalogue",section)
        self.assertIn("python -m scripts.publish_work_posters",section)
        self.assertLess(section.index("python -m scripts.auto_catalogue"),
                        section.index("python -m scripts.build_verified_catalog"))
        self.assertIn("data/work-poster-evidence.json",section)
        self.assertIn("public/catalog/work-posters.json",section)
        self.assertIn("data/autonomous-catalogue-health.json",section)
        # Later refresh still reconfirms source evidence and publishes any
        # fresh results through the very same centralized promotion.
        self.assertIn("python -m scripts.collect_candidate_details --allow-network",
                      workflow[crawl:])
        self.assertIn("python -m scripts.auto_catalogue",workflow[crawl:])

if __name__=="__main__":
    unittest.main()
