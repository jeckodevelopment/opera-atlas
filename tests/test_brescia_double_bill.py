"""The combined Brescia ticket schedule belongs to two distinct canonical operas."""
import copy
import json
import unittest
from datetime import date

from opera_atlas.brescia_detail_parser import parse_brescia_double_bill
from scripts.collect_candidate_details import parse_known_opera_detail
from scripts.auto_catalogue import enrich_double_bill_times,promote
from scripts.build_verified_catalog import MANIFEST,TIME_EVIDENCE,validate_time_evidence,build
from scripts.publish_catalog_v2 import REGISTRY

URL="https://teatrogrande.it/it/stagioni/2026/cavalleria-rusticana-pagliacci"
CANDIDATE="oa-index-double-fixture"

def fixture():
    return (
      "<p>opera / Cavalleria Rusticana/Pagliacci</p>"
      "<div>Turno A</div><div>venerdì 11 dicembre 2026</div>"
      "<div>20:00, Sala Grande</div>"
      "<div>Turno B</div><div>domenica 13 dicembre 2026</div>"
      "<div>15:30, Sala Grande</div>"
      "<p>Acquista online</p>"
      "<h1>Cavalleria Rusticana/Pagliacci di Pietro Mascagni/Ruggero Leoncavallo</h1>"
      "<p>A concludere il cartellone, il dittico verista</p>"
      "<h2>Credits</h2><p>Cavalleria Rusticana</p><p>Melodramma in un atto</p>"
      "<p>Musica di Pietro Mascagni</p>"
      "<p>Pagliacci</p><p>Dramma in un prologo e due atti</p>"
      "<p>Parole e musica di Ruggero Leoncavallo</p>"
      "<p>Accessibilità TURNO B - domenica 13 dicembre ore 15.30</p>"
    )

class DoubleBillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.prior=json.loads(TIME_EVIDENCE.read_text(encoding="utf-8"))

    def evidence(self,html=None):
        rows=parse_known_opera_detail("teatro-grande-opera-2026",URL,
                                      html if html is not None else fixture(),
                                      self.registry)
        candidates={"candidates":[{"id":CANDIDATE,"source_key":"teatro-grande-opera-2026",
                                    "official_url":URL,"status":"needs_review"}]}
        evidence={"evidence":[{"candidate_id":CANDIDATE,"source_key":"teatro-grande-opera-2026",
                               "source_url":URL,"status":"needs_editorial_review",
                               "event_facts":rows}]}
        return rows,evidence,candidates

    def test_two_canonical_composers_and_two_shared_ticket_slots(self):
        raw=parse_brescia_double_bill(fixture(),url=URL,works=self.registry["works"])
        self.assertEqual(len(raw),4)
        self.assertEqual({(x["event_title"],x["composer"]) for x in raw},{
            ("Cavalleria rusticana","Pietro Mascagni"),
            ("Pagliacci","Ruggero Leoncavallo")})
        rows,_,_=self.evidence()
        self.assertEqual(len(rows),4)
        self.assertEqual({x["date"] for x in rows},{"2026-12-11","2026-12-13"})
        self.assertEqual({x["venue"] for x in rows},{"Teatro Grande"})
        self.assertEqual({x["starts_at"][-6:] for x in rows},{"+01:00"})
        for title in ("Cavalleria rusticana","Pagliacci"):
            clocks=[x["starts_at"][11:16] for x in rows if x["event_title"]==title]
            self.assertEqual(clocks,["20:00","15:30"])

    def test_both_existing_stagings_enriched_without_new_id(self):
        rows,evidence,candidates=self.evidence()
        enriched,count=enrich_double_bill_times(self.facts,evidence,candidates,self.prior)
        expected=sum(1 for work in ("cavalleria","pagliacci")
                     for day in ("2026-12-11","2026-12-13")
                     if f"lombardia-{work}-brescia|{day}" not in self.prior["times"])
        self.assertEqual(count,expected)
        self.assertEqual(len(enriched["times"]),len(self.prior["times"])+expected)
        for work in ("cavalleria","pagliacci"):
            self.assertEqual(enriched["times"][f"lombardia-{work}-brescia|2026-12-11"],
                             {"time":"20:00","url":URL})
            self.assertEqual(enriched["times"][f"lombardia-{work}-brescia|2026-12-13"],
                             {"time":"15:30","url":URL})
        validate_time_evidence(self.facts,enriched)
        republished=build(self.facts,enriched)
        self.assertTrue(republished)
        same,delta=enrich_double_bill_times(self.facts,evidence,candidates,enriched)
        self.assertEqual(delta,0)
        self.assertEqual(same,enriched)
        facts,ids,_,report=promote(self.facts,self.registry,evidence,candidates,[],
                                   today=date(2026,11,21))
        self.assertEqual(report["new_recite"],0)
        self.assertEqual(facts,self.facts)
        self.assertEqual(ids,self.registry)

    def test_missing_composer_credit_or_mismatched_heading_fails_closed(self):
        invalid=[
            fixture().replace("Parole e musica di Ruggero Leoncavallo",
                              "Parole e musica di un altro autore"),
            fixture().replace("Musica di Pietro Mascagni","Musica di altro autore"),
            fixture().replace("Cavalleria Rusticana/Pagliacci di Pietro Mascagni/Ruggero Leoncavallo",
                              "Cavalleria Rusticana/Pagliacci di Autore Errato"),
            fixture().replace("15:30, Sala Grande","Orario da definire"),
            fixture().replace("Turno A","Turno A annullata"),
        ]
        for page in invalid:
            with self.subTest(page=page):
                with self.assertRaises(ValueError):
                    parse_brescia_double_bill(page,url=URL,works=self.registry["works"])
        with self.assertRaises(ValueError):
            parse_brescia_double_bill(fixture(),url="https://evil.example/it/stagioni/2026/cavalleria-rusticana-pagliacci",
                                      works=self.registry["works"])

    def test_incomplete_or_disagreeing_two_work_evidence_is_atomic(self):
        rows,evidence,candidates=self.evidence()
        for mutation in ("missing_work","conflicting_date","unknown_composer","extra_row"):
            changed=copy.deepcopy(evidence)
            arr=changed["evidence"][0]["event_facts"]
            if mutation=="missing_work":
                arr[:]=[r for r in arr if r["event_title"]=="Pagliacci"]
            elif mutation=="conflicting_date":
                arr[0]["starts_at"]="2026-12-11T21:00:00+01:00"
            elif mutation=="unknown_composer":
                arr[0]["composer"]="Another composer"
            else:
                arr.append(copy.deepcopy(arr[0]))
            out,count=enrich_double_bill_times(self.facts,changed,candidates,self.prior)
            self.assertEqual(count,0,mutation)
            self.assertEqual(out,self.prior,mutation)

if __name__=="__main__":
    unittest.main()
