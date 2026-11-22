"""The Goldoni Dido event heading has a conflicting date/time."""
import copy
import json
import unittest

from opera_atlas.livorno_future_parser import parse_detail
from scripts.build_verified_catalog import MANIFEST,official_local_time
from scripts.reconcile_published_candidates import verified_livorno_dido_programme_urls

URL="https://www.goldoniteatro.it/spettacoli/dido-ed-enea-2/"
CID="oa-index-5957ac7d6a8b0d34cb4b"
ROWS=(("2026-11-06","20:00"),("2026-11-08","16:00"))

def official_page():
    return ("""<main><div>Teatro Goldoni - 08 Novembre 2026
    Orario/i: 20 Lirica</div><h1>DIDO AND AENEAS</h1>
    <p>Venerdì 6 novembre, ore 20</p><p>Domenica 8 novembre, ore 16</p>
    <h2>DIDO AND AENEAS</h2>
    <p>Opera in tre atti, libretto di Nahum Tate</p>
    <p>Musica di Henry Purcell</p>
    <p>Prima esecuzione mondiale</p><h2>Mediagallery</h2></main>""")

class LivornoDidoProgrammeTests(unittest.TestCase):
    def test_description_overrides_inaccurate_cms_header_only_at_exact_url(self):
        title,composer,venue,recite=parse_detail(official_page(),url=URL)
        self.assertEqual((title,composer,venue),
                         ("Dido and Æneas","Henry Purcell","Teatro Goldoni"))
        self.assertEqual(recite,list(ROWS))
        with self.assertRaises(ValueError):
            parse_detail(official_page().replace(
                "Domenica 8 novembre, ore 16","Domenica 8 novembre, ore 20"),url=URL)

    def test_one_canonical_goldoni_staging_resolves_secondary_ticket(self):
        manifest=json.loads(MANIFEST.read_text())
        record={"candidate_id":CID,"source_key":"goldoni-livorno-rolling-lirica",
                "source_url":URL,"status":"needs_editorial_review",
                "content_sha256":"a"*64,"event_facts":[
                    {"event_title":"Dido and Æneas","composer":"Henry Purcell",
                     "venue":"Teatro Goldoni","date":day,
                     "starts_at":official_local_time(day,hour)}
                    for day,hour in ROWS]}
        self.assertEqual(verified_livorno_dido_programme_urls(
            manifest,{"evidence":[record]}),{URL})
        invalid=copy.deepcopy(record)
        invalid["event_facts"][1]["starts_at"]=official_local_time("2026-11-08","20:00")
        self.assertEqual(verified_livorno_dido_programme_urls(
            manifest,{"evidence":[invalid]}),set())

if __name__=="__main__":
    unittest.main()
