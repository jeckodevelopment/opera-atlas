"""Regression checks: completeness thresholds count eligible opera links only."""
import json
import unittest

from scripts.discover_season_indexes import CONFIG, extract, validate_config

class EligibleSeasonThresholdTests(unittest.TestCase):
    def test_eligible_counts_and_missing_card_fail_closed(self):
        sources={x["key"]:x for x in validate_config(
            json.loads(CONFIG.read_text(encoding="utf-8")))}
        cases=(
            ("modena-teatro-opera-2026-27",9,
             lambda n:f'<a href="/spettacolo/opera-{n}/">Opera {n}</a>',
             "", ""),
            ("piacenza-opera-2026-27",5,
             lambda n:f'<a href="/event/opera-{n}/">Opera {n}</a>',
             "<h2>Opera</h2>", "<h2>Concerti</h2>"),
            ("giglio-lucca-opera-2026-27",3,
             lambda n:f'<a href="/it/cartellone/lirica/stagione-2026-2027/opera-{n}">Opera {n}</a>',
             "", ""),
        )
        for key,count,anchor,prefix,suffix in cases:
            with self.subTest(source=key):
                source=sources[key]
                self.assertEqual(source["min_links"],count)
                html=prefix+"".join(anchor(i) for i in range(count))+suffix
                self.assertEqual(len(extract(key,source["url"],html,count)),count)
                missing=prefix+"".join(anchor(i) for i in range(count-1))+suffix
                with self.assertRaisesRegex(ValueError,"incomplete"):
                    extract(key,source["url"],missing,count)

if __name__=="__main__":
    unittest.main()
