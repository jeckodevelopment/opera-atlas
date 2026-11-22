"""Spoleto municipal fallback preserves provenance and excludes school/tour dates."""
import copy
import json
import unittest
from datetime import date

from opera_atlas.controlled_fetch import FetchResult,FetchUnavailable
from opera_atlas.spoleto_municipal_parser import URL,ORIGIN,parse_program
from scripts.discover_season_indexes import CONFIG,eligible,extract,scan
from scripts.collect_candidate_details import parse_known_opera_detail,selected_candidates
from scripts.auto_catalogue import promote
from scripts.publish_catalog_v2 import REGISTRY
from scripts.build_verified_catalog import MANIFEST

KEY="spoleto-tls-lirica-2026"
THEATRE="https://www.tls-belli.it/stagione-lirica-2026/"
HTML="""<h1>80a Stagione Lirica Sperimentale</h1>
<p>Quattro nuovi allestimenti 2026 a Spoleto</p>
<h2>Dido and Æneas</h2><p>Teatro Caio Melisso venerdì 7 agosto ore 20.30</p>
<h2>L’elisir d’amore e la Stagione regionale</h2>
<p>Concluderà il cartellone un nuovo allestimento dell'Elisir d’amore,
melodramma giocoso in due atti di Gaetano Donizetti.</p>
<p>L’opera sarà rappresentata al Teatro Nuovo Gian Carlo Menotti di Spoleto
venerdì 18 settembre ore 20.30, sabato 19 settembre ore 18.00 e
domenica 20 settembre ore 17.00 (recite per le scuole: mercoledì 16 e
giovedì 17 settembre ore 9.30).</p>
<p>Quest’ultima produzione sarà replicata nei principali teatri della regione:
lunedì 21 settembre alle ore 20.30 al Teatro Lyrick di Assisi;
mercoledì 23 settembre alle ore 20.30 al Teatro Morlacchi di Perugia.</p>"""

class SpoletoMunicipalFallbackTests(unittest.TestCase):
    def test_firstparty_exact_url_and_three_public_recite(self):
        self.assertTrue(eligible(KEY,URL))
        self.assertFalse(eligible(KEY,URL+"?test=1"))
        self.assertEqual(extract(KEY,URL,HTML,1),[URL])
        rows=parse_program(HTML,url=URL)
        self.assertEqual([x[3:] for x in rows],[
            ("2026-09-18","20:30"),("2026-09-19","18:00"),
            ("2026-09-20","17:00")])
        registry=json.loads(REGISTRY.read_text())
        facts=parse_known_opera_detail(KEY,URL,HTML,registry)
        self.assertEqual(len(facts),3)
        self.assertEqual({x["composer"] for x in facts},{"Gaetano Donizetti"})
        self.assertEqual({x["venue"] for x in facts},
                         {"Teatro Nuovo Gian Carlo Menotti"})

    def test_primary_failure_falls_back_to_independently_approved_municipality(self):
        conf=copy.deepcopy(json.loads(CONFIG.read_text()))
        for row in conf["sources"]:
            if row["key"]!=KEY:
                row["access_status"]="blocked"
        requests=[]
        def fake(db,*,source_id,url,network_enabled):
            requests.append(url)
            if url==THEATRE:raise FetchUnavailable("page unavailable")
            if url==URL:return FetchResult(url,HTML,"a"*64,len(HTML))
            raise AssertionError("unexpected unapproved URL: "+url)
        candidates,health=scan(conf,{"schema_version":1,"candidates":[]},
                               fetcher=fake,network_enabled=True)
        row=next(x for x in health if x["key"]==KEY)
        self.assertEqual(row["status"],"success")
        self.assertEqual(row["fallback_official_source"],"comune.spoleto.pg.it")
        self.assertEqual(requests,[THEATRE,URL])
        self.assertEqual([(x["source_key"],x["official_url"])
                          for x in candidates["candidates"]],[(KEY,URL)])

    def test_exact_municipal_notice_is_validated_for_catalog_publication(self):
        from scripts.build_verified_catalog import validate_auto_sources
        self.assertEqual(validate_auto_sources([URL]),{URL})
        for invalid in (URL+"?q=1",
                        URL.replace("/it/news/2022369","/it/news/another"),
                        URL.replace("www.comune.spoleto.pg.it","untrusted.invalid")):
            with self.subTest(url=invalid),self.assertRaises(ValueError):
                validate_auto_sources([invalid])

    def test_municipal_candidate_not_discarded_by_primary_host_filter(self):
        candidate={"id":"oa-index-spoleto-municipal-test",
                   "source_key":KEY,"official_url":URL,"status":"needs_review"}
        chosen=selected_candidates({"schema_version":1,"candidates":[candidate]},
                                   today=date(2026,11,22))
        self.assertEqual([(x["source_key"],x["official_url"]) for x in chosen],
                         [(KEY,URL)])
        candidate["official_url"]=URL.replace(
            "www.comune.spoleto.pg.it","untrusted.invalid")
        self.assertEqual(selected_candidates(
            {"schema_version":1,"candidates":[candidate]},
            today=date(2026,11,22)),[])

    def test_rejects_tour_school_venue_and_modified_dates(self):
        for broken in (
            HTML.replace("Gaetano Donizetti","Giacomo Puccini"),
            HTML.replace("Teatro Nuovo Gian Carlo Menotti","Teatro Caio Melisso"),
            HTML.replace("venerdì 18 settembre","giovedì 18 settembre"),
            HTML.replace("sabato 19 settembre ore 18.00",""),
            HTML.replace("80a Stagione Lirica Sperimentale","Stagione d'estate"),
        ):
            with self.subTest(broken=broken[:85]),self.assertRaises(ValueError):
                parse_program(broken,url=URL)
        for invalid in (URL+"?q=1",URL.replace("https://","http://"),
                        URL.replace("www.comune.spoleto.pg.it","evil.invalid")):
            with self.assertRaises(ValueError):
                parse_program(HTML,url=invalid)

    def test_publication_uses_exact_municipal_provenance_and_is_idempotent(self):
        registry=json.loads(REGISTRY.read_text())
        facts=json.loads(MANIFEST.read_text())
        rows=parse_known_opera_detail(KEY,URL,HTML,registry)
        cid="test-spoleto-municipal"
        evidence={"evidence":[{"candidate_id":cid,"source_key":KEY,
                  "source_url":URL,"status":"needs_editorial_review",
                  "event_facts":rows}]}
        candidates={"candidates":[{"id":cid,"source_key":KEY,
                    "official_url":URL,"status":"needs_review"}]}
        built,ids,urls,report=promote(facts,registry,evidence,candidates,[],
                                     today=date(2026,11,22))
        existing=[x for x in built["productions"]
                  if x["municipality"]=="Spoleto" and x["source_url"]==URL]
        self.assertEqual(len(existing),1,report)
        self.assertEqual(len(existing[0]["dates"]),3,report)
        already_published=any(x["municipality"]=="Spoleto"
                              and x["source_url"]==URL for x in facts["productions"])
        self.assertEqual(report["new_recite"],0 if already_published else 3,report)
        self.assertIn(URL,urls)
        built2,ids2,_,again=promote(built,ids,evidence,candidates,urls,
                                    today=date(2026,11,22))
        self.assertEqual(again["new_recite"],0)
        self.assertEqual(built2,built)
        self.assertEqual(ids2,ids)

if __name__=="__main__":
    unittest.main()
