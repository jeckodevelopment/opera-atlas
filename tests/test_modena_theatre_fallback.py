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

    def test_wagner_work_and_two_modena_recite_pass_full_publication_gate(self):
        from datetime import date
        from scripts.auto_catalogue import official_identity_candidates,promote_new_works
        from scripts.publish_catalog_v2 import ROOT,REGISTRY
        from scripts.build_verified_catalog import MANIFEST
        from scripts.publish_work_editorial import EDITORIAL,HISTORY
        read=lambda path:json.loads(path.read_text(encoding="utf-8"))
        source=("https://www.teatrocomunalemodena.it/spettacolo/"
                "richard-wagner-der-fliegender-hollander-lolandese-volante/")
        detail=next(x for x in read(ROOT/"data/candidate-detail-evidence.json")["evidence"]
                    if x["source_url"]==source)
        candidate={"id":detail["candidate_id"],"source_key":KEY,
                   "official_url":source,"status":"needs_review"}
        rows={"schema_version":1,"evidence":[detail]}
        indexes={"schema_version":1,"candidates":[candidate]}
        ident=official_identity_candidates(rows,indexes,{"schema_version":1,"works":[]})
        verified=[x for x in ident["works"] if x["source_url"]==source]
        self.assertEqual(len(verified),1)
        self.assertEqual((verified[0]["title"],verified[0]["composer"]),
                         ("Der fliegende Holländer","Richard Wagner"))
        originals=read(MANIFEST)
        ids=read(REGISTRY)
        if any(x["title"]=="Der fliegende Holländer" and
               x["composer"]=="Richard Wagner" for x in ids["works"].values()):
            self.skipTest("canonical work already published by current refresh")
        after,reg,urls,editorial,history,report=promote_new_works(
            originals,ids,rows,indexes,ident,read(EDITORIAL),[],
            today=date(2026,11,22),history=read(HISTORY),require_image=True)
        self.assertEqual(report["new_works"],1,report)
        self.assertEqual(report["new_recite"],2,report)
        entry=next(p for p in after["productions"] if p["source_url"]==source)
        self.assertEqual(len(entry["dates"]),2)
        self.assertEqual(entry["title"],"Der fliegende Holländer")
        self.assertTrue(any(w["slug"]=="der-fliegende-hollander"
                            for w in reg["works"].values()))

    def test_veleno_exact_h4_work_identity_with_two_public_clocks(self):
        source="https://www.teatrocomunalemodena.it/spettacolo/gaia-aloisi-veleno/"
        html=(HTML
              .replace("<h1>Giuseppe Verdi – Macbeth</h1>",
                       "<h4>Gaia Aloisi – Veleno</h4>")
              .replace("<h4>Giuseppe Verdi – Macbeth</h4>",
                       "<p>Gaia Aloisi – Veleno</p>")
              .replace("30 Ottobre 2026","7 Maggio 2027")
              .replace("1 Novembre 2026","9 Maggio 2027")
              .replace("20:00","20:00")
              .replace("15:30","15:30"))
        self.assertEqual(parse_detail(html,url=source),(
            "Veleno","Gaia Aloisi","Teatro Comunale Pavarotti-Freni",
            [("2027-05-07","20:00"),("2027-05-09","15:30")]))
        self.assertEqual(len(parse_source_credited_opera_detail(KEY,source,html)),2)
        for invalid in (
            html.replace("Gaia Aloisi – Veleno","Gaia Aloisi – Altra opera"),
            html.replace("<p>Gaia Aloisi – Veleno</p>",
                         "<h4>Gaia Aloisi – Veleno</h4>"),
            html.replace("7 Maggio 2027 - 20:00",
                         "7 Maggio 2027 - orario da confermare")
                .replace("9 Maggio 2027 - 15:30",
                         "9 Maggio 2027 - orario da confermare"),
        ):
            with self.subTest(problem=invalid[-50:]),self.assertRaises(ValueError):
                parse_detail(invalid,url=source)
        with self.assertRaises(ValueError):
            parse_detail(html,url=URL)

    def test_nested_official_veleno_h4_and_sitewide_h1(self):
        source="https://www.teatrocomunalemodena.it/spettacolo/gaia-aloisi-veleno/"
        html=(HTML
              .replace("<h1>Giuseppe Verdi – Macbeth</h1>",
                       '<h4 class="entry-title"><span>Gaia Aloisi</span> – <strong>Veleno</strong></h4>')
              .replace("<h4>Giuseppe Verdi – Macbeth</h4>",
                       "<p>Gaia Aloisi – Veleno</p>")
              .replace("30 Ottobre 2026","7 Maggio 2027")
              .replace("1 Novembre 2026","9 Maggio 2027"))
        self.assertEqual(parse_detail(html,url=source),(
            "Veleno","Gaia Aloisi","Teatro Comunale Pavarotti-Freni",
            [("2027-05-07","20:00"),("2027-05-09","15:30")]))
        self.assertEqual(len(parse_source_credited_opera_detail(KEY,source,html)),2)
        # A site-wide H1 must not obscure the exact work-specific H4.
        self.assertEqual(parse_detail("<h1>Teatro Comunale</h1>"+html,url=source)[0],"Veleno")
        for tampered in (
            html.replace("<strong>Veleno</strong>","<strong>Opera diversa</strong>"),
            html+"<h4>Gaia Aloisi – Veleno</h4>",
            html.replace("Gaia Aloisi</span>","Compositore ignoto</span>"),
        ):
            with self.subTest(page=tampered[-100:]),self.assertRaises(ValueError):
                parse_detail(tampered,url=source)

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
