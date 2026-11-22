"""Season indexes must discover only exact official URLs and preserve canon."""
import copy
import json
import unittest
from opera_atlas.controlled_fetch import FetchResult,FetchUnavailable
from scripts.discover_season_indexes import CONFIG,extract,scan,classify,eligible,reviewed_source_urls

class NationalIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads(CONFIG.read_text(encoding="utf-8"))
    def test_rovigo_parser_reports_precise_safe_diagnostics(self):
        source=next(x for x in self.config["sources"]
                    if x["key"]=="rovigo-sociale-opera-2026-27")
        cases=(
            ("<h1>Unknown venue</h1><p>Stagione 2026/27 Pagliacci</p>",
             "rovigo_venue_missing"),
            ("<h1>Teatro Sociale di Rovigo</h1><p>Pagliacci</p>",
             "rovigo_season_missing"),
            ("<h1>Teatro Sociale di Rovigo - stagione 2026/27</h1><p>Musica</p>",
             "rovigo_opera_titles_missing"),
        )
        for html,reason in cases:
            with self.subTest(reason=reason):
                config=copy.deepcopy(self.config)
                for item in config["sources"]:
                    if item["key"]!=source["key"]:
                        item["access_status"]="blocked"
                def fake(db,*,source_id,url,network_enabled):
                    return FetchResult(url,html,"a"*64,len(html))
                _,rows=scan(config,{"schema_version":1,"candidates":[]},
                            fetcher=fake,network_enabled=True)
                actual=next(x for x in rows if x["key"]==source["key"])
                self.assertEqual(actual["diagnostic"],reason)
                self.assertNotIn("<",actual["diagnostic"])

    def test_scala_only_opera_detail_links(self):
        url="https://www.teatroallascala.org/it/stagione/2026-2027/index.html"
        html='<a href="/it/stagione/2026-2027/opera/otello.html">Otello</a>'+\
            '<a href="/it/stagione/2026-2027/opera/don-giovanni.html">Don Giovanni</a>'+\
            '<a href="/it/stagione/2026-2027/opera/anna-bolena.html">Anna Bolena</a>'+\
            '<a href="/it/stagione/2026-2027/balletto/giselle.html">Giselle</a>'+\
            '<a href="https://external.example/it/stagione/2026-2027/opera/fake.html">Fake</a>'
        links=extract("scala-season-2026-27",url,html,3)
        self.assertEqual(len(links),3)
        self.assertTrue(all("/opera/" in x for x in links))
    def test_arena_and_fenice_index_filter(self):
        arena="https://www.arena.it/arena-opera-festival/spettacoli/"
        a=extract("arena-festival-2027",arena,
                  '<a href="/arena-opera-festival/nabucco/">Nabucco</a>'
                  '<a href="/arena-opera-festival/carmen/">Carmen</a>'
                  '<a href="/arena-opera-festival/calendario/">Calendario</a>',2)
        self.assertEqual(len(a),2)
        fenice="https://www.teatrolafenice.it/event-category/opera-2026-27/"
        f=extract("fenice-opera-2026-27",fenice,
                  '<a href="/event/jenufa/">Jenufa</a>'
                  '<a href="/event/fedora/">Fedora</a>'
                  '<a href="/news/other/">News</a>',2)
        self.assertEqual(len(f),2)
    def test_parma_site_specific_otello_is_not_verdis_canonical_opera(self):
        source="parma-opera-2027"
        special="https://teatroregioparma.it/spettacolo/otello-gamification/"
        self.assertFalse(eligible(source,special))
        self.assertEqual(classify(source,special,set()),"excluded_nonopera")
        self.assertEqual(classify(source,special,{special}),"excluded_nonopera")
        # Sollima's commissioned family opera must NOT be classified as
        # non-opera; two slots on each day are an acquisition problem.
        sollima=("https://teatroregioparma.it/spettacolo/"
                 "piccolo-orso-e-la-montagna-di-ghiaccio/")
        self.assertTrue(eligible(source,sollima))
        self.assertEqual(classify(source,sollima,set()),"needs_review")
        self.assertTrue(eligible(source,
                        "https://teatroregioparma.it/spettacolo/otello/"))

    def test_parma_and_palermo_official_links_without_nonopera(self):
        parma="https://teatroregioparma.it/categoria-spettacoli/opera/"
        p=extract("parma-opera-2027",parma,
                  '<nav><a href="/spettacolo/false/">Off page</a></nav>'
                  '<h1>Opera</h1>'
                  '<a href="/spettacolo/boris-godunov/">Boris Godunov</a>'
                  '<a href="/spettacolo/rigoletto/">Rigoletto</a>'
                  '<a href="/spettacolo/madama-butterfly/">Madama Butterfly</a>'
                  '<a href="/spettacolo/prove-under30/">Prove Under30</a>'
                  '<footer><a href="/spettacolo/not-an-opera/">Footer</a></footer>',3)
        self.assertEqual(len(p),3)
        massimo="https://www.teatromassimo.it/la-stagione-2026-27/"
        m=extract("massimo-season-2026-27",massimo,
                  '<h2>CALENDARIO OPERE E BALLETTI 2026-27</h2>'
                  +''.join('<a href="/event/'+slug+'/">'+slug+'</a>'
                          for slug in ("samson-et-dalila","macbeth",
                                       "lucia-di-lammermoor-2","tosca-2",
                                       "falstaff","ernani","biancaneve",
                                       "sylvia"))
                  +'<h2>CALENDARIO CONCERTI 2026-27</h2>'
                  +'<a href="/event/concerto-non-opera/">Concerto</a>',6)
        self.assertEqual(len(m),6)
        self.assertTrue(all("biancaneve" not in u for u in m))
        self.assertTrue(all("sylvia" not in u for u in m))
        self.assertTrue(all("concerto-non-opera" not in u for u in m))
        self.assertTrue(all("false" not in u for u in p))

    def test_carlo_felice_index_filters_nonopera_and_external_links(self):
        url="https://www.carlofelice.it/rassegna-stagione-opera-danza-musical-2026-27/"
        slugs=("le-nozze-di-figaro","i-capuleti-e-i-montecchi",
               "pagliacci","litaliana-in-algeri","turandot",
               "evgenij-onegin","nabucco","deledda","giselle",
               "lo-schiaccianoci","il-lago-dei-cigni",
               "sergio-bernal-dance-company","the-phantom-of-the-opera")
        html="".join('<a href="/spettacolo/'+slug+'/">Dettaglio</a>' for slug in slugs)
        html+='<a href="https://other.example/spettacolo/false/">External</a>'
        urls=extract("carlo-felice-season-2026-27",url,html,7)
        self.assertEqual(len(urls),7)
        self.assertFalse(any("giselle" in x or "deledda" in x for x in urls))

    def test_donizetti_opera_index_scoped_to_three_operas(self):
        url="https://www.donizettiopera.org/it/opere-2026/"
        html='<nav><a href="/it/evento/unrelated/">Menu</a></nav><h1>Opere 2026</h1>'
        html+=''.join('<a href="/it/evento/'+slug+'/">Opera</a>' for slug in
                      ("l-esule-di-roma","alahor-in-granata/2026-11-14",
                       "le-convenienze-ed-inconvenienze-teatrali"))
        html+='<a href="/it/evento/the-donizetti-brunch/2026-11-29/">Brunch</a>'
        html+='<footer><a href="/it/evento/another/">Footer</a></footer>'
        urls=extract("donizetti-opera-2026",url,html,3)
        self.assertEqual(len(urls),3)
        self.assertFalse(any("brunch" in x or "another" in x for x in urls))
        self.assertTrue(any(x.endswith("/alahor-in-granata/2026-11-14/") for x in urls))
        self.assertFalse(eligible("donizetti-opera-2026",
                     "https://www.donizettiopera.org/it/evento/alahor-in-granata/2025-11-14/"))
        self.assertFalse(eligible("donizetti-opera-2026",
                     "https://www.donizettiopera.org/it/evento/the-donizetti-brunch/2026-11-29/"))

    def test_teatro_grande_index_scoped_to_opera_not_concerts(self):
        url="https://teatrogrande.it/it"
        html='<h2>Opera e Balletto</h2>'
        html+='<a href="/it/stagioni/2026/l-italiana-in-algeri">Italiana</a>'
        html+='<a href="/it/stagioni/2026/cavalleria-rusticana-pagliacci">Dittico</a>'
        html+='<h2>Concerti</h2>'
        html+='<a href="/it/stagioni/2026/brahms-e-kancheli">Concerto</a>'
        urls=extract("teatro-grande-opera-2026",url,html,2)
        self.assertEqual(len(urls),2)
        self.assertFalse(any("brahms" in x for x in urls))

    def test_all_forty_eight_indexes_are_explicitly_configured(self):
        self.assertEqual({x["key"] for x in self.config["sources"]},{
            "sassari-de-carolis-opera-2026", "messina-vittorio-opera-2026-27", "lecce-apollo-pinocchio-2026", "lecce-politeama-opera-2026", "lecce-provincia-politeama-2026", "spoleto-tls-lirica-2026","chieti-marrucino-lirica-2026", "rovigo-regione-programma-2026-27", "rovigo-sociale-opera-2026-27", "padova-verdi-opera-2026", "treviso-del-monaco-opera-2026-27", "ravenna-alighieri-cherubini-2027", "coccia-novara-opera-2027", "filarmonico-verona-opera-2027", "pisa-verdi-opera-2026-27", "salerno-verdi-opera-2026", "macerata-festival-2027", "scala-season-2026-27", "arena-festival-2027",
            "fenice-opera-2026-27","parma-opera-2027",
            "massimo-season-2026-27","carlo-felice-season-2026-27",
            "donizetti-opera-2026","teatro-grande-opera-2026",
            "maggio-fiorentino-calendar-2027","opera-roma-season-2026-27",
            "petruzzelli-opera-2026","petruzzelli-opera-2027",
            "bologna-comunale-opera-2026","bologna-comunale-opera-2027",
            "verdi-trieste-season-2026-27", "lirico-cagliari-opera-2027", "bellini-catania-opera-2026-27","modena-opera-2026-27","modena-teatro-opera-2026-27","giglio-lucca-opera-2026-27","piacenza-opera-2026-27","reggio-valli-opera-2026-27", "ferrara-macbeth-opera-2026-27", "ferrara-barbiere-opera-2026-27", "ferrara-dido-opera-2026-27", "ferrara-clemenza-opera-2026-27", "ferrara-boccanegra-opera-2026-27", "goldoni-livorno-dido-2026-27", "goldoni-livorno-otello-2026-27", "goldoni-livorno-elisir-2026-27", "jesi-trittico-opera-2026", "jesi-don-pasquale-opera-2026", "jesi-esecuzione-opera-2026", "jesi-nabucco-opera-2026", "ancona-elisir-opera-2026", "ancona-cavalleria-program-2026"})

    def test_incomplete_index_is_rejected(self):
        with self.assertRaises(ValueError):
            extract("scala-season-2026-27",
                    "https://www.teatroallascala.org/it/stagione/2026-2027/index.html",
                    "<a href='/it/stagione/2026-2027/opera/otello.html'>Otello</a>",3)
    def test_scans_are_idempotent_and_never_publish_events(self):
        htmls={
          "scala-season-2026-27":'<a href="/it/stagione/2026-2027/opera/otello.html">Otello</a>'
            '<a href="/it/stagione/2026-2027/opera/don-giovanni.html">Don Giovanni</a>'
            '<a href="/it/stagione/2026-2027/opera/anna-bolena.html">Anna Bolena</a>',
          "arena-festival-2027":'<a href="/arena-opera-festival/nabucco/">Nabucco</a>'
            '<a href="/arena-opera-festival/carmen/">Carmen</a>',
          "fenice-opera-2026-27":'<a href="/event/jenufa/">Jenufa</a><a href="/event/fedora/">Fedora</a>'
        }
        def fake(db,*,source_id,url,network_enabled):
            key=next(x["key"] for x in self.config["sources"] if x["url"]==url)
            html=htmls[key]
            return FetchResult(url,html,"a"*64,len(html))
        empty={"schema_version":1,"candidates":[]}
        subset=copy.deepcopy(self.config)
        for row in subset["sources"][3:]:row["access_status"]="blocked"
        first,status=scan(subset,empty,fetcher=fake,network_enabled=True,
                          now="2026-11-20T20:00:00+00:00")
        self.assertEqual(len(first["candidates"]),7)
        # The real catalogue grows autonomously between workflow stages.
        # Do not assert fixed old totals for titles that may now be imported.
        verified=reviewed_source_urls()
        expected={x["official_url"]:classify(x["source_key"],x["official_url"],verified)
                  for x in first["candidates"]}
        self.assertEqual({x["official_url"]:x["status"] for x in first["candidates"]},
                         expected)
        self.assertTrue(all(x["status"] in ("needs_review","already_catalogued")
                            for x in first["candidates"]))
        self.assertTrue(all("date" not in x and "composer" not in x for x in first["candidates"]))
        second,_=scan(subset,first,fetcher=fake,network_enabled=True,
                       now="2026-11-20T20:00:00+00:00")
        self.assertEqual(second,first)
        self.assertEqual([x["status"] for x in status[:3]],["success"]*3)
        self.assertEqual([x["status"] for x in status[3:]],
                         ["blocked"]*(len(self.config["sources"])-3))
    def test_first_live_scan_support_pages_are_not_opera(self):
        for suffix in ("regolamento","preparati-allopera",
                       "spettacoli-prossima-stagione","roberto-bolle-friends",
                       "carmina-burana","artisti","viva-vivaldi"):
            url="https://www.arena.it/arena-opera-festival/"+suffix+"/"
            self.assertFalse(eligible("arena-festival-2027",url),url)
            self.assertEqual(classify("arena-festival-2027",url,set()),
                             "excluded_nonopera")
        for slug in ("piccolo-orso-e-la-montagna-di-ghiaccio",
                     "percorsi-della-danza-cinema-e-danza-il-musical",
                     "concertoriccardofrizzasinopoliperosi"):
            url="https://www.teatrolafenice.it/event/"+slug+"/"
            self.assertFalse(eligible("fenice-opera-2026-27",url))
            self.assertEqual(classify("fenice-opera-2026-27",url,set()),
                             "excluded_nonopera")

    def test_verified_production_is_not_a_new_candidate(self):
        known=reviewed_source_urls()
        url="https://www.teatroallascala.org/it/stagione/2026-2027/opera/otello.html"
        self.assertIn(url,known)
        self.assertEqual(classify("scala-season-2026-27",url,known),
                         "already_catalogued")
        unknown="https://www.teatroallascala.org/it/stagione/2026-2027/opera/fixture-never-observed.html"
        self.assertEqual(classify("scala-season-2026-27",unknown,known),
                         "needs_review")

    def test_historical_live_links_are_classified_without_deletion(self):
        existing={"schema_version":1,"candidates":[
            {"id":"old-arena","source_key":"arena-festival-2027",
             "official_url":"https://www.arena.it/arena-opera-festival/regolamento/",
             "status":"needs_review","first_seen":"old","last_seen":"old"},
            {"id":"old-scala","source_key":"scala-season-2026-27",
             "official_url":"https://www.teatroallascala.org/it/stagione/2026-2027/opera/otello.html",
             "status":"needs_review","first_seen":"old","last_seen":"old"}
        ]}
        config=copy.deepcopy(self.config)
        for item in config["sources"]:
            item["access_status"]="blocked"
        out,_=scan(config,existing,network_enabled=False,now="2026-11-20T21:00:00+00:00")
        self.assertEqual({x["id"]:x["status"] for x in out["candidates"]},
                         {"old-arena":"excluded_nonopera","old-scala":"already_catalogued"})
        self.assertTrue(all(x["first_seen"]=="old" for x in out["candidates"]))

    def test_status_has_actionable_index_diagnostic_not_opaque_valueerror(self):
        source=copy.deepcopy(self.config)
        for item in source["sources"][1:]:item["access_status"]="blocked"
        def incomplete(*args,**kwargs):
            return FetchResult(kwargs["url"],"<html><h1>unrelated</h1></html>","a"*64,35)
        _,health=scan(source,{"schema_version":1,"candidates":[]},
                       fetcher=incomplete,network_enabled=True)
        failure=health[0]
        self.assertEqual(failure["status"],"unavailable_or_invalid")
        self.assertEqual(failure["reason"],"ValueError")
        self.assertEqual(failure["diagnostic"],"index_incomplete_or_markup_changed")
        self.assertEqual(failure["required_links"],3)

    def test_rome_secondary_page_is_safe_partial_fallback(self):
        subset=copy.deepcopy(self.config)
        for row in subset["sources"]:
            if row["key"]!="opera-roma-season-2026-27":
                row["access_status"]="blocked"
        primary=next(x["url"] for x in subset["sources"]
                     if x["key"]=="opera-roma-season-2026-27")
        secondary=primary.rstrip("/")+"/page/2/"
        attempts=[]
        def first_html_unavailable(db,*,source_id,url,network_enabled):
            attempts.append(url)
            if url==primary:raise FetchUnavailable("page unavailable")
            if url==secondary:
                body='<a href="/spettacoli/the-rakes-progress/">Opera</a>'
                return FetchResult(url,body,"a"*64,len(body))
            raise AssertionError("unexpected external URL")
        data,health=scan(subset,{"schema_version":1,"candidates":[]},
                         fetcher=first_html_unavailable,network_enabled=True)
        roma=next(x for x in health if x["key"]=="opera-roma-season-2026-27")
        self.assertEqual(attempts,[primary,secondary])
        self.assertEqual(roma["status"],"partial_pagination")
        self.assertEqual(roma["diagnostic"],"primary_official_html_unavailable")
        self.assertFalse(roma["pagination_complete"])
        self.assertEqual(roma["links"],1)
        self.assertEqual(data["candidates"][0]["official_url"],
                         "https://www.operaroma.it/spettacoli/the-rakes-progress/")

    def test_rome_never_fails_over_when_robots_unavailable(self):
        subset=copy.deepcopy(self.config)
        for row in subset["sources"]:
            if row["key"]!="opera-roma-season-2026-27":
                row["access_status"]="blocked"
        called=[]
        def failed_robots(db,*,source_id,url,network_enabled):
            called.append(url)
            raise FetchUnavailable("robots.txt unavailable")
        data,health=scan(subset,{"schema_version":1,"candidates":[]},
                         fetcher=failed_robots,network_enabled=True)
        primary=next(x["url"] for x in subset["sources"]
                     if x["key"]=="opera-roma-season-2026-27")
        self.assertEqual(called,[primary])
        self.assertFalse(data["candidates"])
        roma=next(x for x in health if x["key"]=="opera-roma-season-2026-27")
        self.assertEqual(roma["diagnostic"],"official_robots_unavailable_or_invalid")
        self.assertEqual(roma["links"],0)

    def test_rome_retrieval_reports_fail_closed_fetch_stage(self):
        subset=copy.deepcopy(self.config)
        for row in subset["sources"]:
            if row["key"]!="opera-roma-season-2026-27":
                row["access_status"]="blocked"
        cases=[
            ("robots.txt unavailable","official_robots_unavailable_or_invalid"),
            ("robots.txt malformed or no user-agent directives",
             "official_robots_unavailable_or_invalid"),
            ("page unavailable","official_html_unavailable_or_invalid"),
            ("not an HTML page","official_html_unavailable_or_invalid"),
            ("unknown transient","official_source_unavailable"),
        ]
        for cause,expected in cases:
            with self.subTest(cause=cause):
                def fail(*args,**kwargs):
                    raise FetchUnavailable(cause)
                data,health=scan(subset,{"schema_version":1,"candidates":[]},
                                 fetcher=fail,network_enabled=True)
                self.assertEqual(data["candidates"],[])
                roma=next(x for x in health if x["key"]=="opera-roma-season-2026-27")
                self.assertEqual(roma["diagnostic"],expected)
                self.assertEqual(roma["links"],0)
                self.assertNotIn(cause,repr(roma))

    def test_last_good_scan_survives_failure_without_false_success(self):
        from scripts.discover_season_indexes import source_health_history
        past={"schema_version":1,"checked_at":"2026-11-21T08:00:00+00:00",
              "sources":[{"key":"donizetti-opera-2026","status":"success","links":3}]}
        failures=[{"key":"donizetti-opera-2026","status":"unavailable_or_invalid",
                   "reason":"ValueError","diagnostic":"index_incomplete_or_markup_changed",
                   "required_links":3,"links":0}]
        now="2026-11-21T12:30:00+00:00"
        rows=source_health_history(failures,past,checked_at=now)
        self.assertFalse(rows[0]["current_scan_verified"])
        self.assertEqual(rows[0]["last_attempt_at"],now)
        self.assertEqual(rows[0]["last_success_at"],past["checked_at"])
        self.assertEqual(rows[0]["last_successful_links"],3)
        recovered=source_health_history([{"key":"donizetti-opera-2026",
                            "status":"success","links":4,"required_links":3}],
                            {"schema_version":1,"sources":rows},checked_at=now)
        self.assertTrue(recovered[0]["current_scan_verified"])
        self.assertEqual(recovered[0]["last_successful_links"],4)
        self.assertEqual(recovered[0]["last_success_at"],now)
        unknown=source_health_history(failures,{},checked_at=now)
        self.assertIsNone(unknown[0]["last_success_at"])
        self.assertIsNone(unknown[0]["last_successful_links"])

    def test_access_and_robots_failure_preserve_last_good(self):
        source=copy.deepcopy(self.config)
        source["sources"][0]["access_status"]="blocked"
        def deny(*args,**kwargs):raise FetchUnavailable("robots unavailable")
        existing={"schema_version":1,"candidates":[]}
        data,health=scan(source,existing,fetcher=deny,network_enabled=True,
                         now="2026-11-20T20:00:00+00:00")
        self.assertEqual(data,existing)
        self.assertEqual(health[0]["status"],"blocked")
        self.assertEqual(health[1]["status"],"unavailable_or_invalid")

if __name__=="__main__":
    unittest.main()
