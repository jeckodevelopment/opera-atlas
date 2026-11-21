"""Official Rome opera detail must produce exact date/clock and canonical ID."""
import json
import copy
import unittest
from datetime import date
from opera_atlas.controlled_fetch import FetchResult,FetchUnavailable

from opera_atlas.roma_detail_parser import parse_roma_detail,parse_roma_credited_detail
from scripts.collect_candidate_details import parse_known_opera_detail,parse_source_credited_opera_detail
from scripts.auto_catalogue import promote, SOURCE_ALLOWLIST
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY,assemble
from scripts.discover_season_indexes import CONFIG,validate_config,eligible,extract,scan,source_health_history

SOURCE="opera-roma-season-2026-27"
DETAIL="https://www.operaroma.it/spettacoli/lucia-di-lammermoor-2/"
INDEX="https://www.operaroma.it/genre/opera/"
DATES=[("2027-02-21","19:00"),("2027-02-23","20:00"),
       ("2027-02-24","20:00"),("2027-02-25","20:00"),
       ("2027-02-26","20:00"),("2027-02-27","18:00"),
       ("2027-02-28","16:30")]

def page():
    lines=[
        ("domenica",21,"Feb","19:00"),("martedì",23,"Feb","20:00"),
        ("mercoledì",24,"Feb","20:00"),("giovedì",25,"Feb","20:00"),
        ("venerdì",26,"Feb","20:00"),("sabato",27,"Feb","18:00"),
        ("domenica",28,"Feb","16:30")]
    return ('<p>Stagione 2026/2027</p><h1>Lucia di Lammermoor</h1>'
            '<p>Musica di Gaetano Donizetti</p><p>Direttore Giacomo Sagripanti</p>'
            '<h3>Dove</h3><h3>Teatro Costanzi</h3>'
            '<h3>Le date</h3><p>Prima rappresentazione</p>'
            +''.join(f'<p>{w}</p><p>{d}</p><p>{m}</p><p>ORE {hh}</p>'
                    for w,d,m,hh in lines)
            +'<h4>Anteprima giovani</h4><p>sabato 20 Feb 18:00</p>'
            +'<h3>Ti può interessare anche</h3>'
            +'<p>sabato 20 Mar ORE 20:00</p>')

class RomeOperaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_strict_rome_source_url_and_index(self):
        config=json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(len(validate_config(config)),14)
        self.assertEqual(next(x["url"] for x in config["sources"] if x["key"]==SOURCE),INDEX)
        with self.assertRaises(ValueError):
            obsolete=json.loads(json.dumps(config))
            next(x for x in obsolete["sources"] if x["key"]==SOURCE)["url"]="https://www.operaroma.it/opere/"
            validate_config(obsolete)
        self.assertTrue(eligible(SOURCE,DETAIL))
        self.assertFalse(eligible(SOURCE,INDEX))
        self.assertFalse(eligible(SOURCE,"https://www.operaroma.it/costanzi/"))
        matches=extract(SOURCE,INDEX,
            '<a href="/spettacoli/lucia-di-lammermoor-2/">Lucia</a>'
            '<a href="/spettacoli/la-traviata-12/">Traviata</a>'
            '<a href="/balletti/il-lago-dei-cigni/">Balletto</a>'
            '<a href="https://untrusted.example/spettacoli/lucia-di-lammermoor-2/">offsite</a>',2)
        self.assertEqual(len(matches),2)

    def test_bounded_second_official_page_adds_2027_operas(self):
        config=copy.deepcopy(json.loads(CONFIG.read_text(encoding="utf-8")))
        for source in config["sources"]:
            if source["key"]!=SOURCE:
                source["access_status"]="pending"
        first='<a href="/spettacoli/la-rondine/">La rondine</a>' \
              '<a href="/spettacoli/il-trovatore-3/">Il trovatore</a>'
        second='<a href="/spettacoli/lucia-di-lammermoor-2/">Lucia</a>' \
               '<a href="/spettacoli/the-rakes-progress-la-carriera-di-un-libertino/">Rake</a>' \
               '<a href="https://external.invalid/spettacoli/fake/">Bad</a>' \
               '<a href="/balletti/il-lago/">Balletto</a>'
        called=[]
        def fetch(db,*,source_id,url,network_enabled):
            called.append(url)
            html=second if url.endswith("/page/2/") else first
            return FetchResult(url,html,"a"*64,len(html))
        result,status=scan(config,{"schema_version":1,"candidates":[]},
                           fetcher=fetch,network_enabled=True)
        actual=[x for x in result["candidates"] if x["source_key"]==SOURCE]
        self.assertEqual(len(actual),4)
        self.assertEqual(len(called),2)
        source=next(x for x in status if x["key"]==SOURCE)
        self.assertEqual(source["status"],"success")
        self.assertEqual(source["pages_checked"],2)
        self.assertTrue(source["pagination_complete"])
        self.assertEqual(source["links"],4)

    def test_unavailable_second_page_does_not_claim_complete_coverage(self):
        config=copy.deepcopy(json.loads(CONFIG.read_text(encoding="utf-8")))
        for source in config["sources"]:
            if source["key"]!=SOURCE:
                source["access_status"]="pending"
        first='<a href="/spettacoli/la-rondine/">La rondine</a>' \
              '<a href="/spettacoli/il-trovatore-3/">Il trovatore</a>'
        def fetch(db,*,source_id,url,network_enabled):
            if url.endswith("/page/2/"):
                raise FetchUnavailable("secondary page failed")
            return FetchResult(url,first,"b"*64,len(first))
        result,status=scan(config,{"schema_version":1,"candidates":[]},
                           fetcher=fetch,network_enabled=True)
        self.assertEqual(len(result["candidates"]),2)
        source=next(x for x in status if x["key"]==SOURCE)
        self.assertEqual(source["status"],"partial_pagination")
        self.assertFalse(source["pagination_complete"])
        history=source_health_history(status,{},checked_at="2026-11-21T12:00:00+00:00")
        self.assertFalse(next(x for x in history if x["key"]==SOURCE)["current_scan_verified"])

    def test_exact_canonical_work_and_no_preview(self):
        venue,dates=parse_roma_detail(page(),url=DETAIL,title="Lucia di Lammermoor",
                                       composer="Gaetano Donizetti")
        self.assertEqual(venue,"Teatro dell'Opera di Roma")
        self.assertEqual(dates,DATES)
        rows=parse_known_opera_detail(SOURCE,DETAIL,page(),self.registry)
        self.assertEqual(len(rows),7)
        self.assertEqual({x["venue"] for x in rows},{"Teatro dell'Opera di Roma"})
        self.assertEqual({x["composer"] for x in rows},{"Gaetano Donizetti"})
        self.assertEqual(rows[0]["starts_at"],"2027-02-21T19:00:00+01:00")

    def test_verified_first_party_composer_credit_for_unregistered_opera(self):
        html=page().replace("Lucia di Lammermoor","Iphigénie en Tauride").replace(
            "Gaetano Donizetti","Christoph Willibald Gluck")
        url="https://www.operaroma.it/spettacoli/iphigenie-en-tauride/"
        title,composer,venue,dates=parse_roma_credited_detail(html,url=url)
        self.assertEqual((title,composer),("Iphigénie en Tauride","Christoph Willibald Gluck"))
        self.assertEqual((venue,len(dates)),("Teatro dell'Opera di Roma",7))
        rows=parse_source_credited_opera_detail(SOURCE,url,html)
        self.assertEqual(len(rows),7)
        self.assertTrue(all(x["composer"]=="Christoph Willibald Gluck"
                            for x in rows))

    def test_rome_2027_cyrillic_transliterated_composer_unicode(self):
        url="https://www.operaroma.it/spettacoli/una-lady-macbeth-del-distretto-di-mzensk/"
        html=page().replace("Lucia di Lammermoor",
            "Una Lady Macbeth del distretto di Mzensk").replace(
            "Gaetano Donizetti","Dmitrij Šostakovič")
        rows=parse_source_credited_opera_detail(SOURCE,url,html)
        self.assertEqual(len(rows),7)
        self.assertEqual({x["composer"] for x in rows},{"Dmitrij Šostakovič"})
        self.assertEqual({x["venue"] for x in rows},{"Teatro dell'Opera di Roma"})
        for invalid in ("Musica di Autori Vari",
                        "Musica di Direttore Esemplare",
                        "Musica di D. 123",
                        "Musica di Artista <script>"):
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):
                parse_roma_credited_detail(html.replace(
                    "Musica di Dmitrij Šostakovič",invalid),url=url)

    def test_same_official_season_september_performances_use_verified_year(self):
        url="https://www.operaroma.it/spettacoli/la-rondine/"
        heading=page().split("<h3>Le date</h3>")[0].replace(
            "Lucia di Lammermoor","La rondine").replace(
            "Gaetano Donizetti","Giacomo Puccini")
        suffix="<h3>Le date</h3>" + (
            "<p>sabato</p><p>18</p><p>Set</p><p>ORE 20:00</p>"
            "<p>mercoledì</p><p>22</p><p>Set</p><p>ORE 20:00</p>"
            "<h3>Ti può interessare anche</h3>")
        rows=parse_source_credited_opera_detail(SOURCE,url,heading+suffix)
        self.assertEqual([r["date"] for r in rows],["2027-09-18","2027-09-22"])
        self.assertEqual(rows[0]["starts_at"],"2027-09-18T20:00:00+02:00")
        self.assertEqual({r["composer"] for r in rows},{"Giacomo Puccini"})

    def test_2026_autumn_still_resolves_and_wrong_weekday_fails(self):
        url="https://www.operaroma.it/spettacoli/la-rondine/"
        heading=page().split("<h3>Le date</h3>")[0].replace(
            "Lucia di Lammermoor","La rondine").replace(
            "Gaetano Donizetti","Giacomo Puccini")
        html=heading+"<h3>Le date</h3><p>venerdì</p><p>18</p><p>Set</p><p>ORE 20:00</p>"
        rows=parse_source_credited_opera_detail(SOURCE,url,html)
        self.assertEqual([r["date"] for r in rows],["2026-09-18"])
        with self.assertRaises(ValueError):
            parse_source_credited_opera_detail(
                SOURCE,url,html.replace("venerdì","lunedì"))

    def test_first_party_credit_fails_closed_for_wrong_year_cast_or_fake_author(self):
        url="https://www.operaroma.it/spettacoli/iphigenie-en-tauride/"
        proper=page().replace("Lucia di Lammermoor","Iphigénie en Tauride").replace(
            "Gaetano Donizetti","Christoph Willibald Gluck")
        bad=[
            proper.replace("Stagione 2026/2027","Stagione 2025/2026"),
            proper.replace("<p>Musica di Christoph Willibald Gluck</p>",""),
            proper.replace("Teatro Costanzi","Teatro Nazionale"),
            proper.replace("Musica di Christoph Willibald Gluck","Musica di Unknown",
                           1),
            proper.replace("<p>Musica di Christoph Willibald Gluck</p>",
                "<p>Musica di Christoph Willibald Gluck</p><p>Musica di Falso Autore</p>"),
        ]
        # Unknown genuine credits cannot be adjudicated by the parser alone;
        # the central catalogue's independent authority gate remains required.
        for html in (bad[0],bad[1],bad[2],bad[4]):
            with self.subTest(html=html[-100:]),self.assertRaises(ValueError):
                parse_roma_credited_detail(html,url=url)
        for other in ("https://example.invalid/spettacoli/iphigenie-en-tauride/",
                      url+"?preview=true"):
            with self.subTest(url=other),self.assertRaises(ValueError):
                parse_roma_credited_detail(proper,url=other)

    def test_bad_composer_wrong_year_offsite_or_conflicting_day_fails(self):
        invalid=[page().replace("Gaetano Donizetti","Giuseppe Verdi"),
                 page().replace("Stagione 2026/2027","Stagione 2025/2026"),
                 page().replace("Teatro Costanzi","Teatro Nazionale"),
                 page().replace("<p>sabato</p><p>27</p>","<p>lunedì</p><p>27</p>")]
        for html in invalid:
            with self.subTest(html=html[-110:]):
                with self.assertRaises(ValueError):
                    parse_roma_detail(html,url=DETAIL,title="Lucia di Lammermoor",
                                      composer="Gaetano Donizetti")
        for url in ("https://example.com/spettacoli/lucia-di-lammermoor-2/",
                    DETAIL+"?preview=1"):
            with self.assertRaises(ValueError):
                parse_roma_detail(page(),url=url,title="Lucia di Lammermoor",
                                  composer="Gaetano Donizetti")

    def test_canonical_publication_and_replay_are_idempotent(self):
        rows=parse_known_opera_detail(SOURCE,DETAIL,page(),self.registry)
        cid="oa-index-52ff40865866999be465"
        candidates={"schema_version":1,"candidates":[
            {"id":cid,"source_key":SOURCE,"official_url":DETAIL,"status":"needs_review"}]}
        evidence={"schema_version":1,"evidence":[
            {"candidate_id":cid,"source_key":SOURCE,"source_url":DETAIL,
             "status":"needs_editorial_review","event_facts":rows}]}
        approved=json.loads(SOURCE_ALLOWLIST.read_text(encoding="utf-8"))["urls"]
        present=any(p["source_url"]==DETAIL for p in self.facts["productions"])
        facts,ids,urls,report=promote(
            self.facts,self.registry,evidence,candidates,approved,today=date(2026,11,21))
        roma=[p for p in facts["productions"]
              if p["municipality"]=="Roma" and p["source_url"]==DETAIL]
        self.assertEqual(len(roma),1)
        self.assertEqual(roma[0]["title"],"Lucia di Lammermoor")
        self.assertEqual(roma[0]["dates"],[[d,h] for d,h in DATES])
        self.assertEqual(report["new_recite"],0 if present else 7)
        self.assertEqual(report["new_stagings"],0 if present else 1)
        self.assertIn("Roma|Teatro dell'Opera di Roma",ids["venues"])
        graph=assemble(facts,ids,approved_extra=set(urls))
        self.assertEqual(sum(x["staging_id"]==ids["stagings"][roma[0]["key"]]["id"]
                             for x in graph["performances"]),7)
        again,again_ids,again_urls,second=promote(
            facts,ids,evidence,candidates,urls,today=date(2026,11,21))
        self.assertEqual(second["new_recite"],0)
        self.assertEqual(again,facts)
        self.assertEqual(again_ids,ids)
        self.assertEqual(again_urls,urls)

if __name__=="__main__":
    unittest.main()
