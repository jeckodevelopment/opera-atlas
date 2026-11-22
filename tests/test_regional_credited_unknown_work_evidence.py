"""Regional opera title+composer can be verified before work exists in Atlas."""
import unittest
from datetime import date
from opera_atlas.controlled_fetch import FetchResult
from scripts.collect_candidate_details import (
    parse_source_credited_opera_detail,collect)

PISA_URL="https://teatrodipisa.it/spettacolo/dido-and-aeneas/"
VERONA_URL="https://www.arena.it/teatro-filarmonico-verona/2027/fidelio/"
PISA_HTML=(
    "<h1>Dido and Aeneas</h1><p>Musica di Henry Purcell</p>"
    "<h3>Date:</h3><h4>23 Ottobre 2026 20:30</h4>"
    "<h4>25 Ottobre 2026 15:30</h4><h3>Allegati:</h3>"
    "<footer>Fondazione Teatro di Pisa</footer>")
VERONA_HTML=(
    "<h1>Fidelio</h1><div>Location Teatro Filarmonico</div>"
    "<div>Tipo di spettacolo Opera</div><p>Musica Ludwig van Beethoven</p>"
    "<h2>Prossimi spettacoli</h2>"
    "<p>domenica 11 aprile 2027 ore 15:30</p>"
    "<p>martedì 13 aprile 2027 ore 20:00</p>"
    "<p>giovedì 15 aprile 2027 ore 20:00</p>"
    "<p>sabato 17 aprile 2027 ore 18:00</p>"
    "<h2>Cast Regia</h2>")

class FirstPartyRegionalCreditBridgeTests(unittest.TestCase):
    def test_pisa_unknown_work_preserves_independently_credited_identity(self):
        facts=parse_source_credited_opera_detail(
            "pisa-verdi-opera-2026-27",PISA_URL,PISA_HTML)
        self.assertEqual(len(facts),2)
        self.assertEqual({r["composer"] for r in facts},{"Henry Purcell"})
        self.assertEqual({r["event_title"] for r in facts},{"Dido and Aeneas"})
        self.assertEqual({r["venue"] for r in facts},{"Teatro Verdi"})
        self.assertEqual([r["date"] for r in facts],
                         ["2026-10-23","2026-10-25"])

    def test_verona_not_arena_and_exact_time(self):
        facts=parse_source_credited_opera_detail(
            "filarmonico-verona-opera-2027",VERONA_URL,VERONA_HTML)
        self.assertEqual(len(facts),4)
        self.assertEqual({r["venue"] for r in facts},{"Teatro Filarmonico"})
        self.assertEqual({r["composer"] for r in facts},{"Ludwig van Beethoven"})
        self.assertTrue(all("+02:00" in r["starts_at"] for r in facts))

    def test_unknown_work_evidence_is_retained_per_candidate_without_publication(self):
        candidate={
            "schema_version":1,"candidates":[{
                "id":"source-credited-new-opera",
                "source_key":"pisa-verdi-opera-2026-27",
                "official_url":PISA_URL,
                "status":"needs_review"}]}
        def fake(db,*,source_id,url,network_enabled):
            self.assertEqual(url,PISA_URL)
            return FetchResult(url,PISA_HTML,"b"*64,len(PISA_HTML))
        found,health=collect(
            candidate,{"schema_version":1,"evidence":[]},
            network_enabled=True,fetcher=fake,today=date(2026,11,22))
        self.assertEqual(health[0]["outcome"],"facts_found",health)
        self.assertEqual(len(found["evidence"]),1)
        self.assertEqual(len(found["evidence"][0]["event_facts"]),2)
        self.assertEqual(found["evidence"][0]["status"],"needs_editorial_review")

    def test_wrong_composer_or_source_cannot_bridge_identity(self):
        with self.assertRaisesRegex(ValueError,"composer"):
            parse_source_credited_opera_detail(
                "pisa-verdi-opera-2026-27",PISA_URL,
                PISA_HTML.replace("Henry Purcell","Giuseppe Verdi"))
        with self.assertRaisesRegex(ValueError,"source"):
            parse_source_credited_opera_detail(
                "pisa-verdi-opera-2026-27",
                "https://untrusted.example/spettacolo/dido-and-aeneas/",
                PISA_HTML)
        self.assertEqual(parse_source_credited_opera_detail(
            "unapproved-city-opera-2027",PISA_URL,PISA_HTML),[])

if __name__=="__main__":
    unittest.main()
