"""Artwork specifically approved for the 2027 Nicola Sani premiere."""
import unittest
import shutil
import subprocess
import json
from pathlib import Path

from opera_atlas.verified_ticketing_art import (
    verified_ticketing_image,is_verified_ticketing_poster)
from scripts.auto_catalogue import verified_candidate_image

SOURCE="https://www.operaroma.it/spettacoli/code-unknown/"
IMG="https://www.ticketone.it/obj/media/IT-eventim/teaser/evo/artwork/2027/code-unknow-biglietti.jpg"

class TicketingArtworkTests(unittest.TestCase):
    def test_code_unknown_ticketone_image_bound_to_exact_work(self):
        proof=verified_ticketing_image(
            source_url=SOURCE,title="Code: Unknown",composer="Nicola Sani")
        self.assertIsNotNone(proof)
        self.assertEqual(proof["image_url"],IMG)
        self.assertEqual(proof["kind"],"ticketing_event_artwork")
        self.assertIn("/artist/",proof["ticketing_page_url"])
        self.assertTrue(is_verified_ticketing_poster(
            proof,title="Code: Unknown",composer="Nicola Sani"))
        self.assertEqual(verified_candidate_image(
            {},title="Code: Unknown",composer="Nicola Sani",url=SOURCE),proof)
    @unittest.skipUnless(shutil.which("node"),"Node.js unavailable")
    def test_frontend_renders_only_canonical_ticketing_image(self):
        root=Path(__file__).resolve().parents[1]
        js=json.dumps(str(root/"site/image-client.js"))
        code=r"""
const fs=require("node:fs"),vm=require("node:vm");
const ctx={window:{},document:{querySelector:()=>null},console,URL};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(PATH,"utf8"),ctx);
const img=ctx.window.OperaAtlasImages;
const art="https://www.ticketone.it/obj/media/IT-eventim/teaser/evo/artwork/2027/code-unknow-biglietti.jpg";
const origFetch=ctx.fetch;
"""
        # Static inspect anchors the rendering allowlist; behavioral tests exercise
        # the client with a controlled V2 feed and reject wrong identities.
        code = '''
const fs=require("node:fs"),vm=require("node:vm"),assert=require("node:assert/strict");
const source=fs.readFileSync(%s,"utf8");
const record={kind:"ticketing_event_artwork",image_url:%s,source_url:%s,credit:"TicketOne"};
const ctx={window:{},document:{querySelector:()=>null},console,
 fetch:async()=>({ok:true,json:async()=>({schema_version:2,works:{"oa-w-000074":record,"oa-w-fake":record}})})};
vm.createContext(ctx);vm.runInContext(source,ctx);
(async()=>{
 const images=ctx.window.OperaAtlasImages;await images.load();
 const good=images.work({title:"Code: Unknown",work_id:"oa-w-000074",composer:"Nicola Sani"});
 assert.equal(good.src,record.image_url);
 assert.equal(good.kind,"ticketing_event_artwork");
 for(const wrong of [
  {title:"Code: Unknown",work_id:"oa-w-fake",composer:"Nicola Sani"},
  {title:"Code: Unknown",work_id:"oa-w-000074",composer:"Other composer"},
  {title:"Unrelated",work_id:"oa-w-000074",composer:"Nicola Sani"}]){
  assert.equal(images.work(wrong).kind,"unavailable");
 }
})().catch(e=>{console.error(e);process.exit(1)});
''' % (js,json.dumps(IMG),json.dumps(SOURCE))
        result=subprocess.run(["node","-e",code],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_never_confuse_homonyms_other_composers_or_sources(self):
        self.assertIsNone(verified_ticketing_image(
            source_url=SOURCE,title="Code: Unknown",composer="Giacomo Puccini"))
        self.assertIsNone(verified_ticketing_image(
            source_url=SOURCE,title="Code Unknown Film",composer="Nicola Sani"))
        self.assertIsNone(verified_ticketing_image(
            source_url="https://www.operaroma.it/spettacoli/falstaff/",
            title="Code: Unknown",composer="Nicola Sani"))
        correct=verified_ticketing_image(
            source_url=SOURCE,title="Code: Unknown",composer="Nicola Sani")
        self.assertFalse(is_verified_ticketing_poster(
            {**correct,"image_url":"https://www.ticketone.it/img/other.jpg"},
            title="Code: Unknown",composer="Nicola Sani"))
        self.assertFalse(is_verified_ticketing_poster(
            {**correct,"ticketing_page_url":"https://example.com"},
            title="Code: Unknown",composer="Nicola Sani"))

if __name__=="__main__":
    unittest.main()
