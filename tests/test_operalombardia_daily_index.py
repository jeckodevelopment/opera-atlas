"""One official OperaLombardia index refresh, not twenty duplicate page fetches."""
import json
import unittest
from datetime import date
from html import escape

from opera_atlas.controlled_fetch import FetchResult
from opera_atlas.operalombardia_calendar import parse_calendar
from scripts.build_verified_catalog import MANIFEST
from scripts.daily_ingest import CONFIG,scan_approved,validate_source_config
from scripts.publish_catalog_v2 import REGISTRY

SOURCE="https://www.operalombardia.it/calendario/"
TITLES={
 "Turandot":"TURANDOT",
 "Death in Venice":"DEATH IN VENICE",
 "Cavalleria rusticana":"CAVALLERIA RUSTICANA / PAGLIACCI",
 "Pagliacci":"CAVALLERIA RUSTICANA / PAGLIACCI",
 "L’italiana in Algeri":"L’ITALIANA IN ALGERI",
 "Un ballo in maschera":"UN BALLO IN MASCHERA",
}
MONTHS=["","GENNAIO","FEBBRAIO","MARZO","APRILE","MAGGIO","GIUGNO",
        "LUGLIO","AGOSTO","SETTEMBRE","OTTOBRE","NOVEMBRE","DICEMBRE"]


def fixture(facts):
    """Synthesize the exact known official row facts without copying HTML."""
    rows=set()
    for p in facts["productions"]:
        if p["key"].startswith("lombardia-"):
            if p["key"] == "lombardia-ballo-pavia":
                continue  # Partner venue page, absent from circuit index
            if p["title"] not in TITLES:
                continue
            for day,_ in p["dates"]:
                rows.add((day,TITLES[p["title"]],p["municipality"]+", "+p["venue"]))
    current=None
    parts=["<html><table>"]
    for day,title,venue in sorted(rows):
        yyyy,mm,dd=map(int,day.split("-"))
        if current != (yyyy,mm):
            current=(yyyy,mm)
            parts.append("<tr><td>"+MONTHS[mm]+" "+str(yyyy)+"</td><td></td><td></td></tr>")
        parts.append("<tr><td>"+str(dd)+"</td><td><a>"+escape(title)+"</a></td><td>"+escape(venue)+"</td></tr>")
    parts.append("</table></html>")
    return "".join(parts)


class IndexDailyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.scheduled=validate_source_config(json.loads(CONFIG.read_text(encoding="utf-8")))
        cls.index=next(x for x in cls.scheduled if x["adapter"]=="operalombardia_calendar")

    def test_multiple_opera_and_cities_from_one_calendar(self):
        html=fixture(self.facts)
        result=parse_calendar(html)
        # The Brescia combined ticket is not represented twice as solo works.
        self.assertGreaterEqual(len(result),48)
        self.assertTrue(all(hour is None for _,_,_,_,hour in result))
        self.assertIn(("Turandot","Teatro Coccia","Novara","2026-10-23",None),result)
        self.assertIn(("Death in Venice","Teatro Dante Alighieri","Ravenna","2027-02-14",None),result)
        self.assertIn(("Pagliacci","Teatro Sociale","Como","2026-12-04",None),result)

    def test_daily_index_reconciles_without_downgrading_known_pavia_hours(self):
        html=fixture(self.facts)
        def fetch(*args,**kwargs):
            return FetchResult(SOURCE,html,"d"*64,len(html))
        facts,registry,health,added=scan_approved(
            self.facts,self.registry,[self.index],network_enabled=True,
            fetcher=fetch,today=date(2026,11,20))
        self.assertEqual(added,0)
        self.assertEqual(registry,self.registry)
        self.assertEqual(facts,self.facts)
        # A dynamic shared catalog may contain additional, independently
        # sourced stagings absent from this one index. Reviewing such
        # unmatched titles must not change any canonical facts or hours.
        self.assertIn(health[0]["outcome"],("success","review_required"))
        if health[0]["outcome"]=="review_required":
            self.assertTrue(health[0]["anomalies"])
            self.assertEqual(health[0]["added"],0)

    def test_unknown_production_and_incomplete_index_fail_closed(self):
        html=fixture(self.facts)
        modified=html.replace("TURANDOT","NEW UNRECOGNIZED OPERA",1)
        with self.assertRaisesRegex(ValueError,"unrecognized production"):
            parse_calendar(modified)
        with self.assertRaises(ValueError):
            parse_calendar("<table><tr><td>OTTOBRE 2026</td></tr><tr><td>9</td><td>TURANDOT</td><td>Pavia, Teatro Fraschini</td></tr></table>")

    def test_unknown_opera_is_reviewed_not_published(self):
        html=fixture(self.facts)
        modified=html.replace("TURANDOT","NEW UNRECOGNIZED OPERA",1)
        rows=parse_calendar(modified,allow_unknown_for_review=True)
        self.assertTrue(any(r[0]=="NEW UNRECOGNIZED OPERA" for r in rows))
        def fetch(*args,**kwargs):
            return FetchResult(SOURCE,modified,"e"*64,len(modified))
        facts,registry,health,added=scan_approved(
            self.facts,self.registry,[self.index],network_enabled=True,
            fetcher=fetch,today=date(2026,11,20))
        self.assertEqual(added,0)
        self.assertEqual(facts,self.facts)
        self.assertEqual(registry,self.registry)
        self.assertEqual(health[0]["outcome"],"review_required")
        self.assertTrue(any(c["title"]=="NEW UNRECOGNIZED OPERA"
                            for c in health[0]["candidates"]))

    def test_review_mode_still_rejects_incomplete_and_cancelled_rows(self):
        html=fixture(self.facts)
        with self.assertRaises(ValueError):
            parse_calendar("<table><tr><td>OTTOBRE 2026</td></tr>"
                           "<tr><td>9</td><td>UNKNOWN OPERA</td>"
                           "<td>Pavia, Teatro Fraschini</td></tr></table>",
                           allow_unknown_for_review=True)
        altered=html.replace("TURANDOT","ANNULLATA TURANDOT",1)
        with self.assertRaises(ValueError):
            parse_calendar(altered,allow_unknown_for_review=True)

    def test_duplicate_and_prohibited_calendar_rows_fail(self):
        html=fixture(self.facts)
        piece="<tr><td>8</td><td><a>TURANDOT</a></td><td>Bergamo, Teatro Donizetti</td></tr>"
        self.assertIn(piece,html)
        bad=html.replace(piece,piece+piece)
        with self.assertRaises(ValueError):
            parse_calendar(bad)

    def test_robots_gate_is_not_bypassed(self):
        self.assertEqual(self.index["access_status"],"approved")
        self.assertIn("robots.txt",self.index["approval_evidence"])
        self.assertEqual(self.index["url"],SOURCE)

if __name__=="__main__":
    unittest.main()
