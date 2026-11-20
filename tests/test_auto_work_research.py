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

    def test_canonical_identity_and_missing_key_do_not_invoke_external_api(self):
        doc={"schema_version":1,"candidates":[CANDIDATE]}
        calls=[]
        def resolver(title):
            calls.append(title)
            return None
        result,status=research(doc,{"schema_version":1,"works":[]},set(),
                               today=date(2026,11,20),resolve=resolver,api_key="")
        self.assertEqual(result["works"],[])
        self.assertEqual(calls,[])
        self.assertEqual(status[0]["status"],"model_not_configured")

    def test_original_synopsis_is_saved_only_if_grounded(self):
        doc={"schema_version":1,"candidates":[CANDIDATE]}
        identity={"title":"Anna Bolena","composer":"Gaetano Donizetti","wikidata_id":"Q111",
                  "authority_url":"https://www.wikidata.org/wiki/Q111",
                  "wikipedia_url":"https://it.wikipedia.org/wiki/Anna_Bolena"}
        calls=[]
        def resolver(title):
            self.assertEqual(title,"anna bolena")
            return identity
        def article(obj):
            return "La vicenda di Anna Bolena e dei suoi rapporti con Enrico VIII, " * 4
        def model(obj,text,*,api_key):
            calls.append(api_key)
            return ("Anna Bolena è al centro di una vicenda di potere, "
                    "rapporti difficili e scelte che cambiano il suo destino.")
        result,status=research(doc,{"schema_version":1,"works":[]},set(),
                               today=date(2026,11,20),resolve=resolver,
                               extract=article,generate=model,api_key="fake-key")
        self.assertEqual(calls,["fake-key"])
        self.assertEqual(status[0]["status"],"enriched")
        self.assertEqual(result["works"][0]["composer"],"Gaetano Donizetti")
        self.assertNotIn("source_excerpt",result["works"][0])
        again,events=research(doc,result,set(),today=date(2026,11,21),
                              resolve=lambda x: (_ for _ in ()).throw(AssertionError("refetched")),
                              api_key="fake-key")
        self.assertEqual(again,result)
        self.assertEqual(events,[])

    def test_never_search_outside_exact_approved_url(self):
        self.assertIsNone(official_title_hint({
            "source_key":"scala-season-2026-27",
            "official_url":"https://www.teatroallascala.org/it/stagione/2026-2027/opera/otello-anteprima-under30.html"}))
        self.assertIsNone(official_title_hint({
            "source_key":"arena-festival-2027",
            "official_url":"https://www.arena.it/arena-opera-festival/regolamento/"}))
if __name__=="__main__":
    unittest.main()
