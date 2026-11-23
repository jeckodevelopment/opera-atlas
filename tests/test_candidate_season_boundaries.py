"""Regression guards for source-specific candidate promotion boundaries."""
import json
import unittest
from scripts.auto_catalogue import split_verified_season, verified_venue, ROOT


class CandidateSeasonBoundaries(unittest.TestCase):
    def test_cosenza_official_season_splits_only_exact_verified_three_works(self):
        rows=[]
        for title,composer,count in (
            ("Il barbiere di Siviglia","Gioachino Rossini",2),
            ("La mère coupable","Darius Milhaud",1),
            ("Le nozze di Figaro","Wolfgang Amadeus Mozart",2),
        ):
            for day in range(1,count+1):
                rows.append({"event_title":title,"composer":composer,
                             "venue":"Teatro Alfonso Rendano",
                             "date":f"2026-12-{day:02d}",
                             "starts_at":f"2026-12-{day:02d}T20:30:00+01:00"})
        record={"candidate_id":"test","source_key":"cosenza-inprimafila-rolling-opera",
                "source_url":"https://www.inprimafila.net/index.php/eventi/stagione-lirica-2026-cosenza",
                "status":"needs_editorial_review","content_sha256":"f"*64,
                "event_facts":rows}
        split=split_verified_season(record)
        self.assertEqual(len(split),3)
        self.assertEqual(sorted(len(x["event_facts"]) for x in split),[1,2,2])
        self.assertTrue(all(x["source_url"]==record["source_url"] and
                            x["content_sha256"]==record["content_sha256"]
                            for x in split))
        # A partial or anomalous season must never be silently promoted.
        self.assertEqual(split_verified_season({**record,"event_facts":rows[:-1]}),
                         [{**record,"event_facts":rows[:-1]}])
        self.assertEqual(split_verified_season({**record,"event_facts":rows+[{
            **rows[0],"event_title":"Unexpected concert"}]}),
                         [{**record,"event_facts":rows+[{
            **rows[0],"event_title":"Unexpected concert"}]}])

    def test_mantova_short_name_reuses_exact_canonical_venue(self):
        registry=json.loads((ROOT/"data/identity-registry.json").read_text())
        rows=[{"event_title":"Tosca","composer":"Giacomo Puccini",
               "venue":"Teatro Sociale","date":"2027-01-08",
               "starts_at":"2027-01-08T20:30:00+01:00"}]
        resolved=verified_venue("mantova-sociale-rolling-opera",rows,registry)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved[0],"Mantova")
        self.assertEqual(resolved[1],"Teatro Sociale")
        # The venue may still be directory-only; if present in the registry,
        # it must be the existing official identity rather than a duplicate.
        matching=[v for v in registry["venues"].values()
                  if v["city"]=="Mantova" and v["name"]=="Teatro Sociale di Mantova"]
        self.assertEqual(resolved[2],matching[0] if matching else None)
        self.assertIsNone(verified_venue("mantova-sociale-rolling-opera",
            [{**rows[0],"venue":"Unknown Concert Hall"}],registry))


if __name__=="__main__":
    unittest.main()
