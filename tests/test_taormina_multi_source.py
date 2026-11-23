"""Taormina source identity, provenance and exclusion contracts."""
import json
import unittest

from opera_atlas.taormina_multi_source import SOURCES,eligible_detail,extract_index,parse_detail
from scripts.discover_season_indexes import CONFIG,validate_config,extract,eligible
from scripts.collect_candidate_details import parse_source_credited_opera_detail

NABUCCO="https://www.fondazione-taormina.it/eventi/7db81e44-6993-4ef1-803d-0dc31c52fb3c"
TRAVIATA="https://www.taorminaoperafestival.org/la-traviata-2025/"
ARTE="https://festivaltaorminarte.it/evento/nabucco/"

def event(title="Nabucco",genre="Opera lirica in 4 atti",
          credit="di Giuseppe Verdi",venue="Teatro Antico di Taormina",
          when="7 agosto 2026 ore 21:00"):
    return (f"<html><h1>{title}</h1><p>{genre}</p><p>{credit}</p>"
            f"<p>{venue}</p><p>{when}</p></html>")

class TaorminaMultiSourceTests(unittest.TestCase):
    def test_all_three_indexes_and_strict_first_party_urls(self):
        data=json.loads(CONFIG.read_text(encoding="utf-8"))
        validated={x["key"]:x for x in validate_config(data)}
        for key,(index,_) in SOURCES.items():
            self.assertEqual(validated[key]["url"],index)
        for key,url in (("taormina-fondazione-rolling-opera",NABUCCO),
                        ("taormina-opera-festival-rolling",TRAVIATA),
                        ("taormina-arte-rolling-opera",ARTE)):
            self.assertTrue(eligible_detail(key,url))
            self.assertTrue(eligible(key,url))
            self.assertFalse(eligible_detail(key,url.replace("https:","http:")))
            self.assertFalse(eligible_detail(key,url+"?preview=1"))
            self.assertFalse(eligible_detail(key,url+"#fragment"))
            self.assertFalse(eligible_detail(key,"https://evil.example/evento/nabucco/"))

    def test_each_index_returns_candidates_not_published_operas(self):
        for key,url in (("taormina-fondazione-rolling-opera",NABUCCO),
                        ("taormina-opera-festival-rolling",TRAVIATA),
                        ("taormina-arte-rolling-opera",ARTE)):
            index=SOURCES[key][0]
            html=f'<a href="{url}">Nabucco</a><a href="https://fake.example/evil">other</a>'
            self.assertEqual(extract_index(key,html,url=index),[url])
            self.assertEqual(extract(key,index,html,1),[url])

    def test_real_navigation_links_do_not_enter_opera_review(self):
        from opera_atlas.taormina_multi_source import FESTIVAL_NONPRODUCTION_SLUGS
        key="taormina-opera-festival-rolling"
        base="https://www.taorminaoperafestival.org/"
        self.assertGreaterEqual(len(FESTIVAL_NONPRODUCTION_SLUGS),15)
        for slug in FESTIVAL_NONPRODUCTION_SLUGS:
            self.assertFalse(eligible_detail(key,base+slug+"/"),slug)
        official=base+"la-grande-lirica-torna-al-teatro-antico-di-taormina-con-la-traviata-secondo-castiglione/"
        self.assertTrue(eligible_detail(key,official))
        html='<nav>'+''.join(
            '<a href="/'+slug+'/">Voce menu</a>'
            for slug in FESTIVAL_NONPRODUCTION_SLUGS
        )+'</nav><a href="'+official+'">La traviata</a>'
        self.assertEqual(extract_index(key,html,url=base),[official])

    def test_nabucco_with_explicit_details_can_enter_canonical_pipeline(self):
        title,composer,venue,rows=parse_detail(
            "taormina-fondazione-rolling-opera",event(),url=NABUCCO)
        self.assertEqual((title,composer,venue),("Nabucco","Giuseppe Verdi",
                                                 "Teatro Antico di Taormina"))
        self.assertEqual(rows,[("2026-08-07","21:00")])
        facts=parse_source_credited_opera_detail(
            "taormina-fondazione-rolling-opera",NABUCCO,event())
        self.assertEqual(facts[0]["starts_at"],"2026-08-07T21:00:00+02:00")

    def test_other_organizer_same_work_yields_same_canonical_identity(self):
        for key,url in (("taormina-opera-festival-rolling",TRAVIATA),
                        ("taormina-arte-rolling-opera",ARTE)):
            result=parse_detail(key,event(),url=url)
            self.assertEqual(result,("Nabucco","Giuseppe Verdi",
                                      "Teatro Antico di Taormina",[("2026-08-07","21:00")]))

    def test_future_seasons_are_not_hardcoded(self):
        r=parse_detail("taormina-arte-rolling-opera",
                       event(when="8 agosto 2027 ore 21:15"),url=ARTE)
        self.assertEqual(r[3],[("2027-08-08","21:15")])

    def test_gala_other_venue_and_missing_facts_fail_closed(self):
        cases=(event(title="Bellini Opera Gala"),
               event(title="Nabucco concerto"),
               event(genre="Musica dal vivo"),
               event(credit="Direttore artistico: Mario Rossi"),
               event(venue="Teatro Nazarena Taormina"),
               event(venue="Palazzo dei Congressi"),
               event(when="7 agosto 2026"),
               event(when="38 agosto 2026 ore 21:00"),
               event(title="Nabucco e La traviata"),
               event(title="Cavalleria rusticana / Pagliacci"))
        for data in cases:
            with self.subTest(data=data[:110]),self.assertRaises(ValueError):
                parse_detail("taormina-fondazione-rolling-opera",data,url=NABUCCO)

    def test_real_official_nabucco_notice_is_not_composer_or_clock_evidence(self):
        html=('<h1>Teatro Antico 2026 – "Nabucco" — Coro Lirico Siciliano</h1>'
              '<p>07 agosto 2026</p><p>Teatro Antico di Taormina</p>')
        with self.assertRaises(ValueError):
            parse_detail("taormina-fondazione-rolling-opera",html,url=NABUCCO)

if __name__=="__main__":
    unittest.main()
