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

    def test_shared_page_identity_survives_lagging_url_index(self):
        # A verified matching solo/program identity must not be reset simply
        # because the generic URL publication index lags this checkpoint.
        url="https://theatre.example/season"
        source="example-opera-2027"
        candidates={"schema_version":1,"candidates":[
            {"id":"verified","source_key":source,"official_url":url,
             "status":"needs_review"},
            {"id":"unverified","source_key":"another-opera-2027",
             "official_url":url,"status":"already_catalogued"}]}
        identity={(source,url)}
        result,report=reconcile(candidates,set(),ambiguous_urls={url},
                                 identity_verified=identity)
        self.assertEqual([row["status"] for row in result["candidates"]],
                         ["already_catalogued","needs_review"])
        self.assertEqual(len(report["changes"]),2)
        again,second=reconcile(result,set(),ambiguous_urls={url},
                               identity_verified=identity)
        self.assertEqual(again,result)
        self.assertFalse(second["changes"])

    def test_pisa_calendar_recite_aliases_reconcile_only_exact_verified_showtimes(self):
        from scripts.reconcile_published_candidates import verified_pisa_recital_urls
        manifest={"productions":[
            {"title":"Otello","composer":"Giuseppe Verdi",
             "municipality":"Pisa","venue":"Teatro Verdi",
             "source_url":"https://teatrodipisa.it/spettacolo/otello/",
             "dates":[["2027-02-05","20:30"],["2027-02-07","15:30"]]},
            {"title":"L'occasione fa il ladro","composer":"Gioachino Rossini",
             "municipality":"Pisa","venue":"Teatro Verdi",
             "source_url":"https://teatrodipisa.it/spettacolo/loccasione-fa-il-ladro-ossia-il-cambio-della-valigia/",
             "dates":[["2026-12-04","20:30"]]}]}
        digest="a"*64
        def row(name,title,day,time="20:30",sha=digest,source="pisa-future-calendar"):
            return {"source_key":source,
                    "source_url":"https://teatrodipisa.it/calendario/"+name+"/",
                    "content_sha256":sha,
                    "event_facts":[{"event_title":title,"date":day,
                                    "starts_at":day+"T"+time+":00+01:00"}]}
        evidence={"evidence":[
            row("otello","Otello","2027-02-05"),
            row("otello-3","Otello","2027-02-07","15:30"),
            row("occasione","L&#8217;occasione fa il ladro ossia il Cambio della valigia",
                "2026-12-04"),
            row("wrong-time","Otello","2027-02-05","21:00"),
            row("wrong-title","Aida","2027-02-05"),
            row("missing-hash","Otello","2027-02-05",sha=""),
            row("wrong-source","Otello","2027-02-05",source="other"),
        ]}
        result=verified_pisa_recital_urls(manifest,evidence)
        self.assertEqual(result,{
            "https://teatrodipisa.it/calendario/otello/",
            "https://teatrodipisa.it/calendario/otello-3/",
            "https://teatrodipisa.it/calendario/occasione/",
        })
        rows={"schema_version":1,"candidates":[
            {"id":str(i),"source_key":"pisa-future-calendar",
             "official_url":item["source_url"],"status":"needs_review"}
            for i,item in enumerate(evidence["evidence"])]}
        updated,_=reconcile(rows,result)
        self.assertEqual([r["status"] for r in updated["candidates"]],
                         ["already_catalogued"]*3+["needs_review"]*4)
        again,health=reconcile(updated,result)
        self.assertEqual(updated,again)
        self.assertFalse(health["changes"])

    def test_annual_and_rolling_source_are_aliases_of_one_published_staging(self):
        from scripts.reconcile_published_candidates import verified_shared_page_identities
        for annual,rolling,url,title,composer in (
            ("filarmonico-verona-opera-2027","filarmonico-verona-rolling-opera",
             "https://www.arena.it/teatro-filarmonico-verona/2027/fidelio/",
             "Fidelio","Ludwig van Beethoven"),
            ("coccia-novara-opera-2027","coccia-novara-rolling-opera",
             "https://www.fondazioneteatrococcia.it/stagione-27-rigoletto.html",
             "Rigoletto","Giuseppe Verdi"),
        ):
            with self.subTest(source=rolling):
                rows={"schema_version":1,"candidates":[
                    {"id":key,"source_key":key,"official_url":url,
                     "status":"needs_review"} for key in (annual,rolling)]}
                production={"source_url":url,"title":title,"composer":composer,
                            "dates":[["2027-01-29","20:00"]]}
                ambiguous,verified=verified_shared_page_identities(
                    rows,{"evidence":[]},{"productions":[production]},
                    {"programs":[]})
                self.assertIn(url,ambiguous)
                self.assertEqual(verified,{(annual,url),(rolling,url)})
                updated,_=reconcile(rows,{url},ambiguous_urls=ambiguous,
                                    identity_verified=verified)
                self.assertTrue(all(r["status"]=="already_catalogued"
                                    for r in updated["candidates"]))
                again,health=reconcile(updated,{url},ambiguous_urls=ambiguous,
                                       identity_verified=verified)
                self.assertEqual(again,updated)
                self.assertFalse(health["changes"])

    def test_macerata_annual_rolling_verified_same_staging(self):
        from scripts.reconcile_published_candidates import verified_shared_page_identities
        annual="macerata-festival-2027"
        rolling="macerata-festival-rolling"
        url="https://www.sferisterio.it/macerata-opera-festival/elisir-damore"
        candidates={"schema_version":1,"candidates":[
            {"id":key,"source_key":key,"official_url":url,
             "status":"needs_review"} for key in (annual,rolling)]}
        production={"source_url":url,"title":"L’elisir d’amore",
                    "composer":"Gaetano Donizetti",
                    "dates":[["2027-07-24","21:00"],["2027-07-30","21:00"]]}
        details={"evidence":[{"source_key":annual,"source_url":url,
                              "event_facts":[
                                  {"event_title":"L'elisir d'amore",
                                   "composer":"Gaetano Donizetti","date":"2027-07-24"},
                                  {"event_title":"L'elisir d'amore",
                                   "composer":"Gaetano Donizetti","date":"2027-07-30"}]}]}
        ambiguous,verified=verified_shared_page_identities(
            candidates,details,{"productions":[production]},{"programs":[]})
        self.assertEqual(verified,{(annual,url),(rolling,url)})
        updated,report=reconcile(candidates,{url},ambiguous_urls=ambiguous,
                                 identity_verified=verified)
        self.assertEqual(report["states"],{"already_catalogued":2})
        again,health=reconcile(updated,{url},ambiguous_urls=ambiguous,
                               identity_verified=verified)
        self.assertEqual(again,updated)
        self.assertFalse(health["changes"])
        # A conflicting composer must reopen both collectors for review.
        details["evidence"][0]["event_facts"][0]["composer"]="Other composer"
        _,verified=verified_shared_page_identities(
            candidates,details,{"productions":[production]},{"programs":[]})
        self.assertFalse(verified)

    def test_sassari_and_ravenna_rolling_aliases_match_only_one_staging(self):
        from scripts.reconcile_published_candidates import verified_shared_page_identities
        cases=(
            ("sassari-de-carolis-opera-2026","sassari-de-carolis-rolling-opera",
             "https://www.marialisadecarolis.it/opera-lirica.aspx?id=372",
             "Die Zauberflöte","Wolfgang Amadeus Mozart","2026-09-25"),
            ("sassari-de-carolis-opera-2026","sassari-de-carolis-rolling-opera",
             "https://www.marialisadecarolis.it/opera-lirica.aspx?id=373",
             "Don Carlos","Giuseppe Verdi","2026-10-30"),
            ("sassari-de-carolis-opera-2026","sassari-de-carolis-rolling-opera",
             "https://www.marialisadecarolis.it/opera-lirica.aspx?id=375",
             "Rigoletto","Giuseppe Verdi","2026-12-11"),
            ("ravenna-alighieri-cherubini-2027","ravenna-cherubini-rolling-opera",
             "https://www.orchestracherubini.it/eventi/pagliacci-2/",
             "Pagliacci","Ruggero Leoncavallo","2027-01-15"),
            ("ravenna-alighieri-cherubini-2027","ravenna-cherubini-rolling-opera",
             "https://www.orchestracherubini.it/eventi/la-cenerentola-4/",
             "La Cenerentola","Gioachino Rossini","2027-04-02"),
        )
        for annual,rolling,url,title,composer,day in cases:
            with self.subTest(url=url):
                candidates={"schema_version":1,"candidates":[
                    {"id":key,"source_key":key,"official_url":url,
                     "status":"needs_review"} for key in (annual,rolling)]}
                production={"source_url":url,"title":title,"composer":composer,
                            "dates":[[day,"20:00"]]}
                ambiguous,verified=verified_shared_page_identities(
                    candidates,{"evidence":[]},{"productions":[production]},
                    {"programs":[]})
                self.assertIn(url,ambiguous)
                self.assertEqual(verified,{(annual,url),(rolling,url)})
                updated,report=reconcile(candidates,{url},
                    ambiguous_urls=ambiguous,identity_verified=verified)
                self.assertEqual(report["states"],{"already_catalogued":2})
                again,health=reconcile(updated,{url},
                    ambiguous_urls=ambiguous,identity_verified=verified)
                self.assertEqual(again,updated)
                self.assertFalse(health["changes"])
                # Official evidence that contradicts the catalog must block
                # automatic retirement of both source observations.
                bad={"evidence":[{"source_key":rolling,"source_url":url,
                     "event_facts":[{"event_title":title,"composer":"Wrong composer",
                                     "date":day}]}]}
                _,verified=verified_shared_page_identities(
                    candidates,bad,{"productions":[production]},{"programs":[]})
                self.assertFalse(verified)
                _,verified=verified_shared_page_identities(
                    candidates,{"evidence":[]},
                    {"productions":[production,dict(production,title="Other opera")]},
                    {"programs":[]})
                self.assertFalse(verified)

    def test_source_alias_never_hides_distinct_or_conflicting_opera(self):
        from scripts.reconcile_published_candidates import verified_shared_page_identities
        url="https://www.arena.it/teatro-filarmonico-verona/2027/fidelio/"
        annual="filarmonico-verona-opera-2027"
        rolling="filarmonico-verona-rolling-opera"
        rows={"schema_version":1,"candidates":[
            {"id":key,"source_key":key,"official_url":url,"status":"needs_review"}
            for key in (annual,rolling)]}
        production={"source_url":url,"title":"Fidelio",
                    "composer":"Ludwig van Beethoven",
                    "dates":[["2027-04-11","15:30"]]}
        detail={"evidence":[{"source_key":rolling,"source_url":url,
                             "event_facts":[{"event_title":"Other opera",
                                             "composer":"Other composer",
                                             "date":"2027-04-11"}]}]}
        ambiguous,verified=verified_shared_page_identities(
            rows,detail,{"productions":[production]},{"programs":[]})
        self.assertFalse(verified)
        # A page holding multiple independently staged compositions cannot
        # be closed just because one verified production uses the same URL.
        ambiguous,verified=verified_shared_page_identities(
            rows,{"evidence":[]},{"productions":[production,dict(production,
                        title="Other opera")]},{"programs":[]})
        self.assertFalse(verified)
        rows["candidates"][1]["source_key"]="unrelated-opera-2027"
        ambiguous,verified=verified_shared_page_identities(
            rows,{"evidence":[]},{"productions":[production]},{"programs":[]})
        self.assertFalse(verified)

    def test_dated_old_season_proof_overrides_duplicate_candidate_url(self):
        url="https://www.fondazionepetruzzelli.it/eventi/la-notte-di-san-nicola-25-28-29-maggio/"
        source_keys=("petruzzelli-opera-2026","petruzzelli-opera-2027")
        rows={"schema_version":1,"candidates":[
            {"id":key,"source_key":key,"official_url":url,
             "status":"needs_review"} for key in source_keys]}
        old={(key,url) for key in source_keys}
        result,report=reconcile(rows,set(),other_season_urls=old,
                                 ambiguous_urls={url})
        self.assertEqual([row["status"] for row in result["candidates"]],
                         ["not_in_official_season"]*2)
        self.assertEqual(len(report["changes"]),2)
        again,health=reconcile(result,set(),other_season_urls=old,
                               ambiguous_urls={url})
        self.assertEqual(again,result)
        self.assertFalse(health["changes"])
        # A confirmed live production is not retired as an older season
        # simply because stale detail evidence also names the same URL.
        published,report=reconcile(rows,{url},other_season_urls=old,
                                  ambiguous_urls=set())
        self.assertTrue(all(row["status"]=="already_catalogued"
                            for row in published["candidates"]))

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
