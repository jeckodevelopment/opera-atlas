"""The Savona evergreen candidate must be collected, not just discovered."""
import unittest
from datetime import date

from opera_atlas.controlled_fetch import FetchResult
from opera_atlas.savona_opera_giocosa_parser import URL
from scripts.collect_candidate_details import collect
from scripts.auto_catalogue import split_verified_season

KEY="savona-giocosa-rolling-opera"
HTML="""<main>
<h2>Stagione lirica autunnale 2026</h2>
<p>Opera</p><div>23 Ottobre - ore 20:00 25 Ottobre - ore 15:30
Teatro Chiabrera Savona La Traviata di Giuseppe Verdi</div>
<p>Opera</p><div>7 Novembre - ore 18:00 Teatro Chiabrera Savona
I salvatori della mezzanotte di Daniele Furlati</div>
<p>Concerto</p><div>13 Dicembre - ore 21:00 Teatro Chiabrera Savona
Te Deum di Marc-Antoine Charpentier</div>
<h2>Stagione lirica estiva 2026</h2>
<p>Opera</p><div>6 Giugno - ore 18:00 Teatro Chiabrera Savona
L’arca di Noè di Benjamin Britten</div>
<p>Opera</p><div>25 Giugno - ore 21:15 Fortezza del Priàmar Savona
Nabucco di Giuseppe Verdi</div>
</main>"""

class SavonaCandidateDispatchTests(unittest.TestCase):
    def test_official_homepage_produces_multiple_canonical_work_evidence(self):
        candidates={"schema_version":1,"candidates":[{
            "id":"oa-index-savona-test-detail-dispatch","source_key":KEY,
            "official_url":URL,"status":"needs_review"}]}
        visited=[]
        def official(db,*,source_id,url,network_enabled):
            visited.append(url)
            return FetchResult(url,HTML,"f"*64,len(HTML))
        result,health=collect(
            candidates,{"schema_version":1,"evidence":[]},
            network_enabled=True,fetcher=official,
            today=date(2026,11,22))
        self.assertEqual(visited,[URL])
        self.assertEqual(len(health),1)
        self.assertEqual(health[0]["outcome"],"facts_found",health)
        row=result["evidence"][0]
        self.assertEqual(row["status"],"needs_editorial_review")
        facts=row["event_facts"]
        self.assertEqual(len(facts),4)
        self.assertEqual({x["event_title"].casefold() for x in facts},
                         {"la traviata","i salvatori della mezzanotte",
                          "l’arca di noè"})
        self.assertTrue(all(x["venue"]=="Teatro Chiabrera" for x in facts))
        self.assertTrue(all(x["starts_at"].endswith(("+01:00","+02:00"))
                            for x in facts))
        self.assertEqual(len(split_verified_season(row)),3)

    def test_page_with_no_valid_opera_never_promotes_concert(self):
        candidate={"schema_version":1,"candidates":[{
            "id":"oa-index-savona-nonopera","source_key":KEY,
            "official_url":URL,"status":"needs_review"}]}
        html="""<h2>Stagione lirica autunnale 2027</h2>
        <p>Concerto 13 Dicembre - ore 21:00 Teatro Chiabrera Savona
        Te Deum di Marc-Antoine Charpentier</p>"""
        def official(db,*,source_id,url,network_enabled):
            return FetchResult(url,html,"a"*64,len(html))
        result,health=collect(candidate,{"schema_version":1,"evidence":[]},
                              network_enabled=True,fetcher=official,
                              today=date(2026,11,22))
        self.assertEqual(health[0]["outcome"],"unavailable_or_unstructured")
        self.assertEqual(result["evidence"],[])

if __name__=="__main__":
    unittest.main()
