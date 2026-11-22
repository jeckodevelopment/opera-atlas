"""Theatre-operated Modena season fallback: official-only links and exact recite."""
import json
import unittest

from opera_atlas.modena_teatro_parser import parse_detail
from scripts.discover_season_indexes import (
    CONFIG,validate_config,eligible,extract
)
from scripts.collect_candidate_details import parse_source_credited_opera_detail

URL="https://www.teatrocomunalemodena.it/spettacolo/giuseppe-verdi-macbeth-2/"
SEASON="https://www.teatrocomunalemodena.it/opera/"
KEY="modena-teatro-opera-2026-27"
HTML="""<h1>Giuseppe Verdi – Macbeth</h1>
<h4>venerdì 30 Ottobre 2026 - 20:00</h4>
<h6>Altre date:</h6>
<p>domenica 1 Novembre 2026 - 15:30</p>
<h4>Giuseppe Verdi – Macbeth</h4>
<p>Teatro Comunale Pavarotti-Freni</p>
<p>venerdì 30 Ottobre 2026 - 20:00</p>
<h6>Altre date:</h6>
<p>domenica 1 Novembre 2026 - 15:30</p>
<a>Acquista online</a>
<p>Informazioni biglietti, artisti e cast</p>"""

class ModenaTheatreFallbackTests(unittest.TestCase):
    def test_first_party_approved_season_and_details_only(self):
        config=validate_config(json.loads(CONFIG.read_text(encoding="utf-8")))
        source=next(s for s in config if s["key"]==KEY)
        self.assertEqual(source["url"],SEASON)
        self.assertTrue(eligible(KEY,URL))
        self.assertFalse(eligible(KEY,URL+"?ref=ad"))
        self.assertFalse(eligible(KEY,URL.replace("www.teatrocomunalemodena.it","example.com")))
        links="".join(f'<a href="/spettacolo/opera-{n}/">Opera {n}</a>' for n in range(11))
        self.assertEqual(len(extract(KEY,SEASON,"<h1>Spettacoli 2026/2027</h1>"+links,11)),11)
        with self.assertRaises(ValueError):
            extract(KEY,SEASON,"<h1>Spettacoli 2026/2027</h1>"+links[:-20],11)

    def test_exact_dates_from_official_work_page(self):
        self.assertEqual(parse_detail(HTML,url=URL),(
            "Macbeth","Giuseppe Verdi","Teatro Comunale Pavarotti-Freni",
            [("2026-10-30","20:00"),("2026-11-01","15:30")]))
        facts=parse_source_credited_opera_detail(KEY,URL,HTML)
        self.assertEqual(len(facts),2)
        self.assertEqual([x["date"] for x in facts],["2026-10-30","2026-11-01"])

    def test_historic_wagner_dutchman_exact_bilingual_identity(self):
        from scripts.auto_catalogue import normalize_source_seed_trieste_genre
        from scripts.publish_catalog_v2 import slugify
        from scripts.publish_work_posters import load_archival_art
        source=("https://www.teatrocomunalemodena.it/spettacolo/"
                "richard-wagner-der-fliegender-hollander-lolandese-volante/")
        html=HTML.replace("Giuseppe Verdi – Macbeth",
                          "Richard Wagner – Der fliegende Holländer (L’olandese volante)")
        self.assertEqual(parse_detail(html,url=source)[:3],(
            "Der fliegende Holländer","Richard Wagner",
            "Teatro Comunale Pavarotti-Freni"))
        seed={"source_key":KEY,"source_url":source,
              "title":"Der fliegende Holländer","composer":"Richard Wagner"}
        original=[{"event_title":"Der fliegende Holländer (L’olandese volante)",
                   "composer":"Richard Wagner","date":"2026-11-20",
                   "venue":"Teatro Comunale Pavarotti-Freni",
                   "starts_at":"2026-11-20T20:00:00+01:00"}]
        normalized=normalize_source_seed_trieste_genre(original,KEY,source,seed)
        self.assertEqual(normalized[0]["event_title"],seed["title"])
        self.assertEqual(normalized[0]["starts_at"],original[0]["starts_at"])
        self.assertEqual(normalize_source_seed_trieste_genre(original,KEY,
                         source.replace("www.","another."),seed),original)
        wrong=[{**original[0],"composer":"Pierre-Louis Dietsch"}]
        self.assertEqual(normalize_source_seed_trieste_genre(wrong,KEY,source,seed),wrong)
        slug=slugify(seed["title"])
        self.assertEqual(slug,"der-fliegende-hollander")
        art=load_archival_art({slug})[slug]
        self.assertIn("Libretto_Der_fliegende_Holl",art["source_url"])
        self.assertEqual(art["kind"],"archival_work_image")
        self.assertIn("Public domain",art["license"])

    def test_no_unverified_authority_or_dates(self):
        for broken in (
            HTML.replace("Giuseppe Verdi – Macbeth","Macbeth"),
            HTML.replace("30 Ottobre 2026","31 Ottobre 2026"),
            HTML.replace("Teatro Comunale Pavarotti-Freni","Teatro di Altrove"),
            HTML.replace("Giuseppe Verdi – Macbeth","Giuseppe Verdi / Another – Macbeth"),
        ):
            with self.assertRaises(ValueError):
                parse_detail(broken,url=URL)
        with self.assertRaises(ValueError):
            parse_detail(HTML,url=URL.replace("https://","http://"))

if __name__=="__main__":
    unittest.main()
