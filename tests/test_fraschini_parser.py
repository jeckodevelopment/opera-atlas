"""Partner Fraschini production parser: only exact, verified paired recite."""
import json
import unittest
from opera_atlas.fraschini_parser import parse_fraschini_detail
from scripts.daily_ingest import _parse, validate_source_config, CONFIG
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY, assemble
URL="https://www.teatrofraschini.it/programma/turandot/"
def page(title="Turandot",composer="Giacomo Puccini",schedule="Venerdì 9 OTTOBRE 2026, ore 20 | Domenica 11 OTTOBRE, ore 15.30"):
    return "<html><h1>"+title+"</h1><p>"+schedule+"</p><p>Opera di "+composer+"</p></html>"
class FraschiniTests(unittest.TestCase):
    def test_explicit_year_on_first_date_and_local_time_second(self):
        self.assertEqual(parse_fraschini_detail(page(),url=URL,title="Turandot",composer="Giacomo Puccini"),
                         [("2026-10-09","20:00"),("2026-10-11","15:30")])
    def test_two_works_same_bill(self):
        url="https://www.teatrofraschini.it/programma/cavalleria-rusticana-pagliacci/"
        html=page(title="Cavalleria rusticana / Pagliacci",composer="Pietro Mascagni e Ruggero Leoncavallo",
                  schedule="Venerdì 30 OTTOBRE 2026, ore 20 | Sabato 31 OTTOBRE, ore 20")
        for title,composer in (("Cavalleria rusticana","Pietro Mascagni"),("Pagliacci","Ruggero Leoncavallo")):
            self.assertEqual(parse_fraschini_detail(html,url=url,title=title,composer=composer),
                             [("2026-10-30","20:00"),("2026-10-31","20:00")])
    def test_missing_date_composer_heading_or_foreign_host_fails(self):
        for html,url in ((page(schedule="ottobre 2026, ore 20"),URL),
                         (page(composer="unknown"),URL),(page(title="Another"),URL),
                         (page(),"https://invalid.example/programma/turandot/")):
            with self.assertRaises(ValueError):
                parse_fraschini_detail(html,url=url,title="Turandot",composer="Giacomo Puccini")
    def test_canonical_ids_and_no_artificial_hour(self):
        facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        ids=json.loads(REGISTRY.read_text(encoding="utf-8"))
        graph=assemble(facts,ids)
        self.assertEqual(len(graph["works"]),19)
        self.assertEqual(len(graph["stagings"]),24)
        self.assertEqual(len(graph["performances"]),131)
        self.assertEqual(sum(not x["time_known"] for x in graph["performances"]),2)
        self.assertEqual(len({x["id"] for x in graph["performances"]}),131)
        self.assertEqual(sum("oa-r-000082" <= x["id"] <= "oa-r-000091" for x in graph["performances"]),10)
    def test_daily_source_is_approved_only_under_robots_gate(self):
        cfg=validate_source_config(json.loads(CONFIG.read_text(encoding="utf-8")))
        sources=[x for x in cfg if x["adapter"]=="fraschini"]
        self.assertEqual(len(sources),5)
        self.assertTrue(all(x["access_status"]=="approved" for x in sources))
        item=next(x for x in sources if x["key"]=="lombardia-turandot-pavia")
        self.assertEqual(_parse(item,page()),[
            ("Teatro Fraschini","Pavia","2026-10-09","20:00"),
            ("Teatro Fraschini","Pavia","2026-10-11","15:30")])
if __name__=="__main__":
    unittest.main()
