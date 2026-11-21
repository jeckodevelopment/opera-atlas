"""Rome Lady Macbeth facts, Unicode credits and complete archival work before publishing."""
import hashlib
import json
import unittest
from datetime import date

from scripts.publish_catalog_v2 import ROOT,REGISTRY,normalized
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_work_editorial import EDITORIAL,HISTORY,build_editorial,validate_history
from scripts.publish_work_posters import load_archival_art
from scripts.auto_catalogue import official_identity_candidates,promote_new_works,SOURCE_ALLOWLIST
from scripts.collect_candidate_details import parse_source_credited_opera_detail

SOURCE="opera-roma-season-2026-27"
URL="https://www.operaroma.it/spettacoli/una-lady-macbeth-del-distretto-di-mzensk/"
TITLE="Una Lady Macbeth del distretto di Mzensk"
COMPOSER="Dmitrij Šostakovič"
SLUG="una-lady-macbeth-del-distretto-di-mzensk"
SHOWS=[("venerdì","14","Mag","20:00"),("domenica","16","Mag","16:30"),
       ("martedì","18","Mag","20:00"),("giovedì","20","Mag","20:00"),
       ("sabato","22","Mag","18:00")]
def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

def page():
    return ('<p>Stagione 2026/2027</p>'
            '<h1>Una Lady Macbeth del distretto di Mzensk</h1>'
            '<h2>(Ledi Makbet Mcenskogo Uezda)</h2>'
            '<p>Musica di&nbsp;Dmitrij Šostakovič</p>'
            '<p>Libretto di Aleksandr Prejs e Dmitrij Šostakovič</p>'
            '<h3>Dove</h3><h3>Teatro Costanzi</h3>'
            '<h3>Le date</h3><h4>Prima rappresentazione</h4>'
            +''.join(f'<p>{wd}</p><p>{dd}</p><p>{mon}</p><p>ORE {hh}</p>'
                    for wd,dd,mon,hh in SHOWS)
            +'<h3>Ti può interessare anche</h3>'
            +'<p>martedì 25 Mag ORE 20:00</p>')

class RomeLadyMacbethComplete(unittest.TestCase):
    def test_verified_official_credits_history_and_archival_document(self):
        rows=parse_source_credited_opera_detail(SOURCE,URL,page())
        self.assertEqual(len(rows),5)
        self.assertEqual([x["date"] for x in rows],
            ["2027-05-14","2027-05-16","2027-05-18","2027-05-20","2027-05-22"])
        self.assertEqual({x["composer"] for x in rows},{COMPOSER})
        self.assertEqual({x["event_title"] for x in rows},{TITLE})
        self.assertEqual({x["venue"] for x in rows},{"Teatro dell'Opera di Roma"})
        entries=[w for w in read(ROOT/"data/verified-work-authority-seeds.json")["works"]
                 if w.get("source_url")==URL]
        self.assertEqual(len(entries),1)
        seed=entries[0]
        self.assertEqual((seed["title"],seed["composer"]),(TITLE,COMPOSER))
        self.assertTrue(validate_history(seed["history"]))
        self.assertTrue(45<=len(seed["synopsis"])<=300)
        art=load_archival_art({SLUG})[SLUG]
        self.assertEqual(art["kind"],"archival_work_image")
        self.assertIn("commons.wikimedia.org",art["source_url"])
        self.assertIn("1936",art["alt"])
        self.assertIn("non è il manifesto",art["alt"])

    def test_shared_atomic_work_promotion_and_replay(self):
        rows=parse_source_credited_opera_detail(SOURCE,URL,page())
        cid="oa-index-"+hashlib.sha256((SOURCE+"|"+URL).encode()).hexdigest()[:20]
        candidates={"schema_version":1,"candidates":[{
            "id":cid,"source_key":SOURCE,"official_url":URL,"status":"needs_review"}]}
        evidence={"schema_version":1,"evidence":[{
            "candidate_id":cid,"source_key":SOURCE,"source_url":URL,
            "status":"needs_editorial_review","event_facts":rows}]}
        work=official_identity_candidates(evidence,candidates,{"schema_version":1,"works":[]})
        self.assertEqual(len(work["works"]),1)
        self.assertEqual(work["works"][0]["history"]["premiere_year"],1934)
        facts,registry=read(MANIFEST),read(REGISTRY)
        urls=read(SOURCE_ALLOWLIST)["urls"]
        previously=any(x["source_url"]==URL for x in facts["productions"])
        result=promote_new_works(
            facts,registry,evidence,candidates,work,read(EDITORIAL),urls,
            today=date(2026,11,21),history=read(HISTORY),require_image=True)
        new_facts,ids,approved,news,hist,report=result
        self.assertEqual(report["new_works"],0 if previously else 1,report)
        self.assertEqual(report["new_recite"],0 if previously else 5,report)
        public=build_editorial(new_facts,ids,news,
                               approved_extra=set(approved),history=hist)
        self.assertEqual(len([x for x in public["works"]
                         if normalized(x["title"])==normalized(TITLE) and
                            normalized(x["composer"])==normalized(COMPOSER)]),1)
        roma=[x for x in new_facts["productions"] if x["source_url"]==URL]
        self.assertEqual(len(roma),1)
        self.assertEqual(len(roma[0]["dates"]),5)
        repeated=promote_new_works(
            new_facts,ids,evidence,candidates,work,news,approved,
            today=date(2026,11,21),history=hist,require_image=True)
        self.assertEqual(repeated[-1]["new_works"],0)
        self.assertEqual(repeated[-1]["new_recite"],0)

if __name__=="__main__":
    unittest.main()
