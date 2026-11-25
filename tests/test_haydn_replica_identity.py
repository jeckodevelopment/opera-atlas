"""The official Haydn replica group is a production, not two stagings."""
import copy
import json
import unittest
from datetime import date
from pathlib import Path

from opera_atlas.haydn_rolling_opera import replica_group_url
from scripts.haydn_replica_identity import (
    CANONICAL_ID,CANONICAL_KEY,RETIRED_ID,RETIRED_KEY,TICKETS,CLOCKS,
    TITLE,COMPOSER,REPLICA_GROUP,consolidate,same_replica_group,
)
from scripts.auto_catalogue import promote
from scripts.reconcile_published_candidates import verified_haydn_replica_urls
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY,assemble


class HaydnReplicaIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts=json.loads(MANIFEST.read_text())
        cls.registry=json.loads(REGISTRY.read_text())
        cls.evidence=json.loads(Path("data/candidate-detail-evidence.json").read_text())
        cls.candidates=json.loads(Path("data/season-index-candidates.json").read_text())

    def test_published_tito_is_one_staging_with_two_original_ticket_ids(self):
        stage=next(p for p in self.facts["productions"] if p["key"]==CANONICAL_KEY)
        self.assertEqual(stage["dates"],[[d,CLOCKS[d]] for d in sorted(CLOCKS)])
        self.assertEqual(stage["ticket_source_urls"],TICKETS)
        self.assertFalse(any(p["key"]==RETIRED_KEY for p in self.facts["productions"]))
        self.assertEqual(self.registry["retired_stagings"][RETIRED_ID]["canonical_id"],CANONICAL_ID)
        public=assemble(self.facts,self.registry)
        recite=[r for r in public["performances"] if r["staging_id"]==CANONICAL_ID]
        self.assertEqual({r["id"] for r in recite},{"oa-r-000962","oa-r-000963"})
        self.assertEqual({r["local_date"]:r["sources"][0] for r in recite},TICKETS)
        self.assertEqual(consolidate(self.facts,self.registry),(self.facts,self.registry,0))
        self.assertEqual(verified_haydn_replica_urls(self.facts,self.evidence),set(TICKETS.values()))

    def test_replay_cannot_recreate_second_production(self):
        evidence={"evidence":[e for e in self.evidence["evidence"] if e.get("source_url") in TICKETS.values()]}
        candidates={"candidates":[{**c,"status":"needs_review"} for c in self.candidates["candidates"]
                                 if c.get("official_url") in TICKETS.values()]}
        facts,ids,_,report=promote(self.facts,self.registry,evidence,candidates,
                                  list(TICKETS.values()),today=date(2026,11,25))
        self.assertEqual(report["new_stagings"],0,report)
        self.assertEqual(report["new_recite"],0,report)
        self.assertEqual(facts,self.facts)
        self.assertEqual(ids,self.registry)

    def test_replica_link_must_be_first_party_and_unambiguous(self):
        html='<a href="/eventi/area/opera?repliche=la-clemenza-di-tito">Repliche</a>'
        url=TICKETS["2026-11-27"]
        self.assertEqual(replica_group_url(html,url=url),REPLICA_GROUP)
        self.assertIsNone(replica_group_url(html.replace("/eventi/","https://example.com/eventi/"),url=url))
        self.assertIsNone(replica_group_url(html+'<a href="/eventi/area/opera?repliche=other">Repliche</a>',url=url))

    def test_group_requires_two_observations_and_matching_showtime(self):
        p=next(p for p in self.facts["productions"] if p["key"]==CANONICAL_KEY)
        records=[]
        for day,url in TICKETS.items():
            records.append({"source_key":"haydn-rolling-opera","status":"needs_editorial_review",
                "source_url":url,"content_sha256":"a"*64,"replica_group_url":REPLICA_GROUP,
                "event_facts":[{"event_title":TITLE,"composer":COMPOSER,"venue":"Teatro Sociale",
                "date":day,"starts_at":day+"T"+CLOCKS[day]+":00+01:00"}]})
        first,other=records
        self.assertTrue(same_replica_group(first,other,p,{"2026-11-27":"20:00"}))
        wrong=copy.deepcopy(other)
        wrong["event_facts"][0]["starts_at"]="2026-11-29T17:00:00+01:00"
        self.assertFalse(same_replica_group(first,wrong,p,{"2026-11-27":"20:00"}))
        self.assertFalse(same_replica_group(first,{**other,"replica_group_url":REPLICA_GROUP+"-other"},p,{"2026-11-27":"20:00"}))
        self.assertFalse(same_replica_group(first,other,p,{"2027-11-27":"20:00"}))


if __name__=="__main__":
    unittest.main()
