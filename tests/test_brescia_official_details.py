"""Official Brescia tickets and composer-specific opera identity."""
import json
import unittest
from datetime import date
from opera_atlas.brescia_detail_parser import parse_brescia_detail
from scripts.collect_candidate_details import parse_known_opera_detail
from scripts.auto_catalogue import promote,enrich_existing_times
from scripts.build_verified_catalog import MANIFEST,TIME_EVIDENCE,validate_time_evidence,build
from scripts.publish_catalog_v2 import REGISTRY,assemble

SINGLE="https://teatrogrande.it/it/stagioni/2026/l-italiana-in-algeri"
DOUBLE="https://teatrogrande.it/it/stagioni/2026/cavalleria-rusticana-pagliacci"

def fixture(title="L'italiana in Algeri",composer="Gioachino Rossini"):
    return (
      '<p>opera / L italiana in Algeri</p>'
      '<div>Turno A</div><div>giovedì 26 novembre 2026</div>'
      '<div>20:00, Sala Grande</div>'
      '<div>Turno B</div><div>sabato 28 novembre 2026</div>'
      '<div>15:30, Sala Grande</div>'
      '<p>Acquista online</p>'
      '<h1>'+title+' di '+composer+'</h1>'
      '<p>Musica di '+composer+'</p>'
      '<p>Accessibilità recita TURNO B sabato 28 novembre ore 15.30</p>'
    )

class BresciaDetailsTests(unittest.TestCase):
    def test_actual_official_two_ticket_showtimes_and_canonical_alias(self):
        rows=parse_brescia_detail(fixture(),url=SINGLE,
                                  title="L’italiana in Algeri",
                                  composer="Gioachino Rossini")
        self.assertEqual(rows,[("2026-11-26","20:00"),("2026-11-28","15:30")])
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        facts=parse_known_opera_detail("teatro-grande-opera-2026",SINGLE,
                                      fixture(),registry)
        self.assertEqual(len(facts),2)
        self.assertTrue(all(x["composer"]=="Gioachino Rossini" for x in facts))
        self.assertEqual({x["venue"] for x in facts},{"Teatro Grande"})
        self.assertEqual(facts[0]["event_title"],"L’italiana in Algeri")
        self.assertIn("+01:00",facts[0]["starts_at"])

    def test_double_bill_kept_out_of_single_work_publication(self):
        html=fixture("Cavalleria Rusticana/Pagliacci",
                     "Pietro Mascagni/Ruggero Leoncavallo")
        with self.assertRaisesRegex(ValueError,"combined bill"):
            parse_brescia_detail(html,url=DOUBLE,title="Cavalleria rusticana",
                                 composer="Pietro Mascagni")
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        # The old fixture lacks independent work credits: the new dual-work
        # parser must fail closed rather than yielding an invented combined opera.
        with self.assertRaisesRegex(ValueError,"independent work credit"):
            parse_known_opera_detail("teatro-grande-opera-2026",DOUBLE,html,registry)

    def test_strict_markup_and_changed_schedule_fail_closed(self):
        examples=[
            fixture().replace("Turno B","Biglietti B"),
            fixture().replace("15:30, Sala Grande","Orario da confermare"),
            fixture().replace("Gioachino Rossini","Gioachino Rossini altro",1),
            fixture().replace("20:00, Sala Grande","20:00, Ridotto"),
            fixture().replace("Turno A","ANNULLATA Turno A")]
        for html in examples:
            with self.subTest(html=html):
                with self.assertRaises(ValueError):
                    parse_brescia_detail(html,url=SINGLE,title="L’italiana in Algeri",
                                         composer="Gioachino Rossini")
        with self.assertRaises(ValueError):
            parse_brescia_detail(fixture(),url="https://outside.invalid"+SINGLE.split("it")[0],
                                 title="L’italiana in Algeri",composer="Gioachino Rossini")

    def test_brescia_promotion_requires_known_work_venue_and_exact_time(self):
        facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        urls=[SINGLE]
        evidence={"evidence":[{"candidate_id":"b-test","source_key":"teatro-grande-opera-2026",
                               "source_url":SINGLE,"status":"needs_editorial_review",
                               "event_facts":parse_known_opera_detail(
                                   "teatro-grande-opera-2026",SINGLE,fixture(),registry)}]}
        candidates={"candidates":[{"id":"b-test","source_key":"teatro-grande-opera-2026",
                                   "official_url":SINGLE,"status":"needs_review"}]}
        out,ids,approved,report=promote(facts,registry,evidence,candidates,[],
                                        today=date(2026,11,21))
        self.assertEqual(report["new_recite"],0)
        self.assertEqual(report["auto_skipped"][0]["reason"],
                         "same_recita_already_in_official_circuit")
        if report["new_recite"]:
            self.assertIn(SINGLE,approved)
            self.assertTrue(any(x["venue"]=="Teatro Grande" and x["municipality"]=="Brescia"
                                for x in out["productions"]))
            assemble(out,ids,approved_extra=set(approved))
        else:
            # When the same recite is already present from OperaLombardia,
            # the official second page must never double the catalogue.
            self.assertEqual(out,facts)
            self.assertEqual(ids,registry)

    def test_existing_brescia_circuit_gets_verified_times_without_new_ids(self):
        facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        rows=parse_known_opera_detail("teatro-grande-opera-2026",SINGLE,fixture(),registry)
        evidence={"evidence":[{"candidate_id":"b-test","source_key":"teatro-grande-opera-2026",
                               "source_url":SINGLE,"status":"needs_editorial_review",
                               "event_facts":rows}]}
        candidates={"candidates":[{"id":"b-test","source_key":"teatro-grande-opera-2026",
                                   "official_url":SINGLE,"status":"needs_review"}]}
        original=json.loads(TIME_EVIDENCE.read_text(encoding="utf-8"))
        updated,count=enrich_existing_times(facts,evidence,candidates,original)
        expected=sum(1 for day in ("2026-11-26","2026-11-28")
                     if "lombardia-italiana-brescia|"+day not in original["times"])
        self.assertEqual(count,expected)
        self.assertEqual(len(updated["times"]),len(original["times"])+expected)
        self.assertEqual(updated["times"]["lombardia-italiana-brescia|2026-11-26"],
                         {"time":"20:00","url":SINGLE})
        self.assertEqual(updated["times"]["lombardia-italiana-brescia|2026-11-28"],
                         {"time":"15:30","url":SINGLE})
        validate_time_evidence(facts,updated)
        published=build(facts,updated)
        matching=[e for e in published["performances"]
                  if e["local_date"] in ("2026-11-26","2026-11-28")
                  and e["venue"]=="Teatro Grande"] if isinstance(published,dict) else []
        self.assertEqual(len(matching),2)
        again,delta=enrich_existing_times(facts,evidence,candidates,updated)
        self.assertEqual(delta,0)
        self.assertEqual(again,updated)
        self.assertEqual(facts,json.loads(MANIFEST.read_text(encoding="utf-8")))

    def test_changed_brescia_time_not_silently_accepted(self):
        facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        rows=parse_known_opera_detail("teatro-grande-opera-2026",SINGLE,fixture(),registry)
        evidence={"evidence":[{"candidate_id":"b-test","source_key":"teatro-grande-opera-2026",
                               "source_url":SINGLE,"status":"needs_editorial_review",
                               "event_facts":rows}]}
        candidates={"candidates":[{"id":"b-test","source_key":"teatro-grande-opera-2026",
                                   "official_url":SINGLE,"status":"needs_review"}]}
        old=json.loads(TIME_EVIDENCE.read_text(encoding="utf-8"))
        updated,_=enrich_existing_times(facts,evidence,candidates,old)
        evidence["evidence"][0]["event_facts"][0]["starts_at"]="2026-11-26T21:00:00+01:00"
        next_doc,n=enrich_existing_times(facts,evidence,candidates,updated)
        self.assertEqual(n,0)
        self.assertEqual(next_doc,updated)

if __name__=="__main__":
    unittest.main()
