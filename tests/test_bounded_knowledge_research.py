"""Regressions for large Wikidata records and bounded Wikipedia plot reads."""
import unittest
from urllib.parse import parse_qs, urlsplit

from scripts.auto_work_research import resolve_identity, wiki_excerpt
from scripts.work_history_research import wikidata_premiere
from scripts.work_plot_generator import synopsis_from_wikipedia_plot


def claim(qid):
    return {"mainsnak": {"datavalue": {"value": {"id": qid}}}}


class BoundedKnowledgeAPITests(unittest.TestCase):
    def test_oversized_opera_identity_uses_scoped_claims(self):
        calls=[]
        def fake(url):
            p=parse_qs(urlsplit(url).query)
            action=p["action"][0]
            calls.append((action,p))
            if action=="wbsearchentities":
                return {"search":[{"id":"Q111","label":"Anna Bolena"}]}
            if action=="wbgetentities":
                ids=p["ids"][0]
                if ids=="Q111" and "claims" in p["props"][0]:
                    raise ValueError("external knowledge response too large")
                if ids=="Q111":
                    return {"entities":{"Q111":{"labels":{"it":{"value":"Anna Bolena"}},
                        "sitelinks":{"itwiki":{"title":"Anna Bolena"}}}}}
                if ids=="Q222":
                    return {"entities":{"Q222":{"labels":{
                        "it":{"value":"Gaetano Donizetti"}}}}}
            if action=="wbgetclaims":
                prop=p["property"][0]
                return {"claims":{prop:[claim({
                    "P31":"Q1344","P86":"Q222"}.get(prop,"Q999"))]
                    if prop in ("P31","P86") else []}}
            raise AssertionError(url)
        result=resolve_identity("Anna Bolena",composer_hint="Gaetano Donizetti",
                                fetch=fake)
        self.assertEqual(result["wikidata_id"],"Q111")
        self.assertEqual(result["composer"],"Gaetano Donizetti")
        self.assertEqual({p["property"][0] for action,p in calls
                          if action=="wbgetclaims"},{"P31","P7937","P86"})

    def test_composer_qualified_search_keeps_exact_title_gate(self):
        def fake(url):
            p=parse_qs(urlsplit(url).query)
            if p["action"][0]=="wbsearchentities":
                if "Gaetano Donizetti" in p["search"][0]:
                    return {"search":[{"id":"Q111","label":"Anna Bolena"}]}
                return {"search":[]}
            if "ids=Q111" in url:
                return {"entities":{"Q111":{"labels":{"it":{"value":"Anna Bolena"}},
                    "claims":{"P31":[claim("Q1344")],"P86":[claim("Q222")]}}}}
            if "ids=Q222" in url:
                return {"entities":{"Q222":{"labels":{"it":{"value":"Gaetano Donizetti"}}}}}
            raise AssertionError(url)
        self.assertEqual(resolve_identity("Anna Bolena",
                             composer_hint="Gaetano Donizetti",
                             fetch=fake)["wikidata_id"],"Q111")

    def test_wikipedia_only_reads_named_plot_section(self):
        calls=[]
        def fake(url):
            p=parse_qs(urlsplit(url).query)
            calls.append(p)
            self.assertEqual(p["action"],["parse"])
            self.assertEqual(p["page"],["Anna Bolena"])
            if p["prop"]==["sections"]:
                return {"parse":{"sections":[{"index":"1","line":"Storia"},
                    {"index":"4","line":"Trama"},{"index":"5","line":"Note"}]}}
            self.assertEqual(p["section"],["4"])
            return {"parse":{"text":{"*":(
                "<div><p>Anna si innamora di Enrico. Enrico cerca di liberare "
                "Anna dalla prigionia. La corte osserva le conseguenze e i "
                "protagonisti affrontano la situazione.</p>"
                "<sup>[2]</sup></div>")}}}
        excerpt=wiki_excerpt({"wikipedia_title":"Anna Bolena"},fetch=fake)
        self.assertTrue(excerpt.startswith("== Trama =="))
        self.assertEqual(len(calls),2)
        self.assertNotIn("[2]",excerpt)
        self.assertIn("Anna prova amore per Enrico",
                      synopsis_from_wikipedia_plot(excerpt))

    def test_no_ambiguous_wikipedia_section_fallback(self):
        def fake(url):
            return {"parse":{"sections":[{"line":"Trama","index":"1"},
                                          {"line":"Trama","index":"2"}]}}
        self.assertIsNone(wiki_excerpt({"wikipedia_title":"Test"},fetch=fake))

    def test_oversized_historical_entity_uses_claims_by_property(self):
        calls=[]
        def fake(url):
            p=parse_qs(urlsplit(url).query)
            action=p["action"][0]
            if action=="wbgetclaims":
                prop=p["property"][0]
                calls.append(prop)
                if prop=="P87": value=[claim("Q201")]
                elif prop=="P4647": value=[claim("Q301")]
                else: value=[{"mainsnak":{"datavalue":{"value":{
                    "time":"+1830-12-26T00:00:00Z"}}}}]
                return {"claims":{prop:value}}
            if p.get("ids")==["Q111"]:
                raise ValueError("external knowledge response too large")
            refs={
                "Q201":{"labels":{"it":{"value":"Giovanni Example"}}},
                "Q301":{"labels":{"it":{"value":"Teatro Nuovo"}},
                        "claims":{"P131":[claim("Q401")]}},
                "Q401":{"labels":{"it":{"value":"Milano"}}}}
            return {"entities":{qid:refs[qid] for qid in
                                p["ids"][0].split("|")}}
        result=wikidata_premiere({"wikidata_id":"Q111"},fetch=fake)
        self.assertEqual(result["premiere_city"],"Milano")
        self.assertEqual(set(calls),{"P87","P1191","P4647"})


if __name__=="__main__":
    unittest.main()
