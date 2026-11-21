"""Source-grounded history and combined prepublication enrichment regression."""
import unittest
from datetime import date
from urllib.parse import parse_qs, urlsplit

from scripts.work_history_research import wikidata_premiere
from scripts.auto_work_research import research


def claim(qid):
    return {"mainsnak": {"datavalue": {"value": {"id": qid}}}}


def fake_wikidata(url):
    args = parse_qs(urlsplit(url).query)
    ids = args["ids"][0].split("|")
    data = {
        "Q111": {"claims": {
            "P87": [claim("Q201")],
            "P1191": [{"mainsnak": {"datavalue": {
                "value": {"time": "+1830-12-26T00:00:00Z", "precision": 11}}}}],
            "P4647": [claim("Q301")]}},
        "Q201": {"labels": {"it": {"value": "Giovanni Example"}}},
        "Q301": {"labels": {"it": {"value": "Teatro Nuovo"}},
                 "claims": {"P131": [claim("Q401")]}},
        "Q401": {"labels": {"it": {"value": "Milano"}}},
    }
    return {"entities": {key: data[key] for key in ids}}


IDENTITY = {
    "title": "Fixture Opera", "composer": "Gaetano Donizetti",
    "wikidata_id": "Q111", "authority_url": "https://www.wikidata.org/wiki/Q111",
    "wikipedia_url": "https://it.wikipedia.org/wiki/Fixture_Opera",
    "wikipedia_title": "Fixture Opera", "title_candidate_count": 2,
}
CANDIDATE = {"id": "oa-index-new-fixture", "source_key": "scala-season-2026-27",
             "official_url": "https://www.teatroallascala.org/it/stagione/2026-2027/opera/fixture-opera.html",
             "status": "needs_review"}
ARTICLE = ("Fixture Opera, un titolo di repertorio.\nTrama\n"
           "Anna si innamora di Enrico. Enrico cerca di liberare Anna. "
           "I due personaggi devono confrontarsi con altri ostacoli a corte.\n"
           "Note\nAnna si innamora di Enrico.")


class WorkHistoryResearchTests(unittest.TestCase):
    def test_sources_complete_history_from_exact_qid(self):
        doc = wikidata_premiere(IDENTITY, fetch=fake_wikidata)
        self.assertEqual(doc["librettist"], "Giovanni Example")
        self.assertEqual(doc["premiere_year"], 1830)
        self.assertEqual(doc["premiere_venue"], "Teatro Nuovo")
        self.assertEqual(doc["premiere_city"], "Milano")
        self.assertEqual(doc["sources"], ["https://www.wikidata.org/wiki/Q111"])

    def test_missing_venue_or_city_is_not_invented(self):
        def incomplete(url):
            result = fake_wikidata(url)
            for v in result["entities"].values():
                if "claims" in v:
                    v["claims"].pop("P131", None)
            return result
        self.assertIsNone(wikidata_premiere(IDENTITY, fetch=incomplete))
        self.assertIsNone(wikidata_premiere({**IDENTITY, "wikidata_id": "bad"},
                                            fetch=fake_wikidata))

    def test_complete_plot_and_history_in_one_refresh(self):
        def resolve(title):
            self.assertEqual(title, "fixture opera")
            return IDENTITY
        result, statuses = research(
            {"candidates": [CANDIDATE]}, {"works": []}, {"fixture-opera"},
            today=date(2026, 11, 21), resolve=resolve, prepared={},
            extract=lambda _: ARTICLE, lookup_history=lambda _: wikidata_premiere(
                IDENTITY, fetch=fake_wikidata), allow_authority=True)
        self.assertEqual(statuses[0]["status"], "enriched")
        self.assertEqual(result["works"][0]["history"]["premiere_year"], 1830)
        self.assertIn("Anna", result["works"][0]["synopsis"])

    def test_partial_plot_is_cached_and_history_can_complete_later(self):
        result, statuses = research(
            {"candidates": [CANDIDATE]}, {"works": []}, {"fixture-opera"},
            today=date(2026, 11, 21), resolve=lambda _: IDENTITY,
            prepared={}, extract=lambda _: ARTICLE, lookup_history=lambda _: None,
            allow_authority=True)
        self.assertEqual(statuses[0]["reason"], "verified_premiere_history_unavailable")
        self.assertTrue(result["works"][0]["synopsis"])
        completed, outcomes = research(
            {"candidates": [CANDIDATE]}, result, {"fixture-opera"},
            today=date(2026, 11, 22), resolve=lambda _: IDENTITY,
            prepared={}, extract=lambda _: (_ for _ in ()).throw(
                AssertionError("cached plot should not be re-downloaded")),
            lookup_history=lambda _: wikidata_premiere(IDENTITY, fetch=fake_wikidata),
            allow_authority=True)
        self.assertEqual(outcomes[0]["status"], "enriched")
        self.assertEqual(completed["works"][0]["history"]["premiere_city"], "Milano")


if __name__ == "__main__":
    unittest.main()
