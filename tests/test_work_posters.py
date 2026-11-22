"""A newly published opera must have a safe cover source and resilient fallback."""
import json
import shutil
import subprocess
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts import publish_work_posters as posters
from opera_atlas.controlled_fetch import FetchResult

class PosterPublicationTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"),"Node.js not available")
    def test_frontend_displays_verified_coproduction_poster(self):
        script=Path(__file__).with_name("bona_sforza_poster_smoke.cjs")
        result=subprocess.run(["node",str(script)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+"\\n"+result.stderr)


    @staticmethod
    def seed_official_evidence(path, *, checks=None):
        # Unit fixtures still start from independently verified, canonical
        # official images. An empty seed is now explicitly invalid.
        stable=json.loads(posters.EVIDENCE.read_text(encoding="utf-8"))
        data={"schema_version":2,"posters":stable["posters"],
              "checks":checks or {}}
        path.write_text(json.dumps(data),encoding="utf-8")

    def test_three_completed_operas_have_exact_archival_material(self):
        matches=posters.load_archival_art({
            "esule-di-roma","i-capuleti-e-i-montecchi","falstaff"})
        self.assertEqual(set(matches),{
            "esule-di-roma","i-capuleti-e-i-montecchi","falstaff"})
        expected={"esule-di-roma":"Donizetti",
                  "i-capuleti-e-i-montecchi":"Bellini",
                  "falstaff":"Verdi"}
        for slug,composer in expected.items():
            with self.subTest(work=slug):
                self.assertEqual(matches[slug]["kind"],"archival_work_image")
                self.assertIn("commons.wikimedia.org",matches[slug]["image_url"])
                self.assertIn(composer,matches[slug]["credit"])
                self.assertIn("Public domain",matches[slug]["license"])
                self.assertNotIn("allestimento in calendario",matches[slug]["credit"])

    def test_exact_first_party_event_alt_approves_opaque_image_filename_only_on_detail(self):
        base="https://www.fondazionepergolesispontini.com/eventi/lesecuzione-sotto-lo-sguardo-di-tosca-2/"
        image="https://www.fondazionepergolesispontini.com/wp-content/uploads/2026/11/asset-37923.jpg"
        html=('''<meta property="og:image" content="'''+image+'''">
                 <meta property="og:image:alt"
                 content="L'esecuzione di Salvatore Passantino, grafica dello spettacolo">''')
        self.assertIsNone(posters.extract_official_poster(html,base,"L'esecuzione"))
        result=posters.extract_official_poster(
            html,base,"L'esecuzione",verified_event_page=True)
        self.assertIsNotNone(result)
        self.assertEqual(result["image_url"],image)
        self.assertEqual(result["kind"],"official_production_image")
        for wrong in ("Nabucco","Don Pasquale","Tosca"):
            with self.subTest(title=wrong):
                self.assertIsNone(posters.extract_official_poster(
                    html,base,wrong,verified_event_page=True))
        bad=html.replace("L'esecuzione di Salvatore Passantino",
                         "Logo della Stagione 2026")
        self.assertIsNone(posters.extract_official_poster(
            bad,base,"L'esecuzione",verified_event_page=True))
        self.assertIsNone(posters.extract_official_poster(
            html.replace(image,"https://untrusted.example/opera.jpg"),
            base,"L'esecuzione",verified_event_page=True))

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
            self.seed_official_evidence(stored)
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
                                 "archival_work_image")
                self.assertEqual(result["works"]["oa-w-000031"]["kind"],
                                 "archival_work_image")
                self.assertEqual(len(calls),0)  # stable archival art needs no theatre fetch
                self.assertTrue(published.exists())
                evidence=json.loads(stored.read_text())
                self.assertNotIn("oa-w-000033",evidence["posters"])  # historical wins without new official evidence
                posters.publish(network_enabled=True,fetcher=mock,
                                today=date(2026,11,21),max_pages=2)
                self.assertEqual(len(calls),0) # archived art is permanently preferred

    def test_anna_bolena_and_leoncavallo_receive_distinct_archival_images(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            self.seed_official_evidence(root/"empty-evidence.json")
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
        self.assertEqual(puccini["kind"],"archival_work_image")

    def test_archival_art_skips_old_poster_retry_even_if_policy_changes(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            source_url="https://www.teatroallascala.org/it/stagione/2026-2027/opera/anna-bolena.html"
            self.seed_official_evidence(root/"evidence.json",
                checks={source_url:{"retry_after":"2026-11-27"}})
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
                self.assertEqual(calls,[])
                saved=json.loads((root/"evidence.json").read_text())
                self.assertEqual(saved["checks"][source_url]["retry_after"],"2026-11-27")
                posters.publish(network_enabled=True,fetcher=fetch,today=date(2026,11,21),max_pages=1)
                self.assertEqual(len(calls),0)

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
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        works=list(registry["works"].values())+list(registry.get("reserved_works",{}).values())
        duplicates=[w for w in works if w["slug"]=="la-boheme"]
        self.assertEqual(len(duplicates),2)
        self.assertNotEqual(duplicates[0]["id"],duplicates[1]["id"])
        # Real feed must contain a distinct entry for *every* canonical work
        # and must not silently merge the two La bohème composers.
        with TemporaryDirectory() as temp:
            root=Path(temp)
            self.seed_official_evidence(root/"empty-evidence.json")
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
            content=json.loads(posters.OUTPUT.read_text(encoding="utf-8"))
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
            self.assertEqual(published[wid]["kind"],"official_production_image")
            self.assertTrue(published[wid]["source_url"].startswith("https://www.tcbo.it/evento/opera/"))

    def test_historical_image_outweighs_saved_official_image(self):
        # The Scala evidence stays available as a fallback, but the
        # permanent poster of Puccini's Bohème must win the public mapping.
        with TemporaryDirectory() as temp:
            root=Path(temp)
            self.seed_official_evidence(root/"evidence.json")
            with patch.object(posters,"EVIDENCE",root/"evidence.json"),\
                 patch.object(posters,"OUTPUT",root/"posters.json"),\
                 patch.object(posters,"HEALTH",root/"health.json"),\
                 patch.object(posters,"connect"),patch.object(posters,"migrate"),\
                 patch.object(posters,"canonical_sources",return_value=[]):
                result=posters.publish(network_enabled=False,max_pages=0)
        for wid in ("oa-w-000001","oa-w-000002","oa-w-000006",
                    "oa-w-000010","oa-w-000011","oa-w-000023",
                    "oa-w-000024","oa-w-000025","oa-w-000038"):
            with self.subTest(wid=wid):
                self.assertEqual(result["works"][wid]["kind"],"archival_work_image")
                self.assertIn("commons.wikimedia.org",result["works"][wid]["source_url"])
        for wid in ("oa-w-000041","oa-w-000044"):
            self.assertEqual(result["works"][wid]["kind"],"official_production_image")
        self.assertNotEqual(result["works"]["oa-w-000007"]["image_url"],
                            result["works"]["oa-w-000024"]["image_url"])

    def test_each_reserved_program_work_has_its_own_archival_cover(self):
        archive=json.loads(posters.ARCHIVE.read_text(encoding="utf-8"))["works_by_id"]
        published=json.loads(posters.OUTPUT.read_text(encoding="utf-8"))["works"]
        expected={"oa-w-000090":"Don Pasquale in London.png",
                  "oa-w-000091":"Iltabarro-poster.jpg",
                  "oa-w-000092":"Disegno per copertina di libretto, disegno di Peter Hoffer per Suor Angelica (s.d.) - Archivio Storico Ricordi ICON012352.jpg",
                  "oa-w-000093":"Schicchi original cover.jpg"}
        for ident,filename in expected.items():
            with self.subTest(ident=ident):
                self.assertEqual(archive[ident]["file"],filename)
                item=published[ident]
                self.assertEqual(item["kind"],"archival_work_image")
                self.assertEqual(item["work_id"],ident)
                self.assertIn("commons.wikimedia.org",item["source_url"])
        self.assertEqual(len({published[i]["image_url"] for i in expected}),4)

    def test_full_catalog_poster_coverage_and_stable_work_provenance(self):
        from scripts.publish_catalog_v2 import REGISTRY
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        works=list(registry["works"].values())+list(registry.get("reserved_works",{}).values())
        from scripts.publish_catalog_v2 import assemble
        from scripts.build_verified_catalog import MANIFEST
        registry_graph=assemble(json.loads(MANIFEST.read_text(encoding="utf-8")),
                                json.loads(REGISTRY.read_text(encoding="utf-8")))
        published=json.loads(posters.OUTPUT.read_text(encoding="utf-8"))["works"]
        self.assertEqual({w["id"] for w in works},set(published))
        self.assertTrue(all(published[w["id"]]["kind"] in
                            ("archival_work_image","official_production_image","ticketing_event_artwork","official_coproduction_poster",
                             "official_original_work_artwork","official_civic_production_image")
                            for w in works))
        self.assertEqual(len(published),len(works))
        self.assertEqual(sum(v["kind"]=="original_editorial_cover"
                             for v in published.values()),0)
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

    def test_historical_posters_replace_old_generated_covers(self):
        published=json.loads(posters.OUTPUT.read_text(encoding="utf-8"))["works"]
        for wid in ("oa-w-000013","oa-w-000020","oa-w-000034"):
            self.assertEqual(published[wid]["kind"],"archival_work_image")
            self.assertTrue(published[wid]["source_url"].startswith(
                "https://commons.wikimedia.org/wiki/File:"))
        self.assertIn("Vocal_score_frontispiece",published["oa-w-000012"]["image_url"])

    def test_publisher_fails_closed_without_authenticated_work_image(self):
        from scripts.publish_catalog_v2 import REGISTRY
        with TemporaryDirectory() as temp:
            root=Path(temp)
            work={"id":"oa-w-999998","slug":"new-work","title":"New work",
                  "composer":"Unknown composer"}
            stub={"schema_version":1,"works":{"new work|unknown composer":work}}
            (root/"registry.json").write_text(json.dumps(stub))
            (root/"archive.json").write_text(json.dumps({
                "schema_version":1,"works":{},"works_by_id":{}}))
            (root/"evidence.json").write_text(json.dumps({
                "schema_version":2,"posters":{},"checks":{}}))
            with patch.object(posters,"REGISTRY",root/"registry.json"),\
                 patch.object(posters,"ARCHIVE",root/"archive.json"),\
                 patch.object(posters,"EVIDENCE",root/"evidence.json"),\
                 patch.object(posters,"OUTPUT",root/"out.json"),\
                 patch.object(posters,"HEALTH",root/"health.json"),\
                 patch.object(posters,"canonical_sources",return_value=[]),\
                 patch.object(posters,"connect"),patch.object(posters,"migrate"):
                with self.assertRaisesRegex(ValueError,"verified opera images missing"):
                    posters.publish(network_enabled=False,max_pages=0)
            self.assertFalse((root/"out.json").exists())

    def test_frontend_loads_posters_without_redeploying_on_each_new_work(self):
        root=Path(__file__).resolve().parents[1]
        image_js=(root/"site/image-client.js").read_text(encoding="utf-8")
        self.assertIn("public/catalog/work-posters.json",image_js)
        self.assertIn("chosen.kind===\"official_production_image\"",image_js)
        self.assertIn("posters[event?.work_id]",image_js)
        self.assertIn('kind:"unavailable"',image_js)
        self.assertNotIn('kind:"original_editorial_cover"',image_js)
        for name in ("app.js","detail.js","directory.js"):
            text=(root/"site"/name).read_text(encoding="utf-8")
            self.assertIn("await window.OperaAtlasImages?.load?.()",text)

if __name__=="__main__":
    unittest.main()
