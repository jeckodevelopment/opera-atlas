"""Bounded detail scanning keeps proposed facts out of the canonical catalog."""
import json
import unittest
from datetime import date

from opera_atlas.controlled_fetch import FetchResult,FetchUnavailable
from scripts.collect_candidate_details import parse_event_facts,selected_candidates,collect,parse_known_opera_detail,parse_authoritative_new_work_detail,MAX_PAGES,MAX_PER_SOURCE
from scripts.publish_catalog_v2 import REGISTRY

class CandidateDetailTests(unittest.TestCase):
    def setUp(self):
        self.empty={"schema_version":1,"evidence":[]}
        self.candidates={"schema_version":1,"candidates":[{
            "id":"candidate-a","source_key":"scala-season-2026-27",
            "official_url":"https://www.teatroallascala.org/it/stagione/2026-2027/opera/anna-bolena.html",
            "status":"needs_review"},
            {"id":"candidate-b","source_key":"arena-festival-2027",
             "official_url":"https://www.arena.it/arena-opera-festival/regolamento/",
             "status":"excluded_nonopera"},
            {"id":"candidate-c","source_key":"fenice-opera-2026-27",
             "official_url":"https://other.example/event/fake/","status":"needs_review"}
        ]}
    def test_palermo_work_identity_from_official_composer_and_full_calendar(self):
        from scripts.collect_candidate_details import parse_official_massimo_work_detail
        url="https://www.teatromassimo.it/event/ernani-2/"
        html=("<p>Date 31 Ottobre 20:00 Turno Prime "
              "2 Novembre 18:30 Turno Opera</p>"
              "<h2>Lo spettacolo</h2><p>31 ottobre, 2 novembre 2027 | Sala Grande</p>"
              "<h1>Ernani</h1><p>Musiche di Giuseppe Verdi</p>"
              "<p>Dramma lirico in quattro parti</p><p>Direttore Altro Musicista</p>")
        rows=parse_official_massimo_work_detail(url,html)
        self.assertEqual([(x["date"],x["composer"]) for x in rows],
                         [("2027-10-31","Giuseppe Verdi"),
                          ("2027-11-02","Giuseppe Verdi")])
        self.assertTrue(all(x["starts_at"].endswith("+01:00") for x in rows))
        self.assertEqual(rows[0]["venue"],"Teatro Massimo")

    def test_palermo_uncredited_or_ambiguous_work_fails_closed(self):
        from scripts.collect_candidate_details import parse_official_massimo_work_detail
        url="https://www.teatromassimo.it/event/ernani-2/"
        common=("<p>31 Ottobre 20:00</p><h2>Lo spettacolo</h2>"
                "<p>31 ottobre 2027 | Sala Grande</p><h1>Ernani</h1>")
        for credit in ("<p>Direttore Giuseppe Verdi</p>",
                       "<p>Musiche di Giuseppe Verdi</p><p>Musiche di Altro Compositore</p>",
                       "<p>Musiche di Giuseppe Verdi</p><p>Il giorno 31 ottobre rinviato</p>"):
            with self.subTest(credit=credit),self.assertRaises(ValueError):
                parse_official_massimo_work_detail(url,common+credit+
                                                  "<p>Dramma lirico</p>")
        with self.assertRaises(ValueError):
            parse_official_massimo_work_detail(
                "https://untrusted.example/event/ernani-2/",
                common+"<p>Musiche di Giuseppe Verdi</p><p>Dramma lirico</p>")

    def test_parma_official_composer_and_only_public_dates(self):
        from scripts.collect_candidate_details import parse_official_parma_work_detail
        url="https://teatroregioparma.it/spettacolo/boris-godunov/"
        html=("<h1>Boris Godunov</h1><p>Modest Petrovič Musorgskij</p>"
              "<p>18 gen 2027</p><p>22 gen 2027</p>"
              "<h2>Spettacolo</h2><p>Musica Modest Petrovič Musorgskij</p>"
              "<p>Dramma musicale in quattro parti</p>"
              "<h2>Teatro Regio di Parma</h2>"
              "<p>lun 18 gen 20:00 Prova Under30</p>"
              "<p>ven 22 gen 20:00 TURNO A</p>"
              "<p>Biglietti per il pubblico</p>")
        rows=parse_official_parma_work_detail(url,html)
        self.assertEqual([(x["date"],x["composer"]) for x in rows],
                         [("2027-01-22","Modest Petrovič Musorgskij")])
        self.assertEqual(rows[0]["venue"],"Teatro Regio di Parma")
        with self.assertRaises(ValueError):
            parse_official_parma_work_detail(
                url,html.replace("Musica Modest Petrovič Musorgskij",
                                 "Direttore Modest Petrovič Musorgskij"))

    def test_fenice_real_venue_and_school_only_dates(self):
        from scripts.collect_candidate_details import parse_source_credited_opera_detail
        from opera_atlas.national_detail_parser import fenice_primary_credits
        url="https://www.teatrolafenice.it/event/larca-di-noe/"
        html=("<h1>L'arca di Noè</h1><p>Benjamin Britten</p>"
              "<p>Teatro Malibran</p><p>Seleziona una data:</p>"
              "<a>mercoledì 17 Marzo 2027 11:00 RISERVATO ALLE SCUOLE</a>"
              "<a>sabato 20 Marzo 2027 15:30 ACQUISTA</a>")
        self.assertEqual(fenice_primary_credits(html),
                         ("L'arca di Noè","Benjamin Britten","Teatro Malibran"))
        rows=parse_source_credited_opera_detail("fenice-opera-2026-27",url,html)
        self.assertEqual([(x["date"],x["venue"]) for x in rows],
                         [("2027-03-20","Teatro Malibran")])
        with self.assertRaises(ValueError):
            fenice_primary_credits(html.replace("Benjamin Britten",""))
        self.assertEqual(parse_source_credited_opera_detail(
            "fenice-opera-2026-27","https://fake.example/event/larca-di-noe/",html),[])

    def test_structured_music_composer_is_preserved_not_conductor(self):
        event={"@type":"MusicEvent","name":"Il barbiere di Siviglia",
               "startDate":"2027-05-09T20:00:00+02:00",
               "location":{"@type":"Place","name":"Teatro alla Scala"},
               "performer":{"name":"Other Conductor"},
               "workPerformed":{"@type":"MusicComposition",
                                "composer":{"@type":"Person","name":"Giovanni Paisiello"}}}
        html='<script type="application/ld+json">'+json.dumps(event)+'</script>'
        result=parse_event_facts(html)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["composer"],"Giovanni Paisiello")
        self.assertEqual(result[0]["event_title"],"Il barbiere di Siviglia")
        del event["workPerformed"]
        result=parse_event_facts('<script type="application/ld+json">'+
                                 json.dumps(event)+'</script>')
        self.assertNotIn("composer",result[0])

    def test_verified_scala_work_parser_produces_review_only_date(self):
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        url="https://www.teatroallascala.org/it/stagione/2026-2027/opera/macbeth.html"
        html="<h1>Macbeth Giuseppe Verdi</h1><p>5 febbraio 2027 ore 20:00</p>"
        rows=parse_known_opera_detail("scala-season-2026-27",url,html,registry)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["composer"],"Giuseppe Verdi")
        self.assertEqual(rows[0]["venue"],"Teatro alla Scala")
        self.assertEqual(rows[0]["date"],"2027-02-05")
        self.assertIn("+01:00",rows[0]["starts_at"])

    def test_verified_arena_known_work_and_unknown_rejected(self):
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        url="https://www.arena.it/arena-opera-festival/carmen/"
        html="<h1>Carmen Georges Bizet</h1><h2>Prossimi spettacoli</h2><p>12 giugno 2027 ore 21:00</p>"
        rows=parse_known_opera_detail("arena-festival-2027",url,html,registry)
        self.assertEqual(len(rows),1)
        self.assertIn("+02:00",rows[0]["starts_at"])
        unknown="https://www.teatroallascala.org/it/stagione/2026-2027/opera/unknown-opera.html"
        self.assertEqual(parse_known_opera_detail("scala-season-2026-27",unknown,html,registry),[])

    def test_incorrect_composer_does_not_produce_evidence(self):
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        url="https://www.teatroallascala.org/it/stagione/2026-2027/opera/macbeth.html"
        with self.assertRaises(ValueError):
            parse_known_opera_detail("scala-season-2026-27",url,
                                    "<h1>Macbeth by another composer</h1>"
                                    "<p>5 febbraio 2027 ore 20:00</p>",registry)

    def test_publishable_known_works_are_scanned_before_unknown_titles(self):
        candidates={"schema_version":1,"candidates":[]}
        for i in range(25):
            candidates["candidates"].append({
                "id":f"candidate-{i:03d}","source_key":"scala-season-2026-27",
                "official_url":f"https://www.teatroallascala.org/it/stagione/2026-2027/opera/unknown-{i}.html",
                "status":"needs_review"})
        candidates["candidates"].append({
            "id":"candidate-z-macbeth","source_key":"scala-season-2026-27",
            "official_url":"https://www.teatroallascala.org/it/stagione/2026-2027/opera/macbeth.html",
            "status":"needs_review"})
        chosen=selected_candidates(candidates,today=date(2026,11,20))
        self.assertEqual(len(chosen),24)
        self.assertEqual(chosen[0]["id"],"candidate-z-macbeth")

    def test_untested_new_opera_requires_authority_and_official_composer(self):
        item={"id":"oa-index-new-anna","source_key":"scala-season-2026-27",
              "official_url":"https://www.teatroallascala.org/it/stagione/2026-2027/opera/anna-bolena.html"}
        intelligence={"schema_version":1,"works":[{
            "candidate_id":item["id"],"source_key":item["source_key"],
            "source_url":item["official_url"],"title":"Anna Bolena",
            "composer":"Gaetano Donizetti","synopsis":
            "La protagonista affronta intrighi di corte, rapporti difficili "
            "e le conseguenze di decisioni che segnano il suo destino."
        }]}
        html="<h1>Anna Bolena Gaetano Donizetti</h1><p>2 giugno 2027 ore 20:00</p>"
        facts=parse_authoritative_new_work_detail(item,html,intelligence)
        self.assertEqual(facts[0]["composer"],"Gaetano Donizetti")
        self.assertIn("+02:00",facts[0]["starts_at"])
        with self.assertRaises(ValueError):
            parse_authoritative_new_work_detail(
                item,"<h1>Anna Bolena altro autore</h1><p>2 giugno 2027 ore 20:00</p>",
                intelligence)

    def test_three_national_official_pages_with_canonical_identity(self):
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        cases=[
            ("fenice-opera-2026-27",
             "https://www.teatrolafenice.it/event/jenufa/",
             "<h1>Jenůfa</h1><p>Leoš Janáček</p><p>Teatro La Fenice</p><p>Seleziona una data:</p>"
             "<a>venerdì 12 Marzo 2027 19:00 ACQUISTA</a>",
             "Jenůfa","Leoš Janáček","2027-03-12"),
            ("parma-opera-2027",
             "https://teatroregioparma.it/spettacolo/madama-butterfly/",
             "<h1>Madama Butterfly</h1><p>Giacomo Puccini</p><p>19 feb 2027</p>"
             "<p>Musica Giacomo Puccini</p><h2>Teatro Regio di Parma</h2>"
             "<p>ven 19 feb</p><p>20:00</p><p>TURNO A</p>",
             "Madama Butterfly","Giacomo Puccini","2027-02-19"),
            ("massimo-season-2026-27",
             "https://www.teatromassimo.it/event/macbeth/",
             "<h2>Date</h2><p>5 Febbraio</p><p>19:00</p>"
             "<p>7 Febbraio</p><p>17:30</p><h2>Lo spettacolo</h2>"
             "<p>5, 7 febbraio 2027 | Sala Grande</p>"
             "<h1>Macbeth</h1><p>Musiche di Giuseppe Verdi</p>",
             "Macbeth","Giuseppe Verdi","2027-02-05"),
        ]
        for key,url,html,title,composer,day in cases:
            with self.subTest(key=key):
                facts=parse_known_opera_detail(key,url,html,registry)
                self.assertTrue(facts)
                self.assertEqual(facts[0]["date"],day)
                self.assertEqual(facts[0]["event_title"],title)
                self.assertEqual(facts[0]["composer"],composer)
                self.assertTrue(facts[0]["starts_at"].endswith(("+01:00","+02:00")))

    def test_rotation_eventually_visits_every_candidate_even_at_budget_multiple(self):
        rows=[]
        for i in range(20):
            rows.append({"id":f"unknown-{i:03d}","source_key":"scala-season-2026-27",
                "official_url":f"https://www.teatroallascala.org/it/stagione/2026-2027/opera/unknown-{i}.html",
                "status":"needs_review"})
        candidates={"schema_version":1,"candidates":rows}
        observed=set()
        for offset in range(30):
            day=date.fromordinal(date(2026,11,20).toordinal()+offset)
            observed.update(x["id"] for x in selected_candidates(candidates,today=day))
        self.assertEqual(observed,{x["id"] for x in rows})

    def test_reserved_slots_for_unknown_opera_with_large_known_work_queue(self):
        rows=[]
        for i in range(20):
            rows.append({"id":f"known-{i:03d}","source_key":"scala-season-2026-27",
                "official_url":"https://www.teatroallascala.org/it/stagione/2026-2027/opera/macbeth.html",
                "status":"needs_review"})
        for i in range(12):
            rows.append({"id":f"unknown-{i:03d}","source_key":"scala-season-2026-27",
                "official_url":f"https://www.teatroallascala.org/it/stagione/2026-2027/opera/unknown-{i}.html",
                "status":"needs_review"})
        candidates={"schema_version":1,"candidates":rows}
        seen=set()
        for offset in range(30):
            day=date.fromordinal(date(2026,11,20).toordinal()+offset)
            chosen=selected_candidates(candidates,today=day)
            self.assertEqual(len(chosen),24)
            self.assertGreaterEqual(len([x for x in chosen if x["id"].startswith("unknown")]),4)
            seen.update(x["id"] for x in chosen)
        self.assertEqual(seen,{x["id"] for x in rows})

    def test_preverified_rigoletto_receives_daily_candidate_priority(self):
        candidates={"schema_version":1,"candidates":[]}
        for i in range(24):
            candidates["candidates"].append({
                "id":f"other-{i:02d}","source_key":"parma-opera-2027",
                "official_url":f"https://teatroregioparma.it/spettacolo/unknown-{i}/",
                "status":"needs_review"})
        candidates["candidates"].append({
            "id":"verified-rigoletto","source_key":"parma-opera-2027",
            "official_url":"https://teatroregioparma.it/spettacolo/rigoletto/",
            "status":"needs_review"})
        batch=selected_candidates(candidates,today=date(2026,11,20))
        self.assertIn("verified-rigoletto",{x["id"] for x in batch})
        self.assertEqual(len(batch),24)

    def test_rome_official_seed_is_selected_before_historical_backlog(self):
        # A first-party opera with completed, source-bound editorial facts
        # must be read even when its composition is not yet a site work.
        rows=[{
            "id":f"rome-historical-{i:02d}",
            "source_key":"opera-roma-season-2026-27",
            "official_url":f"https://www.operaroma.it/spettacoli/old-{i}/",
            "status":"needs_review"} for i in range(24)]
        rows.append({
            "id":"rome-code-unknown",
            "source_key":"opera-roma-season-2026-27",
            "official_url":"https://www.operaroma.it/spettacoli/code-unknown/",
            "status":"needs_review"})
        picked=selected_candidates(
            {"schema_version":1,"candidates":rows},today=date(2026,11,21))
        self.assertEqual(len(picked),MAX_PER_SOURCE)
        self.assertEqual(picked[0]["id"],"rome-code-unknown")
        self.assertEqual(len({x["id"] for x in picked}),MAX_PER_SOURCE)

    def test_daily_budget_covers_each_of_five_active_theatres(self):
        bases={
            "scala-season-2026-27":"https://www.teatroallascala.org/it/stagione/2026-2027/opera/unknown-{}.html",
            "arena-festival-2027":"https://www.arena.it/arena-opera-festival/unknown-{}/",
            "fenice-opera-2026-27":"https://www.teatrolafenice.it/event/unknown-{}/",
            "parma-opera-2027":"https://teatroregioparma.it/spettacolo/unknown-{}/",
            "massimo-season-2026-27":"https://www.teatromassimo.it/event/unknown-{}/"}
        rows=[{"id":f"{key}-{index}","source_key":key,
               "official_url":template.format(index),"status":"needs_review"}
              for key,template in bases.items() for index in range(15)]
        candidates={"schema_version":1,"candidates":rows}
        chosen=selected_candidates(candidates,today=date(2026,11,20))
        self.assertEqual(len(chosen),60)
        self.assertEqual({x["source_key"] for x in chosen},set(bases))
        visited=set()
        for offset in range(80):
            day=date.fromordinal(date(2026,11,20).toordinal()+offset)
            visited.update(x["id"] for x in selected_candidates(candidates,today=day))
        self.assertEqual(visited,{x["id"] for x in rows})

    def test_full_current_queue_covered_without_daily_ten_page_artificial_limit(self):
        self.assertEqual(MAX_PAGES,60)
        self.assertEqual(MAX_PER_SOURCE,24)
        bases={
            "scala-season-2026-27":"https://www.teatroallascala.org/it/stagione/2026-2027/opera/unknown-{}.html",
            "arena-festival-2027":"https://www.arena.it/arena-opera-festival/unknown-{}/",
            "fenice-opera-2026-27":"https://www.teatrolafenice.it/event/unknown-{}/",
            "parma-opera-2027":"https://teatroregioparma.it/spettacolo/unknown-{}/",
            "massimo-season-2026-27":"https://www.teatromassimo.it/event/unknown-{}/",
        }
        sizes=[10,2,7,12,23]  # 54 pending productions observed in live catalog
        rows=[{"id":f"{key}-{i}","source_key":key,
               "official_url":url.format(i),"status":"needs_review"}
              for (key,url),size in zip(bases.items(),sizes) for i in range(size)]
        chosen=selected_candidates({"schema_version":1,"candidates":rows},
                                  today=date(2026,11,20))
        self.assertEqual(len(chosen),54)
        self.assertEqual(len({x["id"] for x in chosen}),54)
        from collections import Counter
        by_source=Counter(x["source_key"] for x in chosen)
        self.assertEqual(max(by_source.values()),23)

    def test_network_pacing_is_injected_and_testable_without_waiting(self):
        rows=[]
        for i in range(3):
            rows.append({"id":f"pacing-{i}",
                "source_key":"fenice-opera-2026-27",
                "official_url":f"https://www.teatrolafenice.it/event/example-{i}/",
                "status":"needs_review"})
        waits=[]
        def fake(db,*,source_id,url,network_enabled):
            return FetchResult(url,"<p>no supported events</p>","a"*64,26)
        _,health=collect({"schema_version":1,"candidates":rows},self.empty,
                         network_enabled=True,fetcher=fake,
                         today=date(2026,11,20),pause=waits.append)
        self.assertEqual(len(health),3)
        self.assertEqual(len(waits),2)
        self.assertTrue(all(0<x<=1 for x in waits))

    def test_structured_dates_and_explicit_timezone_only(self):
        html='<script type="application/ld+json">'+json.dumps({"@graph":[
            {"@type":"MusicEvent","name":"Anna Bolena",
             "startDate":"2027-05-02T20:00:00+02:00",
             "location":{"@type":"Place","name":"Teatro alla Scala"}},
            {"@type":"Event","name":"Preview","startDate":"2027-05-03"},
            {"@type":"Event","name":"Untrusted","startDate":"2027-05-04T20:00:00"}
        ]})+'</script>'
        events=parse_event_facts(html)
        self.assertEqual(len(events),2)
        self.assertEqual(events[0]["date"],"2027-05-02")
        self.assertIn("+02:00",events[0]["starts_at"])
        self.assertIsNone(events[1]["starts_at"])
    def test_scripts_not_events_are_ignored(self):
        self.assertEqual(parse_event_facts('<script type="application/ld+json">'+
            '{"@type":"Article","name":"Opere","datePublished":"2027-01-01"}'+
            '</script>'),[])
    def test_selection_only_review_and_exact_official_domains(self):
        chosen=selected_candidates(self.candidates,today=date(2026,11,20))
        self.assertEqual([x["id"] for x in chosen],["candidate-a"])
    def test_collect_captures_title_specific_image_from_verified_official_page(self):
        url=self.candidates["candidates"][0]["official_url"]
        html=('<h1>Anna Bolena</h1>'
              '<meta property="og:image" content="/static/upload/ann/anna-bolena.jpg">'
              '<script type="application/ld+json">'+json.dumps({
                  "@type":"MusicEvent","name":"Anna Bolena",
                  "startDate":"2027-05-02T20:00:00+02:00",
                  "location":{"@type":"Place","name":"Teatro alla Scala"},
                  "workPerformed":{"@type":"MusicComposition",
                       "composer":{"name":"Gaetano Donizetti"}}})+'</script>')
        def mock(db,*,source_id,url,network_enabled):
            return FetchResult(url,html,"a"*64,len(html))
        evidence,health=collect(self.candidates,self.empty,network_enabled=True,
                                fetcher=mock,today=date(2026,11,20))
        record=evidence["evidence"][0]
        proof=record["poster_evidence"]
        self.assertEqual(proof["kind"],"official_production_image")
        self.assertEqual(proof["source_url"],url)
        self.assertIn("anna-bolena.jpg",proof["image_url"])

    def test_success_preserves_evidence_and_does_not_create_recite(self):
        html='<script type="application/ld+json">'+json.dumps({
            "@type":"MusicEvent","name":"Anna Bolena",
            "startDate":"2027-05-02T20:00:00+02:00"})+'</script>'
        def fake(db,*,source_id,url,network_enabled):
            return FetchResult(url,html,"a"*64,len(html))
        report,health=collect(self.candidates,self.empty,
                              network_enabled=True,fetcher=fake,today=date(2026,11,20))
        self.assertEqual(health[0]["outcome"],"facts_found")
        self.assertEqual(len(report["evidence"]),1)
        self.assertEqual(report["evidence"][0]["status"],"needs_editorial_review")
        self.assertEqual(len(report["evidence"][0]["event_facts"]),1)
    def test_failure_health_explains_canonical_and_authority_parser_rejections(self):
        html="<h1>Unknown production</h1><p>Dates not provided</p>"
        def fake(db,*,source_id,url,network_enabled):
            return FetchResult(url,html,"b"*64,len(html))
        result,health=collect(self.candidates,self.empty,
                              network_enabled=True,fetcher=fake,today=date(2026,11,20))
        self.assertEqual(result,self.empty)
        self.assertEqual(health[0]["reason"],"no_verified_showtimes")
        self.assertEqual(len(health[0]["diagnostic"]),4)
        self.assertTrue(health[0]["diagnostic"][0].startswith("canonical_work:"))
        self.assertTrue(health[0]["diagnostic"][1].startswith("authority_work:"))
        self.assertTrue(health[0]["diagnostic"][2].startswith("official_composer_credit:"))
        self.assertTrue(health[0]["diagnostic"][3].startswith("schema_event:"))
        self.assertNotIn(html,json.dumps(health))

    def test_robots_failure_preserves_last_evidence(self):
        past={"schema_version":1,"evidence":[{
            "candidate_id":"candidate-a","event_facts":[{"date":"2027-05-02"}]}]}
        def denied(*args,**kwargs):raise FetchUnavailable("robots denied")
        result,health=collect(self.candidates,past,
                              network_enabled=True,fetcher=denied,today=date(2026,11,20))
        self.assertEqual(result,past)
        self.assertEqual(health[0]["outcome"],"unavailable_or_unstructured")
    def test_without_network_does_not_fetch(self):
        def forbidden(*a,**k):raise AssertionError("unexpected network")
        result,health=collect(self.candidates,self.empty,network_enabled=False,
                              fetcher=forbidden,today=date(2026,11,20))
        self.assertEqual(result,self.empty)
        self.assertEqual(health[0]["reason"],"AccessDenied")

if __name__=="__main__":
    unittest.main()
