"""Corroboration requires issuer repertoire and two publisher domains."""
import copy
import json
import unittest
from datetime import date

from scripts.corroborate_performances import CONFIG,integrate,verify_pages,validate_case
from scripts.auto_catalogue import promote
from scripts.publish_catalog_v2 import ROOT

CASE=json.loads(CONFIG.read_text())["cases"][0]
ISSUER=("<html><p>La stagione 2026/2027 del Teatro Sociale "
        "prosegue con Pagliacci di R. Leoncavallo e Traviata di G. Verdi, "
        "Aida di G. Verdi.</p>"
        "<p>La Traviata del 2021 fu eseguita in novembre.</p></html>")
CROSS=("<h1>La Traviata</h1><p>Teatro Sociale, Rovigo</p>"
       "<p>Giuseppe Verdi: le recite pubbliche sono il 22 gennaio "
       "alle 20:30 e il 24 gennaio alle 16:00, con anteprima "
       "(prova generale) il 21 gennaio alle 16:00.</p>")
def classicalive(day,clock,weekday):
    return (f"<h3>{weekday} {day} gennaio 2027</h3><h6>ore {clock}</h6>"
            "<h4>Rovigo</h4><h5>Teatro Sociale</h5>"
            "<p>Giuseppe Verdi</p><h1>La traviata</h1>"
            "<p>Fonte: https://www.comune.rovigo.it/teatrosociale/"
            "dettaglio-teatro/eventi/la-traviata-2027</p>")
def pages():
    return {
        CASE["issuer_repertoire_url"]:ISSUER,
        CASE["independent_event_url"]:CROSS,
        CASE["publisher_events"][0]["url"]:classicalive(22,"20:30","venerdì"),
        CASE["publisher_events"][1]["url"]:classicalive(24,"16:00","domenica"),
    }

class CorroborationTests(unittest.TestCase):
    def test_four_sources_concur_with_known_canonical_dates(self):
        rows=verify_pages(CASE,pages())
        self.assertEqual(len(rows),2)
        self.assertEqual([x["date"] for x in rows],
                         ["2027-01-22","2027-01-24"])
        self.assertEqual([x["starts_at"][-6:] for x in rows],
                         ["+01:00","+01:00"])

    def test_missing_or_conflicting_source_fails_closed(self):
        source=pages()
        altered=[
            {k:v for k,v in source.items() if k!=CASE["independent_event_url"]},
            {**source,CASE["issuer_repertoire_url"]:
             ISSUER.replace("2026/2027","2021/2022")},
            {**source,CASE["independent_event_url"]:
             CROSS.replace("24 gennaio alle 16:00","24 gennaio alle 18:00")},
            {**source,CASE["publisher_events"][1]["url"]:
             classicalive(24,"18:00","domenica")},
        ]
        for docs in altered:
            with self.subTest(docs=list(docs)),self.assertRaises(ValueError):
                verify_pages(CASE,docs)
        wrong=copy.deepcopy(CASE)
        wrong["publisher_events"][0]["url"]="https://evil.test/la-traviata"
        with self.assertRaises(ValueError):
            validate_case(wrong)

    def test_corroboration_enters_existing_canonical_reconciler(self):
        now="2026-11-22T16:00:00+00:00"
        candidates={"schema_version":1,"candidates":[]}
        evidence={"schema_version":1,"evidence":[]}
        c,e,status=integrate(CASE,pages(),candidates,evidence,now)
        self.assertEqual(status,"corroborated")
        self.assertEqual(len(c["candidates"]),1)
        record=e["evidence"][0]
        self.assertEqual(record["corroboration"]["method"],
                         "issuer_repertoire_plus_two_secondary_publishers")
        self.assertFalse(record["corroboration"]["official_event_page_retrieved"])
        facts=json.loads((ROOT/"data/verified-launch-catalog.json").read_text())
        registry=json.loads((ROOT/"data/identity-registry.json").read_text())
        approved=json.loads((ROOT/"data/auto-source-urls.json").read_text())
        output,ids,urls,report=promote(
            facts,registry,e,c,approved["urls"],today=date(2026,11,22))
        self.assertEqual(report["auto_skipped"],[])
        rovigo=[x for x in output["productions"] if x["municipality"]=="Rovigo"]
        self.assertEqual(len(rovigo),1)
        self.assertEqual(rovigo[0]["title"],"La traviata")
        self.assertEqual(rovigo[0]["dates"],
                         [["2027-01-22","20:30"],["2027-01-24","16:00"]])
        self.assertEqual(ids["venues"]["Rovigo|Teatro Sociale"]["city"],"Rovigo")
        # A verified launch catalogue may already contain the Rovigo staging
        # from an earlier ingestion. Confirm exact dates either way, without
        # falsely counting existing recite as newly published.
        existing=any(p.get("municipality")=="Rovigo" and
                     p.get("title")=="La traviata" and
                     p.get("dates")==[["2027-01-22","20:30"],
                                      ["2027-01-24","16:00"]]
                     for p in facts.get("productions",[]))
        self.assertEqual(report["new_recite"],0 if existing else 2)
        # Repeated input must not allocate duplicate canonical staging/recite.
        after,_,_,repeat=promote(
            output,ids,e,c,urls,today=date(2026,11,22))
        self.assertEqual(repeat["new_recite"],0)
        self.assertEqual(len([x for x in after["productions"]
                              if x["municipality"]=="Rovigo"]),1)

if __name__=="__main__":
    unittest.main()
