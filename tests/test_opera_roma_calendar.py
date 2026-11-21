"""Official Rome opera detail must produce exact date/clock and canonical ID."""
import json
import unittest
from datetime import date

from opera_atlas.roma_detail_parser import parse_roma_detail
from scripts.collect_candidate_details import parse_known_opera_detail
from scripts.auto_catalogue import promote, SOURCE_ALLOWLIST
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY,assemble
from scripts.discover_season_indexes import CONFIG,validate_config,eligible,extract

SOURCE="opera-roma-season-2026-27"
DETAIL="https://www.operaroma.it/spettacoli/lucia-di-lammermoor-2/"
INDEX="https://www.operaroma.it/opere/"
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
        self.assertTrue(eligible(SOURCE,DETAIL))
        self.assertFalse(eligible(SOURCE,INDEX))
        self.assertFalse(eligible(SOURCE,"https://www.operaroma.it/costanzi/"))
        matches=extract(SOURCE,INDEX,
            '<a href="/spettacoli/lucia-di-lammermoor-2/">Lucia</a>'
            '<a href="/spettacoli/la-traviata-12/">Traviata</a>'
            '<a href="/balletti/il-lago-dei-cigni/">Balletto</a>'
            '<a href="https://untrusted.example/spettacoli/lucia-di-lammermoor-2/">offsite</a>',2)
        self.assertEqual(len(matches),2)

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
        roma=[p for p in facts["productions"] if p["municipality"]=="Roma"]
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
