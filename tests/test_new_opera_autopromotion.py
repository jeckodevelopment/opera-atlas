"""End-to-end graph creation for entirely new verified opera and synopsis."""
import copy
import json
import unittest
from datetime import date
from unittest.mock import patch
from scripts.auto_catalogue import promote_new_works,merge_official_poster_cache
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY,assemble
from scripts.publish_work_editorial import EDITORIAL,build_editorial

URL="https://www.teatroallascala.org/it/stagione/2026-2027/opera/fixture-opera.html"
CID="oa-index-test-new-fixture"

class NewOperaPromotionTests(unittest.TestCase):
    def test_maggio_galuppi_complete_source_first_work_card(self):
        from scripts.auto_catalogue import official_identity_candidates, promote_new_works
        from scripts.publish_work_posters import load_archival_art
        from scripts.auto_catalogue import SOURCE_ALLOWLIST
        from scripts.publish_work_editorial import EDITORIAL, HISTORY
        import hashlib
        url="https://www.maggiofiorentino.com/events/il-mondo-alla-roversa-o-sia-le-donne-che-comandano"
        source="maggio-fiorentino-calendar-2027"
        cid="oa-index-"+hashlib.sha256((source+"|"+url).encode()).hexdigest()[:20]
        candidate={"schema_version":1,"candidates":[{
            "id":cid,"source_key":source,"official_url":url,"status":"needs_review"}]}
        dates=[("2027-01-30","17:00"),("2027-01-31","15:30"),("2027-02-02","20:00")]
        from scripts.build_verified_catalog import official_local_time
        evidence={"schema_version":1,"evidence":[{
            "candidate_id":cid,"source_key":source,"source_url":url,
            "status":"needs_editorial_review",
            "event_facts":[{"event_title":"Il mondo alla roversa o sia le donne che comandano",
                "composer":"Baldassarre Galuppi","venue":"Teatro Goldoni",
                "date":day,"starts_at":official_local_time(day,clock)}
                for day,clock in dates]}]}
        doc=official_identity_candidates(evidence,candidate,{"schema_version":1,"works":[]})
        self.assertEqual(len(doc["works"]),1)
        self.assertEqual(doc["works"][0]["composer"],"Baldassarre Galuppi")
        self.assertEqual(doc["works"][0]["history"]["premiere_year"],1750)
        cover=load_archival_art({"il-mondo-alla-roversa-o-sia-le-donne-che-comandano"})
        self.assertEqual(cover["il-mondo-alla-roversa-o-sia-le-donne-che-comandano"]["kind"],"archival_work_image")
        work_ids=json.loads(REGISTRY.read_text(encoding="utf-8"))
        if any(w["title"]=="Il mondo alla roversa o sia le donne che comandano" and w["composer"]=="Baldassarre Galuppi"
               for w in work_ids["works"].values()):
            return # Already promoted by an independent refresh.
        facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        orig=json.loads(EDITORIAL.read_text(encoding="utf-8"))
        history=json.loads(HISTORY.read_text(encoding="utf-8"))
        allow=json.loads(SOURCE_ALLOWLIST.read_text(encoding="utf-8"))["urls"]
        published=promote_new_works(facts,work_ids,evidence,candidate,doc,orig,allow,
                                  today=date(2026,11,21),history=history,require_image=True)
        self.assertEqual(published[-1]["new_works"],1,published[-1])
        self.assertEqual(published[-1]["new_recite"],3,published[-1])
        self.assertIn("Firenze|Teatro Goldoni",published[1]["venues"])

    def test_ready_cached_works_get_editorial_before_publication(self):
        from scripts.auto_catalogue import complete_cached_verified_work_cards
        from scripts.auto_work_research import OUT
        from scripts.collect_candidate_details import OUTPUT
        doc=json.loads(OUT.read_text(encoding="utf-8"))
        evidence=json.loads(OUTPUT.read_text(encoding="utf-8"))
        complete=complete_cached_verified_work_cards(doc,evidence)
        targets={
            "oa-index-184e57e1cd9f38d554d5":"Gaetano Donizetti",
            "oa-index-b4180540983902f703af":"Giuseppe Verdi",
            "oa-index-dfe824fe3301174d2165":"Vincenzo Bellini",
            "oa-index-05dfa4b5d5270a7fc051":"Vincenzo Bellini",
            "oa-index-144db2827af86d96232c":"Jacques Offenbach",
            "oa-index-9c8433ba74501efca6eb":"Francesco Cilea",
            "oa-index-5ab298c2300ec275c2a3":"Wolfgang Amadeus Mozart",
            "oa-index-6cd199691f7145a4d048":"Engelbert Humperdinck",
            "oa-index-8a4ea2e4cf761a147ffb":"Giuseppe Verdi"}
        actual={x["candidate_id"]:x for x in complete["works"]}
        for cid,composer in targets.items():
            with self.subTest(candidate=cid):
                self.assertEqual(actual[cid]["composer"],composer)
                self.assertTrue(45<=len(actual[cid]["synopsis"])<=300)
                self.assertIsNotNone(actual[cid]["history"])
                self.assertNotIn("Consulta le rappresentazioni",actual[cid]["synopsis"])
        # Test placeholder replacement independently from the mutable public
        # checkpoint, which may already have a completed synopsis.
        unresolved=copy.deepcopy(doc)
        old=next(x for x in unresolved["works"] if x["candidate_id"]==
                 "oa-index-9c8433ba74501efca6eb")
        old["synopsis"]=("«Adriana Lecouvreur» è un'opera di Francesco Cilea. "
                         "Consulta le rappresentazioni verificate in programma nei teatri italiani.")
        completed=complete_cached_verified_work_cards(unresolved,evidence)
        final=next(x for x in completed["works"] if x["candidate_id"]==
                   "oa-index-9c8433ba74501efca6eb")
        self.assertNotIn("Consulta le rappresentazioni",final["synopsis"])
        # Construct a missing synopsis explicitly, rather than assuming
        # the public intelligence cache has not yet been promoted.
        before_spoof=copy.deepcopy(doc)
        source=next(x for x in before_spoof["works"] if x["candidate_id"]==
                    "oa-index-b4180540983902f703af")
        source["synopsis"]=None
        forged=json.loads(json.dumps(evidence))
        match=next(x for x in forged["evidence"] if x["candidate_id"]==
                   "oa-index-b4180540983902f703af")
        match["event_facts"][0]["composer"]="Different Composer"
        blocked=complete_cached_verified_work_cards(before_spoof,forged)
        cached=next(x for x in blocked["works"] if x["candidate_id"]==
                    "oa-index-b4180540983902f703af")
        self.assertIsNone(cached.get("synopsis"))

    def test_salvatori_modena_can_promote_with_exact_municipal_image(self):
        from scripts.auto_catalogue import official_identity_candidates,promote_new_works
        from scripts.publish_catalog_v2 import ROOT
        from scripts.publish_work_editorial import HISTORY
        url=("https://www.teatrocomunalemodena.it/spettacolo/"
             "daniele-furlati-i-salvatori-della-mezzanotte/")
        doc=json.loads((ROOT/"data/candidate-detail-evidence.json").read_text(encoding="utf-8"))
        record=next(x for x in doc["evidence"] if x["source_url"]==url)
        cid=record["candidate_id"]
        evidence={"schema_version":1,"evidence":[record]}
        candidate={"schema_version":1,"candidates":[{
            "id":cid,"source_key":"modena-teatro-opera-2026-27",
            "official_url":url,"status":"needs_review"}]}
        intelligence=official_identity_candidates(evidence,candidate,
                                              {"schema_version":1,"works":[]})
        work=next(x for x in intelligence["works"] if x["candidate_id"]==cid)
        self.assertEqual((work["title"],work["composer"]),
                         ("I salvatori della mezzanotte","Daniele Furlati"))
        self.assertEqual(work["history"]["premiere_date"],"2023-12-17")
        self.assertEqual(work["history"]["librettist"],"Bruno Tognolini")
        self.assertNotIn("Consulta le rappresentazioni verificate",work["synopsis"])
        facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        ids=json.loads(REGISTRY.read_text(encoding="utf-8"))
        editorial=json.loads(EDITORIAL.read_text(encoding="utf-8"))
        history=json.loads(HISTORY.read_text(encoding="utf-8"))
        updated,_,_,_,_,report=promote_new_works(
            facts,ids,evidence,candidate,intelligence,editorial,[],
            today=date(2026,11,22),history=history,require_image=True)
        # The image is a genuine, individually reviewed municipal scene
        # photograph, not an invented cover or a different work's poster.
        self.assertEqual(report["new_works"],1)
        self.assertEqual(report["new_stagings"],1)
        self.assertEqual(report["new_recite"],1)
        self.assertNotIn({"candidate_id":cid,"reason":"verified_work_image_missing"},
                         report["auto_skipped"])
        self.assertNotEqual(updated,facts)

    def test_veleno_is_same_canonical_work_in_reggio_and_modena(self):
        from scripts.publish_catalog_v2 import ROOT,normalized
        from scripts.publish_work_editorial import validate_history
        seeds=json.loads((ROOT/"data/verified-work-authority-seeds.json")
                         .read_text(encoding="utf-8"))["works"]
        original=next(x for x in seeds if x["source_key"]=="reggio-valli-opera-2026-27"
                      and x["title"]=="Veleno")
        modenese=next(x for x in seeds if x["source_key"]=="modena-teatro-opera-2026-27"
                      and x["title"]=="Veleno")
        self.assertNotEqual(original["source_url"],modenese["source_url"])
        self.assertEqual(
            (normalized(original["title"]),normalized(original["composer"])),
            (normalized(modenese["title"]),normalized(modenese["composer"])))
        self.assertEqual(modenese["history"]["premiere_date"],"2027-04-28")
        self.assertEqual(original["history"]["premiere_venue"],
                         modenese["history"]["premiere_venue"])
        self.assertEqual(original["synopsis"],modenese["synopsis"])
        self.assertTrue(validate_history(modenese["history"]))
        self.assertIn(modenese["source_url"],modenese["history"]["sources"])

    def test_siberia_source_bound_editorial_completes_existing_candidate(self):
        from scripts.auto_catalogue import complete_cached_verified_work_cards
        from scripts.auto_work_research import OUT
        from scripts.collect_candidate_details import OUTPUT
        from scripts.publish_work_editorial import validate_history
        intelligence=json.loads(OUT.read_text(encoding="utf-8"))
        evidence=json.loads(OUTPUT.read_text(encoding="utf-8"))
        cid="oa-index-9fdcd7eba240da4540af"
        completed=complete_cached_verified_work_cards(intelligence,evidence)
        row=next(x for x in completed["works"] if x["candidate_id"]==cid)
        self.assertEqual(row["wikidata_id"],"Q2292268")
        self.assertEqual(row["composer"],"Umberto Giordano")
        self.assertIn("Stephana",row["synopsis"])
        self.assertTrue(validate_history(row["history"]))
        # An exact source-bound editorial card must never be reused when
        # official composer evidence disagrees with the canonical identity.
        tampered=copy.deepcopy(evidence)
        detail=next(x for x in tampered["evidence"] if x["candidate_id"]==cid)
        detail["event_facts"][0]["composer"]="Giuseppe Verdi"
        unresolved=copy.deepcopy(intelligence)
        target=next(x for x in unresolved["works"] if x["candidate_id"]==cid)
        target["synopsis"]=None
        rejected=complete_cached_verified_work_cards(unresolved,tampered)
        row=next(x for x in rejected["works"] if x["candidate_id"]==cid)
        self.assertIsNone(row["synopsis"])

    @classmethod
    def setUpClass(cls):
        cls.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.editorial=json.loads(EDITORIAL.read_text(encoding="utf-8"))

    def fixture(self):
        candidates={"schema_version":1,"candidates":[{
            "id":CID,"source_key":"scala-season-2026-27",
            "official_url":URL,"status":"needs_review"}]}
        evidence={"schema_version":1,"evidence":[{
            "candidate_id":CID,"source_key":"scala-season-2026-27",
            "source_url":URL,"status":"needs_editorial_review",
            "event_facts":[{
                "event_title":"Fixture Opera","composer":"Gaetano Donizetti",
                "date":"2027-06-02",
                "starts_at":"2027-06-02T20:00:00+02:00",
                "venue":"Teatro alla Scala"}
            ]}]}
        enrichment={"schema_version":1,"works":[{
            "candidate_id":CID,"source_key":"scala-season-2026-27",
            "source_url":URL,"wikidata_id":"Q111",
            "title":"Fixture Opera","composer":"Gaetano Donizetti",
            "synopsis":"Fixture Opera affronta le tensioni della corte e un destino "
                       "segnato da passioni e lotte per il potere.",
            "history":{"librettist":"Giovanni Example",
                       "premiere_year":1830,"premiere_venue":"Teatro Nuovo",
                       "premiere_city":"Milano",
                       "sources":["https://www.wikidata.org/wiki/Q111"]}
        }]}
        return evidence,candidates,enrichment

    def test_exact_jesi_alternate_official_art_requires_provenance(self):
        from scripts.auto_catalogue import verified_candidate_image
        index=("https://www.fondazionepergolesispontini.com/"
               "lirica/programma-stagione-lirica-2026/")
        dedicated=("https://www.fondazionepergolesispontini.com/"
                   "eventi/lesecuzione-sotto-lo-sguardo-di-tosca-2/")
        image={"kind":"official_production_image",
               "source_url":dedicated,
               "image_url":"https://www.fondazionepergolesispontini.com/wp-content/uploads/2026/11/lesecuzione-bollo.jpg",
               "credit":"Fondazione Pergolesi Spontini",
               "alt":"L'esecuzione, locandina"}
        record={"source_key":"jesi-esecuzione-opera-2026",
                "source_url":index,"poster_evidence":image}
        result=verified_candidate_image(
            record,title="L'esecuzione",composer="Salvatore Passantino",url=index)
        self.assertIsNotNone(result)
        self.assertEqual(result["source_url"],dedicated)
        for invalid in [
            {**record,"source_key":"jesi-don-pasquale-opera-2026"},
            {**record,"poster_evidence":{**image,"source_url":"https://untrusted.example/poster"}},
            {**record,"poster_evidence":{**image,"image_url":"https://www.fondazionepergolesispontini.com/images/tosca.jpg"}},
        ]:
            self.assertIsNone(verified_candidate_image(
                invalid,title="L'esecuzione",composer="Salvatore Passantino",url=index))
        self.assertIsNone(verified_candidate_image(
            record,title="L'esecuzione",composer="Giacomo Puccini",url=index))

    def test_new_work_is_deferred_until_authentic_poster_is_verified(self):
        evidence,candidates,enrichment=self.fixture()
        skipped=promote_new_works(
            self.facts,self.registry,evidence,candidates,enrichment,
            self.editorial,[],today=date(2026,11,20),require_image=True)
        self.assertEqual(skipped[-1]["new_works"],0)
        self.assertTrue(any(x["reason"]=="verified_work_image_missing"
                            for x in skipped[-1]["auto_skipped"]))
        self.assertEqual(skipped[1],self.registry)

        poster={"image_url":"https://www.teatroallascala.org/static/upload/fixture/fixture-opera-poster.jpg",
                "source_url":URL,"kind":"official_production_image",
                "alt":"Fixture Opera, immagine ufficiale", "credit":"Teatro alla Scala"}
        evidence["evidence"][0]["poster_evidence"]=poster
        result=promote_new_works(
            self.facts,self.registry,evidence,candidates,enrichment,
            self.editorial,[],today=date(2026,11,20),require_image=True)
        self.assertEqual(result[-1]["new_works"],1)
        for invalid in (
            {**poster,"image_url":"https://example.org/fixture-opera.jpg"},
            {**poster,"image_url":"https://www.teatroallascala.org/static/upload/other/nabucco.jpg"},
            {**poster,"source_url":"https://www.teatroallascala.org/it/fake.html"},
        ):
            evidence["evidence"][0]["poster_evidence"]=invalid
            denied=promote_new_works(
                self.facts,self.registry,evidence,candidates,enrichment,
                self.editorial,[],today=date(2026,11,20),require_image=True)
            self.assertEqual(denied[-1]["new_works"],0)

    def test_archival_art_promotes_new_work_without_official_poster_cache(self):
        # A trustworthy archival image is already in the archival work bank.
        # Its lack of an official-production image must not crash main().
        evidence,candidates,enrichment=self.fixture()
        with patch("scripts.publish_work_posters.load_archival_art",
                   return_value={"fixture-opera":{"image_url":
                       "https://commons.wikimedia.org/wiki/Special:Redirect/file/Fixture.png"}}):
            result=promote_new_works(
                self.facts,self.registry,evidence,candidates,enrichment,
                self.editorial,[],today=date(2026,11,20),require_image=True)
        self.assertEqual(result[-1]["new_works"],1)
        self.assertEqual(merge_official_poster_cache(None,{}),None)
        self.assertEqual(merge_official_poster_cache({"schema_version":2,
                                                      "posters":{}},{}),None)
        before={"schema_version":2,"posters":{},"checks":{}}
        image={"work_id":"oa-w-123456","kind":"official_production_image",
               "image_url":"https://www.teatroallascala.org/example.jpg"}
        after=merge_official_poster_cache(before,{"oa-w-123456":image})
        self.assertEqual(after["posters"]["oa-w-123456"],image)
        self.assertEqual(before["posters"],{})
        with self.assertRaises(ValueError):
            merge_official_poster_cache(before,{"oa-w-999999":image})

    def test_new_opera_and_synopsis_are_published_as_one_graph(self):
        evidence,candidates,enrichment=self.fixture()
        facts,ids,urls,editorial,report=promote_new_works(
            self.facts,self.registry,evidence,candidates,enrichment,
            self.editorial,[],today=date(2026,11,20))
        self.assertEqual((report["new_works"],report["new_stagings"],report["new_recite"]),
                         (1,1,1))
        self.assertEqual(len(ids["works"]),len(self.registry["works"])+1)
        self.assertIn("fixture-opera",editorial["synopses"])
        self.assertEqual(urls,[URL])
        graph=assemble(facts,ids,approved_extra=set(urls))
        self.assertEqual(len(graph["performances"]),len(self.registry["performances"])+1)
        from scripts.publish_work_editorial import HISTORY
        history=json.loads(HISTORY.read_text(encoding="utf-8"))
        history["works"]["fixture-opera"]={
            "librettist":"Giovanni Example","premiere_year":1830,
            "premiere_venue":"Teatro Nuovo","premiere_city":"Milano",
            "sources":["https://www.wikidata.org/wiki/Q111"]}
        card=build_editorial(facts,ids,editorial,approved_extra=set(urls),
                             history=history)
        self.assertEqual(len(card["works"]),len(ids["works"])+len(ids["reserved_works"]))
        self.assertTrue(any(x["slug"]=="fixture-opera" for x in card["works"]))
        second=promote_new_works(facts,ids,evidence,candidates,enrichment,editorial,urls,
                                 today=date(2026,11,20))
        self.assertEqual(second[-1]["new_works"],0)
        self.assertEqual(second[0],facts)
        self.assertEqual(second[1],ids)

    def test_verified_identity_without_history_remains_unpublished(self):
        evidence,candidates,enrichment=self.fixture()
        enrichment["works"][0]["history"]=None
        from scripts.publish_work_editorial import HISTORY
        history=json.loads(HISTORY.read_text(encoding="utf-8"))
        result=promote_new_works(self.facts,self.registry,evidence,candidates,
                                 enrichment,self.editorial,[],
                                 today=date(2026,11,20),history=history,
                                 require_image=True)
        self.assertEqual(result[-1]["new_works"],0)
        self.assertIn({"candidate_id":CID,"reason":"incomplete_work_editorial"},
                      result[-1]["auto_skipped"])
        self.assertEqual(result[1],self.registry)

    def test_wrong_composer_or_unproven_date_cannot_create_new_work(self):
        evidence,candidates,enrichment=self.fixture()
        variants=[]
        bad=copy.deepcopy(evidence)
        bad["evidence"][0]["event_facts"][0]["composer"]="Another composer"
        variants.append(bad)
        bad=copy.deepcopy(evidence)
        bad["evidence"][0]["event_facts"][0]["starts_at"]="2027-06-02T20:00:00"
        variants.append(bad)
        bad=copy.deepcopy(evidence)
        bad["evidence"][0]["event_facts"][0]["venue"]="Unknown theatre"
        variants.append(bad)
        for modified in variants:
            facts,ids,urls,editorial,report=promote_new_works(
                self.facts,self.registry,modified,candidates,enrichment,
                self.editorial,[],today=date(2026,11,20))
            self.assertEqual(report["new_works"],0)
            self.assertEqual(facts,self.facts)
            self.assertEqual(ids,self.registry)
            self.assertEqual(editorial,self.editorial)
            self.assertEqual(urls,[])

    def test_unverified_synopsis_or_source_is_not_published(self):
        evidence,candidates,enrichment=self.fixture()
        intel=copy.deepcopy(enrichment)
        intel["works"][0]["synopsis"]="Too short"
        one=promote_new_works(self.facts,self.registry,evidence,candidates,intel,
                              self.editorial,[],today=date(2026,11,20))
        self.assertEqual(one[-1]["new_works"],0)
        bad=copy.deepcopy(candidates)
        bad["candidates"][0]["official_url"]="https://evil.example/opera/fixture-opera.html"
        two=promote_new_works(self.facts,self.registry,evidence,bad,enrichment,
                              self.editorial,[],today=date(2026,11,20))
        self.assertEqual(two[-1]["new_works"],0)
if __name__=="__main__":
    unittest.main()
