"""Institutional Marrucino season: exactly seven official showtimes, no guesses."""
import json
import unittest
from datetime import date

from opera_atlas.chieti_marrucino_parser import URL,parse_program
from scripts.discover_season_indexes import eligible,extract,CONFIG,validate_config
from scripts.collect_candidate_details import parse_known_opera_detail
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY
from scripts.auto_catalogue import promote,split_verified_season

HTML="""<h1>Presentata la Stagione Lirica 2026 del Teatro Marrucino</h1>
<p>Ad inaugurare la programmazione sarà l’anteprima di stagione, sabato
26 settembre alle ore 21.00, con Le avventure di Pinocchio, opera in due
atti composta da Antonio Cericola.</p>
<p>La Stagione entrerà nel vivo con Turandot di Giacomo Puccini,
in scena venerdì 23 ottobre alle 20.30 e domenica 25 ottobre
alle 17.30.</p>
<p>Il secondo appuntamento della Stagione sarà dedicato a Le Nozze di Figaro
di Wolfgang Amadeus Mozart, in programma venerdì 20 novembre alle
20.30 e domenica 22 novembre alle 17.30.</p>
<p>A chiudere la Stagione Lirica 2026 sarà La Traviata di Giuseppe Verdi,
in scena venerdì 11 dicembre alle 20.30 e domenica 13 dicembre
alle 17.30.</p><p>La vicenda di Violetta Valery</p>"""

class ChietiSourceTests(unittest.TestCase):
    def test_exact_approved_source_and_seven_recite(self):
        entries=validate_config(json.loads(CONFIG.read_text(encoding="utf-8")))
        self.assertTrue(any(x["key"]=="chieti-marrucino-lirica-2026" for x in entries))
        self.assertTrue(eligible("chieti-marrucino-lirica-2026",URL))
        self.assertFalse(eligible("chieti-marrucino-lirica-2026",URL+"?utm=test"))
        rows=parse_program(HTML,url=URL)
        self.assertEqual(len(rows),7)
        self.assertEqual(rows[0][-2:],("2026-09-26","21:00"))
        self.assertEqual(rows[-1][-2:],("2026-12-13","17:30"))
        self.assertEqual(extract("chieti-marrucino-lirica-2026",URL,HTML,1),[URL])

    def test_three_known_operas_are_promoted_without_duplicate_works(self):
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        rows=parse_known_opera_detail("chieti-marrucino-lirica-2026",URL,HTML,registry)
        self.assertEqual(len(rows),7)
        cid="test-chieti-season"
        item={"candidate_id":cid,"source_key":"chieti-marrucino-lirica-2026",
              "source_url":URL,"status":"needs_editorial_review","event_facts":rows}
        self.assertEqual(len(split_verified_season(item)),4)
        candidates={"schema_version":1,"candidates":[
            {"id":cid,"source_key":item["source_key"],"official_url":URL,
             "status":"needs_review"}]}
        evidence={"schema_version":1,"evidence":[item]}
        published,ids,urls,report=promote(facts,registry,evidence,candidates,[],
                                          today=date(2026,11,22))
        # The cached publisher may promote Pinocchio as soon as its
        # independently verified editorial/authority data is complete.
        # Include it only if the canonical work identity is already
        # registered; otherwise it must remain in the authority queue.
        known=("Turandot","Le nozze di Figaro","La traviata")
        pinocchio=any(w["title"]=="Le avventure di Pinocchio"
                      and w["composer"]=="Antonio Cericola"
                      for w in registry["works"].values())
        eligible=known+(("Le avventure di Pinocchio",) if pinocchio else ())
        previous=[x for x in facts["productions"]
                  if x["municipality"]=="Chieti"
                  and x["venue"]=="Teatro Marrucino"
                  and x["source_url"]==URL and x["title"] in eligible]
        expected_new=len(eligible)-len(previous)
        self.assertEqual(report["new_stagings"],expected_new,report)
        self.assertEqual(report["new_recite"],2*len(known)+int(pinocchio)
                         -sum(len(x["dates"]) for x in previous),report)
        for title in known:
            selected=[x for x in published["productions"]
                      if x["municipality"]=="Chieti" and
                      x["venue"]=="Teatro Marrucino" and
                      x["source_url"]==URL and x["title"]==title]
            self.assertEqual(len(selected),1,(title,report))
            self.assertEqual(len(selected[0]["dates"]),2,(title,report))
        if pinocchio:
            selected=[x for x in published["productions"]
                      if x["municipality"]=="Chieti" and
                      x["venue"]=="Teatro Marrucino" and
                      x["source_url"]==URL and
                      x["title"]=="Le avventure di Pinocchio"]
            self.assertEqual(len(selected),1,report)
            self.assertEqual(selected[0]["dates"],[["2026-09-26","21:00"]])
        else:
            self.assertTrue(any(x["reason"]=="unknown_work_needs_authority_data"
                                for x in report["auto_skipped"]))
        self.assertEqual(len(ids["works"]),len(registry["works"]))
        again,again_ids,_,again_report=promote(
            published,ids,evidence,candidates,urls,today=date(2026,11,22))
        self.assertEqual(again_report["new_recite"],0)
        self.assertEqual(again,published)
        self.assertEqual(again_ids,ids)

    def test_malformed_or_ambiguous_calendar_is_rejected(self):
        for modified in (
            HTML.replace("Wolfgang Amadeus Mozart","Gioachino Rossini"),
            HTML.replace("domenica 13 dicembre","domenica 12 dicembre"),
            HTML.replace("venerdì 23 ottobre alle 20.30 e",""),
            HTML.replace("Stagione Lirica 2026","Stagione Lirica 2025"),
            HTML.replace("La Traviata di Giuseppe Verdi","La Traviata di Giuseppe Verdi annullata"),
        ):
            with self.subTest(modified=modified[:70]):
                with self.assertRaises(ValueError):
                    parse_program(modified,url=URL)
        with self.assertRaises(ValueError):
            parse_program(HTML,url=URL.replace("https://","http://"))

if __name__=="__main__":
    unittest.main()
