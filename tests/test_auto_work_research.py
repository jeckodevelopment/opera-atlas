"""Autonomous new-opera research needs corroborated authority and original summary."""
import json
import unittest
from datetime import date

from scripts.auto_work_research import (
    claim_ids, resolve_identity, choose_candidates, research,make_synopsis,
    official_title_hint, wiki_excerpt
)

URL="https://www.teatroallascala.org/it/stagione/2026-2027/opera/anna-bolena.html"
CANDIDATE={"id":"oa-index-anna","source_key":"scala-season-2026-27",
           "official_url":URL,"status":"needs_review"}

class AutoWorkResearchTests(unittest.TestCase):
    def test_exact_wikidata_opera_and_composer(self):
        def fake(url):
            if "wbsearchentities" in url:
                return {"search":[{"id":"Q111","label":"Anna Bolena"},
                                  {"id":"Q222","label":"Other work"}]}
            if "ids=Q111" in url:
                return {"entities":{"Q111":{
                    "labels":{"it":{"value":"Anna Bolena"}},
                    "claims":{
                        "P7937":[{"mainsnak":{"datavalue":{"value":{"id":"Q1344"}}}}],
                        "P86":[{"mainsnak":{"datavalue":{"value":{"id":"Q333"}}}}],
                    },
                    "sitelinks":{"itwiki":{"title":"Anna Bolena"}}
                }}}
            if "ids=Q333" in url:
                return {"entities":{"Q333":{"labels":{"it":{"value":"Gaetano Donizetti"}}}}}
            raise AssertionError(url)
        result=resolve_identity("anna bolena",fetch=fake)
        self.assertEqual(result["title"],"Anna Bolena")
        self.assertEqual(result["composer"],"Gaetano Donizetti")
        self.assertEqual(result["wikidata_id"],"Q111")
        self.assertTrue(result["wikipedia_url"].startswith("https://it.wikipedia.org/"))

    def test_two_barbiere_compositions_resolve_only_with_official_composer(self):
        def claim(qid):
            return [{"mainsnak":{"datavalue":{"value":{"id":qid}}}}]
        def entity(composer_id):
            return {"labels":{"it":{"value":"Il barbiere di Siviglia"}},
                    "claims":{"P7937":claim("Q1344"),"P86":claim(composer_id)},
                    "sitelinks":{"itwiki":{"title":"Il barbiere di Siviglia"}}}
        def fake(url):
            if "wbsearchentities" in url:
                return {"search":[{"id":"Q101","label":"Il barbiere di Siviglia"},
                                  {"id":"Q102","label":"Il barbiere di Siviglia"}]}
            if "ids=Q101%7CQ102" in url:
                return {"entities":{"Q101":entity("Q201"),
                                    "Q102":entity("Q202")}}
            if "ids=Q201%7CQ202" in url:
                return {"entities":{
                    "Q201":{"labels":{"it":{"value":"Gioachino Rossini"}}},
                    "Q202":{"labels":{"it":{"value":"Giovanni Paisiello"}}}}}
            raise AssertionError(url)
        self.assertIsNone(resolve_identity("Il barbiere di Siviglia",fetch=fake))
        rossini=resolve_identity("Il barbiere di Siviglia",
                                 composer_hint="Gioachino Rossini",fetch=fake)
        paisiello=resolve_identity("Il barbiere di Siviglia",
                                   composer_hint="Giovanni Paisiello",fetch=fake)
        self.assertEqual(rossini["wikidata_id"],"Q101")
        self.assertEqual(paisiello["wikidata_id"],"Q102")
        self.assertIsNone(resolve_identity("Il barbiere di Siviglia",
                          composer_hint="Giacomo Puccini",fetch=fake))

    def test_known_title_is_researched_for_new_composer(self):
        from scripts.auto_work_research import preverified_work_material
        options={"schema_version":1,"candidates":[CANDIDATE]}
        # Known title must not bypass authority lookup: it may be a homonym.
        choices=choose_candidates(options,{"schema_version":1,"works":[]},
                                  {"anna-bolena"},today=date(2026,11,20))
        self.assertEqual(len(choices),1)
        captured=[]
        def resolve(title,*,composer_hint=None):
            captured.append(composer_hint)
            return {"title":"Anna Bolena","composer":"Second Composer",
                    "wikidata_id":"Q101",
                    "authority_url":"https://www.wikidata.org/wiki/Q101",
                    "wikipedia_url":"https://it.wikipedia.org/wiki/Anna_Bolena"}
        work_evidence={"evidence":[{
            "candidate_id":CANDIDATE["id"],"source_key":CANDIDATE["source_key"],
            "source_url":CANDIDATE["official_url"],"status":"needs_editorial_review",
            "event_facts":[{"event_title":"Anna Bolena",
                            "composer":"Second Composer"}]}]}
        output,status=research(options,{"schema_version":1,"works":[]},
                               {"anna-bolena"},today=date(2026,11,20),
                               evidence=work_evidence,resolve=resolve,
                               prepared=preverified_work_material(),
                               extract=lambda obj:"Source " * 45,
                               generate=lambda *a,**k:"Nuova composizione con una storia documentata e autonoma.",
                               generate_history=lambda *a,**k:{
                                   "librettist":"Giovanni Example",
                                   "premiere_year":1900,
                                   "premiere_venue":"Teatro Nuovo",
                                   "premiere_city":"Milano",
                                   "sources":["https://www.wikidata.org/wiki/Q101"]},
                               api_key="test")
        self.assertEqual(captured,["Second Composer"])
        self.assertEqual(status[0]["status"],"enriched")
        self.assertEqual(output["works"][0]["composer"],"Second Composer")

    def test_missing_opera_type_rejected(self):
        def fake(url):
            if "wbsearchentities" in url:
                return {"search":[{"id":"Q111","label":"Anna Bolena"}]}
            return {"entities":{"Q111":{
                "labels":{"it":{"value":"Anna Bolena"}},
                "claims":{"P31":[{"mainsnak":{"datavalue":{"value":{"id":"Q5"}}}}],
                          "P86":[{"mainsnak":{"datavalue":{"value":{"id":"Q333"}}}}]},
                "sitelinks":{"itwiki":{"title":"Anna Bolena"}}
            }}}
        self.assertIsNone(resolve_identity("anna bolena",fetch=fake))

    def test_piccolo_orso_is_opera_with_documented_world_premiere(self):
        from scripts.auto_work_research import preverified_work_material
        material=preverified_work_material()
        card=material["piccolo-orso-e-la-montagna-di-ghiaccio"]
        self.assertIn("Piccolo Orso",card["synopsis"])
        self.assertEqual(card["history"]["librettist"],"Giancarlo De Cataldo")
        self.assertEqual(card["history"]["premiere_year"],2026)
        self.assertEqual(card["history"]["premiere_venue"],"Teatro Malibran")
        self.assertEqual(card["history"]["premiere_city"],"Venezia")
        self.assertTrue(any("teatrolafenice.it" in x
                            for x in card["history"]["sources"]))

    def test_additional_ten_original_opera_cards_have_archival_histories(self):
        from scripts.auto_work_research import preverified_work_material
        material=preverified_work_material()
        expected={
            "don-quichotte","the-rake-s-progress","leonora",
            "les-pecheurs-de-perles","boris-godunov","nozze-istriane",
            "partenope","al-cavallino-bianco","norma","l-arca-di-noe"}
        self.assertTrue(expected.issubset(material))
        for slug in expected:
            with self.subTest(slug=slug):
                self.assertGreaterEqual(len(material[slug]["synopsis"]),45)
                self.assertEqual(len(material[slug]["history"]["sources"])>=1,True)
                self.assertGreaterEqual(material[slug]["history"]["premiere_year"],1600)

    def test_official_fenice_title_aliases_are_exact_and_checked_by_authority(self):
        for slug,title in (
            ("normatebar","Norma"),
            ("ilbarbieredisivigliapercacciolo","Il barbiere di Siviglia")):
            with self.subTest(slug=slug):
                item={"id":slug,"source_key":"fenice-opera-2026-27",
                      "official_url":"https://www.teatrolafenice.it/event/"+slug+"/",
                      "status":"needs_review"}
                self.assertEqual(official_title_hint(item),title)
        unrelated={"id":"unrelated","source_key":"fenice-opera-2026-27",
                   "official_url":"https://www.teatrolafenice.it/event/normatebar-other/",
                   "status":"needs_review"}
        self.assertEqual(official_title_hint(unrelated),"normatebar other")
        untrusted=dict(unrelated,official_url="https://evil.example/event/normatebar/")
        self.assertIsNone(official_title_hint(untrusted))

    def test_eleven_sourced_opera_cards_are_suitable_for_automated_authority_checks(self):
        from scripts.auto_work_research import preverified_work_material,MAX_PREVERIFIED
        material=preverified_work_material()
        expected={
            "anna-bolena","i-puritani","il-barbiere-di-siviglia",
            "ernani","falstaff","la-clemenza-di-tito",
            "adriana-lecouvreur","nixon-in-china","hansel-und-gretel",
            "il-pipistrello","die-zauberflote"
        }
        self.assertTrue(expected.issubset(material))
        self.assertGreaterEqual(MAX_PREVERIFIED,len(expected))
        for slug in expected:
            with self.subTest(work=slug):
                self.assertTrue(45<=len(material[slug]["synopsis"])<=300)
                self.assertGreaterEqual(len(material[slug]["history"]["sources"]),1)
        # All eleven have their own approved official production link.
        options={"schema_version":1,"candidates":[
            {"id":"work-"+slug,"source_key":"scala-season-2026-27",
             "official_url":"https://www.teatroallascala.org/it/stagione/2026-2027/opera/"+
                 slug+".html","status":"needs_review"} for slug in sorted(expected)]}
        batch=choose_candidates(options,{"schema_version":1,"works":[]},set(),
                                today=date(2026,11,20))
        self.assertEqual({x["id"] for x in batch},
                         {"work-"+slug for slug in expected})

    def test_preverified_rigoletto_is_enriched_without_paid_model(self):
        from scripts.auto_work_research import preverified_work_material
        material=preverified_work_material()
        self.assertIn("rigoletto",material)
        self.assertEqual(material["rigoletto"]["history"]["premiere_year"],1851)
        candidate={"id":"rigoletto-new","source_key":"parma-opera-2027",
                   "official_url":"https://teatroregioparma.it/spettacolo/rigoletto/",
                   "status":"needs_review"}
        calls=[]
        def resolve(title):
            calls.append(title)
            return {"title":"Rigoletto","composer":"Giuseppe Verdi",
                    "wikidata_id":"Q123","authority_url":"https://www.wikidata.org/wiki/Q123",
                    "wikipedia_url":"https://it.wikipedia.org/wiki/Rigoletto"}
        result,outcomes=research({"schema_version":1,"candidates":[candidate]},
                                 {"schema_version":1,"works":[]},set(),
                                 today=date(2026,11,20),resolve=resolve,
                                 extract=lambda x: (_ for _ in ()).throw(
                                     AssertionError("paid excerpt pipeline must not run")),
                                 generate=lambda *a,**k: (_ for _ in ()).throw(
                                     AssertionError("paid synthesis must not run")),
                                 generate_history=lambda *a,**k: (_ for _ in ()).throw(
                                     AssertionError("paid history synthesis must not run")),
                                 api_key="",allow_authority=True)
        self.assertEqual(calls,["rigoletto"])
        self.assertEqual(outcomes[0]["status"],"enriched")
        self.assertEqual(result["works"][0]["composer"],"Giuseppe Verdi")
        self.assertEqual(result["works"][0]["synopsis"],material["rigoletto"]["synopsis"])
        self.assertEqual(result["works"][0]["history"],material["rigoletto"]["history"])
        again,events=research({"schema_version":1,"candidates":[candidate]},result,set(),
                              today=date(2026,11,21),
                              resolve=lambda x: (_ for _ in ()).throw(
                                  AssertionError("already enriched")),
                              api_key="",allow_authority=True)
        self.assertEqual(again,result)
        self.assertEqual(events,[])

    def test_keyless_authority_retries_only_when_identity_cannot_be_verified(self):
        doc={"schema_version":1,"candidates":[CANDIDATE]}
        calls=[]
        def resolver(title):
            calls.append(title)
            return None
        result,status=research(doc,{"schema_version":1,"works":[]},set(),
                               today=date(2026,11,20),resolve=resolver,api_key="")
        self.assertEqual(result["works"],[])
        self.assertEqual(calls,["anna bolena"])
        self.assertEqual(status[0]["status"],"automatic_retry")

    def test_new_work_generates_keyless_factual_introduction(self):
        from scripts.auto_work_research import identity_introduction
        identity={"title":"Il barbiere di Siviglia",
                  "composer":"Giovanni Paisiello",
                  "wikidata_id":"Q123",
                  "authority_url":"https://www.wikidata.org/wiki/Q123",
                  "wikipedia_url":"https://it.wikipedia.org/wiki/Il_barbiere_di_Siviglia"}
        doc={"schema_version":1,"candidates":[CANDIDATE]}
        def resolver(title):
            return identity
        def forbidden(*args,**kwargs):
            raise AssertionError("No paid model, excerpt or historical synthesis")
        result,status=research(doc,{"schema_version":1,"works":[]},set(),
                               today=date(2026,11,20),resolve=resolver,
                               extract=forbidden,generate=forbidden,
                               generate_history=forbidden,api_key="")
        self.assertEqual(status[0]["status"],"enriched")
        card=result["works"][0]
        self.assertEqual(card["synopsis"],identity_introduction(identity))
        self.assertIsNone(card["history"])
        self.assertIn("Giovanni Paisiello",card["synopsis"])

    def test_original_synopsis_is_saved_only_if_grounded(self):
        doc={"schema_version":1,"candidates":[{
            "id":"oa-index-fake-for-paid-path","source_key":"scala-season-2026-27",
            "official_url":"https://www.teatroallascala.org/it/stagione/2026-2027/opera/fixture-new-opera.html",
            "status":"needs_review"}]}
        identity={"title":"Fixture New Opera","composer":"Gaetano Donizetti","wikidata_id":"Q111",
                  "authority_url":"https://www.wikidata.org/wiki/Q111",
                  "wikipedia_url":"https://it.wikipedia.org/wiki/Anna_Bolena"}
        calls=[]
        def resolver(title):
            self.assertEqual(title,"fixture new opera")
            return identity
        def article(obj):
            return "La vicenda di Anna Bolena e dei suoi rapporti con Enrico VIII, " * 4
        def model(obj,text,*,api_key):
            calls.append(api_key)
            return ("Anna Bolena è al centro di una vicenda di potere, "
                    "rapporti difficili e scelte che cambiano il suo destino.")
        result,status=research(doc,{"schema_version":1,"works":[]},set(),
                               today=date(2026,11,20),resolve=resolver,
                               extract=article,generate=model,
            generate_history=lambda obj,text,*,api_key:{
                "librettist":"Giovanni Example","premiere_year":1830,
                "premiere_venue":"Teatro Example","premiere_city":"Milano",
                "sources":[obj["authority_url"],obj["wikipedia_url"]]},
            api_key="fake-key")
        self.assertEqual(calls,[])
        self.assertEqual(status[0]["status"],"enriched")
        self.assertEqual(result["works"][0]["composer"],"Gaetano Donizetti")
        self.assertIn("history",result["works"][0])
        self.assertNotIn("source_excerpt",result["works"][0])
        again,events=research(doc,result,set(),today=date(2026,11,21),
                              resolve=lambda x: (_ for _ in ()).throw(AssertionError("refetched")),
                              api_key="fake-key")
        self.assertEqual(again,result)
        self.assertEqual(events,[])

    def test_unseen_opera_research_rotates_fairly_with_six_candidates(self):
        rows=[{"id":f"unseen-{i:02d}","source_key":"scala-season-2026-27",
               "official_url":f"https://www.teatroallascala.org/it/stagione/2026-2027/opera/unknown-{i}.html",
               "status":"needs_review"} for i in range(6)]
        doc={"schema_version":1,"candidates":rows}
        existing={"schema_version":1,"works":[]}
        seen=set()
        for offset in range(12):
            day=date.fromordinal(date(2026,11,20).toordinal()+offset)
            batch=choose_candidates(doc,existing,set(),today=day)
            self.assertEqual(len(batch),3)
            seen.update(x["id"] for x in batch)
        self.assertEqual(seen,{x["id"] for x in rows})

    def test_never_search_outside_exact_approved_url(self):
        self.assertIsNone(official_title_hint({
            "source_key":"scala-season-2026-27",
            "official_url":"https://www.teatroallascala.org/it/stagione/2026-2027/opera/otello-anteprima-under30.html"}))
        self.assertIsNone(official_title_hint({
            "source_key":"arena-festival-2027",
            "official_url":"https://www.arena.it/arena-opera-festival/regolamento/"}))
if __name__=="__main__":
    unittest.main()
