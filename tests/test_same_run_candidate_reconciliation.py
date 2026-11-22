"""Published productions must leave the discovery queue in the same run."""
import copy
import unittest
from scripts.reconcile_published_candidates import reconcile

class SameRunCandidateReconciliationTests(unittest.TestCase):
    def test_newly_published_production_moves_to_catalogued_immediately(self):
        rows={"schema_version":1,"candidates":[
            {"id":"new-carmen","source_key":"arena-festival-2027",
             "official_url":"https://www.arena.it/arena-opera-festival/carmen/",
             "status":"needs_review","first_seen":"first","last_seen":"last"},
            {"id":"future","source_key":"scala-season-2026-27",
             "official_url":"https://www.teatroallascala.org/it/stagione/2026-2027/opera/future.html",
             "status":"needs_review","first_seen":"first","last_seen":"last"},
            {"id":"manual","source_key":"arena-festival-2027",
             "official_url":"https://www.arena.it/arena-opera-festival/carmen/",
             "status":"editorially_rejected","first_seen":"first","last_seen":"last"}
        ]}
        before=copy.deepcopy(rows)
        results,report=reconcile(rows,{"https://www.arena.it/arena-opera-festival/carmen/"})
        self.assertEqual(rows,before)
        by={x["id"]:x for x in results["candidates"]}
        self.assertEqual(by["new-carmen"]["status"],"already_catalogued")
        self.assertEqual(by["future"]["status"],"needs_review")
        self.assertEqual(by["manual"]["status"],"editorially_rejected")
        self.assertEqual(by["new-carmen"]["first_seen"],"first")
        self.assertEqual(by["new-carmen"]["last_seen"],"last")
        self.assertEqual(report["states"]["already_catalogued"],1)
        self.assertEqual(len(report["changes"]),1)
        twice,second=reconcile(results,{"https://www.arena.it/arena-opera-festival/carmen/"})
        self.assertEqual(twice,results)
        self.assertEqual(second["changes"],[])

    def test_treviso_one_candidate_shared_season_requires_all_observed_works(self):
        from scripts.reconcile_published_candidates import verified_shared_page_identities
        source="treviso-del-monaco-opera-2026-27"
        url="https://risorse.teatrostabileveneto.it/treviso-teatro-del-monaco-stagione-lirica-concertistica-26-27"
        candidates={"schema_version":1,"candidates":[{
            "id":"treviso","source_key":source,"official_url":url,
            "status":"already_catalogued"}]}
        details={"evidence":[{
            "candidate_id":"treviso","source_key":source,"source_url":url,
            "event_facts":[
                {"event_title":"La traviata","composer":"Giuseppe Verdi","date":"2026-10-23"},
                {"event_title":"Pagliacci","composer":"Ruggero Leoncavallo","date":"2026-12-04"}]}]}
        facts={"productions":[{"title":"La traviata","composer":"Giuseppe Verdi",
            "source_url":url,"dates":[["2026-10-23","20:00"]]}]}
        ambiguous,verified=verified_shared_page_identities(
            candidates,details,facts,{"programs":[]})
        self.assertIn(url,ambiguous)
        self.assertNotIn((source,url),verified)
        result,_=reconcile(candidates,{url},ambiguous_urls=ambiguous,
                            identity_verified=verified)
        self.assertEqual(result["candidates"][0]["status"],"needs_review")
        facts["productions"].append({"title":"Pagliacci","composer":"Ruggero Leoncavallo",
            "source_url":url,"dates":[["2026-12-04","20:00"]]})
        _,verified=verified_shared_page_identities(
            candidates,details,facts,{"programs":[]})
        self.assertIn((source,url),verified)

    def test_shared_official_season_page_never_retires_other_works(self):
        from scripts.reconcile_published_candidates import verified_shared_page_identities
        url="https://theatre.example/season-2026/"
        keys=("jesi-nabucco-opera-2026","jesi-trittico-opera-2026",
              "jesi-don-pasquale-opera-2026","jesi-esecuzione-opera-2026")
        names=(("Nabucco","Giuseppe Verdi"),("Il tabarro","Giacomo Puccini"),
               ("Don Pasquale","Gaetano Donizetti"),("L'esecuzione","Salvatore Passantino"))
        records={"schema_version":1,"candidates":[
            {"id":str(i),"source_key":key,"official_url":url,
             "status":"already_catalogued"} for i,key in enumerate(keys)]}
        detail={"evidence":[
            {"candidate_id":str(i),"source_key":key,"source_url":url,
             "event_facts":[{"event_title":name,"composer":composer,"date":"2026-11-14"}]}
            for i,(key,(name,composer)) in enumerate(zip(keys,names))]}
        manifest={"productions":[
            {"title":"Nabucco","composer":"Giuseppe Verdi",
             "source_url":url,"dates":[["2026-11-14","20:30"]]}]}
        programs={"programs":[{
            "source_key":"jesi-trittico-opera-2026","source_url":url,
            "components":[{"title":"Il tabarro","composer":"Giacomo Puccini"}],
            "performances":[{"local_date":"2026-11-14"}]}]}
        ambiguous,verified=verified_shared_page_identities(
            records,detail,manifest,programs)
        self.assertEqual(ambiguous,{url})
        self.assertEqual(verified,{(keys[0],url),(keys[1],url)})
        reconciled,report=reconcile(records,{url},ambiguous_urls=ambiguous,
                                     identity_verified=verified)
        self.assertEqual([x["status"] for x in reconciled["candidates"]],
                         ["already_catalogued","already_catalogued",
                          "needs_review","needs_review"])
        self.assertEqual(len(report["changes"]),2)

    def test_published_program_is_stable_across_refreshes(self):
        program_url="https://www.fondazionepetruzzelli.it/eventi/larlesienne-di-georges-bizet-pagliacci-di-ruggero-leoncavallo-13-20-ottobre/"
        candidate={"schema_version":1,"candidates":[{
            "id":"mixed","source_key":"petruzzelli-opera-2027",
            "official_url":program_url,"status":"needs_review",
            "first_seen":"old","last_seen":"recent"}]}
        published={program_url}
        first,report=reconcile(candidate,published)
        self.assertEqual(first["candidates"][0]["status"],"already_catalogued")
        self.assertEqual(first["candidates"][0]["first_seen"],"old")
        second,again=reconcile(first,published)
        self.assertEqual(first,second)
        self.assertFalse(again["changes"])

    def test_known_nonopera_is_excluded_but_kept_as_audit_record(self):
        old={"schema_version":1,"candidates":[{
            "id":"irrelevant","source_key":"arena-festival-2027",
            "official_url":"https://www.arena.it/arena-opera-festival/regolamento/",
            "status":"needs_review","first_seen":"old","last_seen":"old"}]}
        result,report=reconcile(old,set())
        self.assertEqual(result["candidates"][0]["status"],"excluded_nonopera")
        self.assertEqual(result["candidates"][0]["first_seen"],"old")
        self.assertEqual(report["total"],1)

    def test_complete_verified_second_theatre_source_is_resolved(self):
        import json
        from scripts.publish_catalog_v2 import ROOT
        from scripts.reconcile_published_candidates import verified_secondary_source_urls
        manifest=json.loads((ROOT/"data/verified-launch-catalog.json").read_text())
        verified=json.loads((ROOT/"data/verified-time-evidence.json").read_text())
        url="https://teatrogrande.it/it/stagioni/2026/l-italiana-in-algeri"
        equivalent=verified_secondary_source_urls(manifest,verified)
        self.assertIn(url,equivalent)
        candidate={"schema_version":1,"candidates":[{
            "id":"known-circuit","source_key":"teatro-grande-opera-2026",
            "official_url":url,"status":"needs_review",
            "first_seen":"first","last_seen":"last"}]}
        updated,_=reconcile(candidate,equivalent)
        self.assertEqual(updated["candidates"][0]["status"],"already_catalogued")
        partial=copy.deepcopy(verified)
        partial["times"].pop("lombardia-italiana-brescia|2026-11-28")
        self.assertNotIn(url,verified_secondary_source_urls(manifest,partial))

    def test_invalid_registry_rejected_instead_of_erasing_queue(self):
        with self.assertRaises(ValueError):
            reconcile({"schema_version":1,"candidates":None},set())
if __name__=="__main__":
    unittest.main()
