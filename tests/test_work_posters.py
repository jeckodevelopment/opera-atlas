"""A newly published opera must have a safe cover source and resilient fallback."""
import json
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts import publish_work_posters as posters
from opera_atlas.controlled_fetch import FetchResult

class PosterPublicationTests(unittest.TestCase):
    def test_extracts_explicit_official_poster_with_credit(self):
        url="https://www.teatrolafenice.it/event/adriana-lecouvreur/"
        html='''<html><head>
        <meta property="og:image" content="/wp-content/uploads/adriana-lecouvreur-poster.jpg">
        <meta property="og:image:alt" content="Adriana Lecouvreur - locandina">
        <meta property="og:image:width" content="800">
        <meta property="og:image:height" content="1200">
        </head></html>'''
        got=posters.extract_official_poster(html,url,"Adriana Lecouvreur")
        self.assertEqual(got["kind"],"official_production_image")
        self.assertEqual(got["image_url"],
                         "https://www.teatrolafenice.it/wp-content/uploads/adriana-lecouvreur-poster.jpg")
        self.assertEqual(got["source_url"],url)
        self.assertIn("teatro",got["credit"])

    def test_unrelated_open_graph_people_and_concerts_never_pass_for_work_posters(self):
        # Observed real upstream metadata: conductor portraits and unrelated
        # symphonic concerts appeared on official opera production pages.
        bad=[
            ("Anna Bolena","https://www.teatroallascala.org/static/upload/cia/ciampa-2-scaled.jpg"),
            ("Don Quichotte","https://www.teatroallascala.org/static/upload/ber/bertrand-de-billy.jpg"),
            ("I puritani","https://www.teatroallascala.org/static/upload/202/2025-concerto-fabio-luisi.jpg"),
            ("Macbeth","https://www.teatroallascala.org/static/upload/202/2025-filarmonica-con-chung.jpg"),
            ("Nixon in China","https://www.teatroallascala.org/static/upload/ken/kent-nagano---symphonie-de-beethoven.jpg"),
        ]
        for work,image_url in bad:
            with self.subTest(work=work):
                self.assertFalse(posters.image_matches_work(image_url,work))
                html=f'<meta property="og:image" content="{image_url}">'
                self.assertIsNone(posters.extract_official_poster(
                    html,"https://www.teatroallascala.org/it/stagione/2026-2027/opera/macbeth.html",work))
        self.assertTrue(posters.image_matches_work(
            "https://www.teatroallascala.org/static/upload/la-/la-boheme--7-.jpg","La bohème"))

    def test_seven_recently_published_works_have_real_archival_fallbacks(self):
        required={"al-cavallino-bianco","il-pipistrello","partenope",
                  "don-quichotte","norma","nozze-istriane","adriana-lecouvreur"}
        archive=posters.load_archival_art(required)
        self.assertEqual(set(archive),required)
        for slug,record in archive.items():
            with self.subTest(work=slug):
                self.assertEqual(record["kind"],"archival_work_image")
                self.assertTrue(record["image_url"].startswith(
                    "https://commons.wikimedia.org/wiki/Special:Redirect/file/"))
                self.assertTrue(record["source_url"].startswith(
                    "https://commons.wikimedia.org/wiki/File:"))
                self.assertTrue(record["credit"])
                self.assertTrue(record["license"])
                self.assertTrue(any(word in record["alt"].lower() for word in ("storico","storica","archivio")))

    def test_never_accepts_logos_trackers_unsafe_hosts_or_landscape_banners(self):
        url="https://www.teatrolafenice.it/event/norma/"
        bad=[
            '<meta property="og:image" content="http://www.teatrolafenice.it/poster.jpg">',
            '<meta property="og:image" content="https://tracking.example/poster.jpg">',
            '<meta property="og:image" content="https://www.teatrolafenice.it/logo.png">',
            '<meta property="og:image" content="https://www.teatrolafenice.it/poster.svg">',
            '<meta property="og:image" content="https://www.teatrolafenice.it/poster.jpg" />'
            '<meta property="og:image:width" content="1600">'
            '<meta property="og:image:height" content="600">',
        ]
        for html in bad:
            with self.subTest(html=html):
                self.assertIsNone(posters.extract_official_poster(html,url,"Norma"))
        self.assertIsNone(posters.allowed_image_url(
            "https://www.teatrolafenice.it.evil.example/x.jpg",url))
        self.assertIsNone(posters.allowed_image_url(
            "https://www.teatrolafenice.it:8443/poster.jpg",url))

    def test_publishes_one_image_record_per_canonical_work_not_candidates(self):
        with TemporaryDirectory() as temp:
            folder=Path(temp)
            stored=folder/"evidence.json"
            published=folder/"work-posters.json"
            health=folder/"health.json"
            catalogue=[
                {"slug":"adriana-lecouvreur","work_id":"oa-w-000033",
                 "title":"Adriana Lecouvreur","source_key":"fenice-opera-2026-27",
                 "official_root":"https://www.teatrolafenice.it/",
                 "source_url":"https://www.teatrolafenice.it/event/adriana-lecouvreur/"},
                {"slug":"norma","work_id":"oa-w-000031","title":"Norma",
                 "source_key":"fenice-opera-2026-27",
                 "official_root":"https://www.teatrolafenice.it/",
                 "source_url":"https://www.teatrolafenice.it/event/normatebar/"},
            ]
            html='''<meta property="og:image" content="/wp-content/uploads/adriana-lecouvreur-poster.jpg">
            <meta property="og:image:width" content="700">
            <meta property="og:image:height" content="1000">'''
            calls=[]
            def mock(db,*,source_id,url,network_enabled):
                calls.append(url)
                if "adriana" in url:
                    return FetchResult(url,html,"x"*64,len(html))
                return FetchResult(url,"<html><head></head></html>","y"*64,26)
            class FakeDB:
                def execute(self,*a,**k):
                    class Cursor:
                        def fetchone(self):return {"id":1}
                    return Cursor()
                def close(self):pass
            with patch.object(posters,"EVIDENCE",stored),patch.object(posters,"OUTPUT",published),\
                 patch.object(posters,"HEALTH",health),patch.object(posters,"canonical_sources",return_value=catalogue),\
                 patch.object(posters,"connect",return_value=FakeDB()),patch.object(posters,"migrate"):
                result=posters.publish(network_enabled=True,fetcher=mock,
                                       today=date(2026,11,21),max_pages=2)
                self.assertEqual(result["works"]["oa-w-000033"]["kind"],
                                 "official_production_image")
                self.assertEqual(result["works"]["oa-w-000031"]["kind"],
                                 "archival_work_image")
                self.assertEqual(len(calls),2)
                self.assertTrue(published.exists())
                evidence=json.loads(stored.read_text())
                self.assertEqual(len(evidence["posters"]),1)
                posters.publish(network_enabled=True,fetcher=mock,
                                today=date(2026,11,21),max_pages=2)
                self.assertEqual(len(calls),2) # no repeat within cooldown

    def test_anna_bolena_and_leoncavallo_receive_distinct_archival_images(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            with patch.object(posters,"EVIDENCE",root/"empty-evidence.json"),\
                 patch.object(posters,"OUTPUT",root/"work-posters.json"),\
                 patch.object(posters,"HEALTH",root/"health.json"),\
                 patch.object(posters,"connect"),patch.object(posters,"migrate"),\
                 patch.object(posters,"canonical_sources",return_value=[]):
                result=posters.publish(network_enabled=False,max_pages=0)
        anna=result["works"]["oa-w-000035"]
        leoncavallo=result["works"]["oa-w-000007"]
        puccini=result["works"]["oa-w-000024"]
        self.assertEqual(anna["kind"],"archival_work_image")
        self.assertIn("Anna_Bolena",anna["image_url"])
        self.assertEqual(leoncavallo["kind"],"archival_work_image")
        self.assertIn("Leoncavallo",leoncavallo["image_url"])
        self.assertNotEqual(leoncavallo["image_url"],puccini.get("image_url"))
        self.assertEqual(puccini["kind"],"original_editorial_cover")

    def test_retries_old_cooldowns_when_poster_policy_changes(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            source_url="https://www.teatroallascala.org/it/stagione/2026-2027/opera/anna-bolena.html"
            (root/"evidence.json").write_text(json.dumps({
                "schema_version":2,"posters":{},
                "checks":{source_url:{"retry_after":"2026-11-27"}}}),encoding="utf-8")
            calls=[]
            class FakeDB:
                def execute(self,*args,**kwargs):
                    class Cursor:
                        def fetchone(self):return {"id":1}
                    return Cursor()
                def close(self):pass
            def fetch(db,*,source_id,url,network_enabled):
                calls.append(url)
                return FetchResult(url,"<html></html>","x"*64,13)
            with patch.object(posters,"EVIDENCE",root/"evidence.json"),\
                 patch.object(posters,"OUTPUT",root/"work-posters.json"),\
                 patch.object(posters,"HEALTH",root/"health.json"),\
                 patch.object(posters,"connect",return_value=FakeDB()),\
                 patch.object(posters,"migrate"),\
                 patch.object(posters,"canonical_sources",return_value=[{
                     "slug":"anna-bolena","work_id":"oa-w-000035",
                     "title":"Anna Bolena","source_key":"scala",
                     "official_root":"https://www.teatroallascala.org/",
                     "source_url":source_url}]):
                posters.publish(network_enabled=True,fetcher=fetch,today=date(2026,11,21),max_pages=1)
                self.assertEqual(calls,[source_url])
                saved=json.loads((root/"evidence.json").read_text())
                self.assertEqual(saved["checks"][source_url]["retry_after"],"2026-11-23")
                self.assertEqual(saved["checks"][source_url]["policy_version"],posters.POSTER_POLICY_VERSION)
                posters.publish(network_enabled=True,fetcher=fetch,today=date(2026,11,21),max_pages=1)
                self.assertEqual(len(calls),1)

    def test_twitter_specific_image_can_replace_unrelated_open_graph(self):
        html='''<meta property="og:image" content="/static/upload/con/conductor.jpg">
        <meta name="twitter:image" content="/static/upload/ann/anna-bolena-poster.jpg">'''
        got=posters.extract_official_poster(
            html,"https://www.teatroallascala.org/it/stagione/2026-2027/opera/anna-bolena.html",
            "Anna Bolena")
        self.assertIsNotNone(got)
        self.assertTrue(got["image_url"].endswith("anna-bolena-poster.jpg"))

    def test_homonymous_operas_get_distinct_permanent_poster_identities(self):
        from scripts.publish_catalog_v2 import REGISTRY
        works=list(json.loads(REGISTRY.read_text(encoding="utf-8"))["works"].values())
        duplicates=[w for w in works if w["slug"]=="la-boheme"]
        self.assertEqual(len(duplicates),2)
        self.assertNotEqual(duplicates[0]["id"],duplicates[1]["id"])
        # Real feed must contain a distinct entry for *every* canonical work
        # and must not silently merge the two La bohème composers.
        with TemporaryDirectory() as temp:
            root=Path(temp)
            with patch.object(posters,"EVIDENCE",root/"empty-evidence.json"),\
                 patch.object(posters,"OUTPUT",root/"work-posters.json"),\
                 patch.object(posters,"HEALTH",root/"health.json"),\
                 patch.object(posters,"connect"),patch.object(posters,"migrate"),\
                 patch.object(posters,"canonical_sources",return_value=[]):
                result=posters.publish(network_enabled=False,max_pages=0)
        self.assertEqual(result["schema_version"],2)
        self.assertEqual(len(result["works"]),len(works))
        self.assertEqual({d["id"] for d in duplicates} &
                         set(result["works"]),{d["id"] for d in duplicates})
        self.assertTrue(all(item["work_id"]==work_id
                            for work_id,item in result["works"].items()))

    def test_poster_schema_refuses_mismatched_work_id(self):
        from scripts.publish_catalog_v2 import REGISTRY
        works=json.loads(REGISTRY.read_text(encoding="utf-8"))["works"]
        with TemporaryDirectory() as temp:
            output=Path(temp)/"posters.json"
            content={"schema_version":2,"works":{
                w["id"]:{"work_id":w["id"],"kind":"original_editorial_cover",
                         "alt":w["title"]} for w in works.values()}}
            output.write_text(json.dumps(content),encoding="utf-8")
            with patch.object(posters,"OUTPUT",output):
                posters.check()
                key=next(iter(content["works"]))
                content["works"][key]["work_id"]="oa-w-999999"
                output.write_text(json.dumps(content),encoding="utf-8")
                with self.assertRaises(ValueError):
                    posters.check()

    def test_new_historical_images_have_exact_work_identity_and_composer(self):
        from scripts.publish_catalog_v2 import REGISTRY
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))["works"]
        archive=json.loads(posters.ARCHIVE.read_text(encoding="utf-8"))
        published=json.loads(posters.OUTPUT.read_text(encoding="utf-8"))["works"]
        cases={
            "oa-w-000039":("Tristan und Isolde","Richard Wagner"),
            "oa-w-000040":("La straniera","Vincenzo Bellini"),
            "oa-w-000042":("I due Foscari","Giuseppe Verdi"),
            "oa-w-000043":("Il ritorno di Ulisse in patria","Claudio Monteverdi"),
        }
        for wid,(title,composer) in cases.items():
            with self.subTest(title=title):
                work=next(w for w in registry.values() if w["id"]==wid)
                self.assertEqual((work["title"],work["composer"]),(title,composer))
                record=archive["works_by_id"][wid]
                self.assertEqual(record["work_id"],wid)
                self.assertEqual(record["composer"],composer)
                self.assertIn(work["slug"],archive["works"])
                poster=published[wid]
                self.assertEqual(poster["kind"],"archival_work_image")
                self.assertIn("commons.wikimedia.org/wiki/File:",poster["source_url"])
                self.assertIn("Special:Redirect/file/",poster["image_url"])
                self.assertEqual(poster["work_id"],wid)
        for wid in ("oa-w-000041","oa-w-000044"):
            # Modern works keep distinct, truthfully labelled original covers,
            # never the historical poster of another composition.
            self.assertEqual(published[wid]["kind"],"original_editorial_cover")

    def test_full_catalog_poster_coverage_and_stable_work_provenance(self):
        from scripts.publish_catalog_v2 import REGISTRY
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))["works"]
        works=list(registry.values())
        from scripts.publish_catalog_v2 import assemble
        from scripts.build_verified_catalog import MANIFEST
        registry_graph=assemble(json.loads(MANIFEST.read_text(encoding="utf-8")),
                                json.loads(REGISTRY.read_text(encoding="utf-8")))
        published=json.loads(posters.OUTPUT.read_text(encoding="utf-8"))["works"]
        self.assertEqual({w["id"] for w in works},set(published))
        editorial=[w for w in works if published[w["id"]]["kind"]=="original_editorial_cover"]
        # The three established illustrated works remain explicit. Future
        # first-party verified operas can temporarily use a truthful editorial
        # fallback if no reusable official poster is available. All other
        # unexplained fallbacks must still fail.
        established={"Death in Venice","Nixon in China","Jenůfa"}
        self.assertTrue(established.issubset({w["title"] for w in editorial}))
        for work in editorial:
            if work["title"] in established:continue
            # All new work IDs require independently verified authority,
            # but eligible works from other theatres may have Wikidata rather
            # than a TCBO URL. An artwork fallback is not a fake poster.
            import re
            official=work.get("authority_url","")
            first_party=(
                bool(re.fullmatch(
                    r"https://www\.tcbo\.it/evento/opera/[a-z0-9-]+-20\d{2}/",
                    official)) and
                any(stage["work_id"]==work["id"] and
                    stage["source_url"]==official
                    for stage in registry_graph["stagings"]))
            wikidata=bool(re.fullmatch(
                r"Q[1-9][0-9]*",work.get("wikidata_id","")))
            self.assertTrue(first_party or wikidata,work["title"])
        # Each newly catalogued opera must have an approved image plan, but
        # the number of *archival* works changes whenever new canonical IDs
        # are introduced. Never assert a fixed total from a different snapshot.
        counts={kind:sum(v["kind"]==kind for v in published.values())
                for kind in ("archival_work_image","official_production_image",
                             "original_editorial_cover")}
        # Official imagery is discovered continuously, and can replace an
        # archival fallback without changing the work inventory. Validate
        # the full partition, provenance and IDs, not a fixed number per kind.
        self.assertEqual(sum(counts.values()),len(works))
        self.assertEqual(counts["original_editorial_cover"],len(editorial))
        posters.check()
        for work in works:
            image=published[work["id"]]
            self.assertEqual(image["work_id"],work["id"])
            if image["kind"]=="archival_work_image":
                self.assertTrue(image["image_url"].startswith(
                    "https://commons.wikimedia.org/wiki/Special:Redirect/file/"))
                self.assertTrue(image["source_url"].startswith(
                    "https://commons.wikimedia.org/wiki/File:"))
                self.assertTrue(image["alt"])
                self.assertTrue(image["credit"])
                self.assertTrue(image["license"])
        self.assertNotEqual(published["oa-w-000007"]["image_url"],
                            published["oa-w-000024"]["image_url"])

    def test_explicit_editorial_covers_are_local_and_titles_are_visible(self):
        from scripts.deploy_atlas import FILES, SOURCE
        posted=json.loads(posters.OUTPUT.read_text(encoding="utf-8"))["works"]
        for work_id,filename,title in [
            ("oa-w-000020","cover-jenufa.svg","JENŮFA"),
            ("oa-w-000034","cover-nixon-in-china.svg","NIXON")
        ]:
            item=posted[work_id]
            self.assertEqual(item["kind"],"original_editorial_cover")
            self.assertEqual(item["cover_file"],filename)
            self.assertIn(filename,FILES)
            content=(SOURCE/filename).read_text(encoding="utf-8")
            self.assertIn(title,content)
            self.assertIn("COPERTINA EDITORIALE ORIGINALE",content)
        ballo=posted["oa-w-000012"]
        self.assertIn("Vocal_score_frontispiece",ballo["image_url"])
        self.assertNotIn("Yerevan",ballo["image_url"])

    def test_frontend_loads_posters_without_redeploying_on_each_new_work(self):
        root=Path(__file__).resolve().parents[1]
        image_js=(root/"site/image-client.js").read_text(encoding="utf-8")
        self.assertIn("public/catalog/work-posters.json",image_js)
        self.assertIn("chosen.kind===\"official_production_image\"",image_js)
        self.assertIn("posters[event?.work_id]",image_js)
        for name in ("app.js","detail.js","directory.js"):
            text=(root/"site"/name).read_text(encoding="utf-8")
            self.assertIn("await window.OperaAtlasImages?.load?.()",text)

if __name__=="__main__":
    unittest.main()
