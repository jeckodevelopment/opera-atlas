"""True Roman Teatro Valle opera performance and researched historic theatre."""
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
from scripts.publish_venue_directory import build as build_venues

SOURCE="opera-roma-season-2026-27"
URL="https://www.operaroma.it/spettacoli/la-cenerentola-3/"

def read(p):
    return json.loads(p.read_text(encoding="utf-8"))

def html():
    dates=[("venerdì","01","20:00"),("domenica","03","17:00"),
           ("martedì","05","20:00"),("giovedì","07","20:00"),
           ("domenica","10","17:00")]
    return ("<p>Stagione 2026/2027</p><h1>La Cenerentola</h1>"
            "<p>Musica di Gioachino Rossini</p>"
            "<h3>Dove</h3><p>Teatro Valle Franca Valeri</p>"
            "<h3>Le date</h3>"
            + "".join(f"<p>{day}</p><p>{daynum}</p><p>Ott</p><p>ORE {clock}</p>"
                      for day,daynum,clock in dates)
            + "<h3>Ti può interessare anche</h3>")

class RomeTeatroValle(unittest.TestCase):
    def test_full_canonical_work_and_distinct_theatre_profile(self):
        seeds=[x for x in read(ROOT/"data/verified-work-authority-seeds.json")["works"]
               if x.get("source_url")==URL]
        self.assertEqual(len(seeds),1)
        work=seeds[0]
        self.assertEqual((work["title"],work["composer"]),
                         ("La Cenerentola","Gioachino Rossini"))
        self.assertTrue(validate_history(work["history"]))
        self.assertTrue(45<=len(work["synopsis"])<=300)
        self.assertEqual(work["history"]["premiere_venue"],"Teatro Valle")
        archival=load_archival_art({"la-cenerentola"})["la-cenerentola"]
        self.assertIn("commons.wikimedia.org",archival["source_url"])
        self.assertIn("1817",archival["alt"])
        self.assertIn("non è il manifesto",archival["alt"])
        directory=read(ROOT/"data/venue-directory.json")
        profiles=read(ROOT/"site/theatre-profiles.json")["venues"]
        entries=[x for x in directory["venues"] if x["city"]=="Roma"
                 and x["name"]=="Teatro Valle Franca Valeri"]
        self.assertEqual(len(entries),1)
        self.assertEqual(entries[0]["address"],"Via del Teatro Valle 21")
        self.assertEqual(profiles["Roma|Teatro Valle Franca Valeri"]["history"],
                         entries[0]["history"])
        self.assertTrue(entries[0]["photo_source_url"].startswith(
            "https://commons.wikimedia.org/wiki/File:"))
        self.assertNotEqual(entries[0]["slug"],"teatro-dell-opera-di-roma")

    def test_cached_research_is_completed_from_exact_official_seed(self):
        rows=parse_source_credited_opera_detail(SOURCE,URL,html())
        cid="oa-index-"+hashlib.sha256((SOURCE+"|"+URL).encode()).hexdigest()[:20]
        candidates={"schema_version":1,"candidates":[{
            "id":cid,"source_key":SOURCE,"official_url":URL,"status":"needs_review"}]}
        detail={"schema_version":1,"evidence":[{
            "candidate_id":cid,"source_key":SOURCE,"source_url":URL,
            "status":"needs_editorial_review","event_facts":rows}]}
        cached={"schema_version":1,"works":[{
            "candidate_id":cid,"source_key":SOURCE,"source_url":URL,
            "title":"La Cenerentola","composer":"Gioachino Rossini",
            "synopsis":None,"history":None}]}
        enriched=official_identity_candidates(detail,candidates,cached)["works"]
        seed=next(w for w in read(ROOT/"data/verified-work-authority-seeds.json")["works"]
                  if w["source_url"]==URL)
        self.assertEqual(len(enriched),1)
        self.assertEqual(enriched[0]["synopsis"],seed["synopsis"])
        self.assertEqual(enriched[0]["history"],seed["history"])
        self.assertEqual(enriched[0]["official_authority_url"],URL)
        wrong={"schema_version":1,"works":[{
            **cached["works"][0],"composer":"Giovanni Paisiello"}]}
        unchanged=official_identity_candidates(detail,candidates,wrong)["works"][0]
        self.assertIsNone(unchanged["synopsis"])
        self.assertNotIn("official_authority_url",unchanged)

    def test_shared_atomic_publication_keeps_valle_venue_separate(self):
        rows=parse_source_credited_opera_detail(SOURCE,URL,html())
        self.assertEqual(len(rows),5)
        self.assertEqual([x["date"] for x in rows],
            ["2027-10-01","2027-10-03","2027-10-05","2027-10-07","2027-10-10"])
        cid="oa-index-"+hashlib.sha256((SOURCE+"|"+URL).encode()).hexdigest()[:20]
        candidates={"schema_version":1,"candidates":[{
            "id":cid,"source_key":SOURCE,"official_url":URL,"status":"needs_review"}]}
        detail={"schema_version":1,"evidence":[{
            "candidate_id":cid,"source_key":SOURCE,"source_url":URL,
            "status":"needs_editorial_review","event_facts":rows}]}
        intel=official_identity_candidates(detail,candidates,{"schema_version":1,"works":[]})
        self.assertEqual(len(intel["works"]),1)
        facts,registry=read(MANIFEST),read(REGISTRY)
        already=any(x["source_url"]==URL for x in facts["productions"])
        out=promote_new_works(
            facts,registry,detail,candidates,intel,read(EDITORIAL),
            read(SOURCE_ALLOWLIST)["urls"],today=date(2026,11,21),
            history=read(HISTORY),require_image=True)
        new_facts,ids,approved,news,hist,report=out
        self.assertEqual(report["new_works"],0 if already else 1,report)
        self.assertEqual(report["new_recite"],0 if already else 5,report)
        new=[x for x in new_facts["productions"] if x["source_url"]==URL]
        self.assertEqual(len(new),1)
        self.assertEqual(new[0]["venue"],"Teatro Valle Franca Valeri")
        self.assertEqual(len(new[0]["dates"]),5)
        self.assertNotEqual(ids["venues"]["Roma|Teatro Valle Franca Valeri"]["id"],
                             ids["venues"]["Roma|Teatro dell'Opera di Roma"]["id"])
        directory=build_venues(read(ROOT/"data/venue-directory.json"),ids)
        record=next(x for x in directory["venues"] if
                    x["name"]=="Teatro Valle Franca Valeri")
        self.assertEqual(record["canonical_venue_id"],
                         ids["venues"]["Roma|Teatro Valle Franca Valeri"]["id"])
        output=build_editorial(new_facts,ids,news,approved_extra=set(approved),
                              history=hist)
        self.assertEqual(len([x for x in output["works"]
                              if normalized(x["title"])=="la cenerentola"
                              and normalized(x["composer"])=="gioachino rossini"]),1)
        again=promote_new_works(new_facts,ids,detail,candidates,intel,news,approved,
                                today=date(2026,11,21),history=hist,
                                require_image=True)
        self.assertEqual(again[-1]["new_works"],0)
        self.assertEqual(again[-1]["new_recite"],0)

if __name__=="__main__":
    unittest.main()
