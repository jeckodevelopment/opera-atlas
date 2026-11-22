"""Conservative catalog evidence: no false proof for shared pages or missing recite."""
import unittest
from scripts.candidate_publication_evidence import evidence


class PublicationEvidenceTests(unittest.TestCase):
    def test_exact_solo_link_and_ambiguous_shared_url(self):
        auto={"venues":[{"venue_id":"v1","sources":[{"source_key":"source1","configured":True}]}]}
        c={"schema_version":1,"candidates":[
            {"id":"a","source_key":"source1","status":"already_catalogued","official_url":"https://example.org/a"},
            {"id":"b","source_key":"source1","status":"already_catalogued","official_url":"https://example.org/shared"},
            {"id":"c","source_key":"source1","status":"already_catalogued","official_url":"https://example.org/no"},
            {"id":"d","source_key":"source1","status":"excluded_nonopera","official_url":"https://example.org/a"}
        ]}
        m={"schema_version":2,"files":{"stagings":{"sha256":"hash"}}}
        works={"works":[{"id":"w1"}]}
        stagings={"stagings":[
            {"id":"s1","source_url":"https://example.org/a","work_id":"w1","url":"/x/"},
            {"id":"s2","source_url":"https://example.org/shared","work_id":"w1"},
            {"id":"s3","source_url":"https://example.org/shared","work_id":"w1"}]}
        performances={"performances":[{"id":"r1","staging_id":"s1"}]}
        result=evidence(auto,c,m,works,stagings,performances,{"programs":[]})
        by_id={x["candidate_id"]:x for x in result["candidates"]}
        self.assertEqual(by_id["a"]["evidence_status"],"linked_solo_in_repository")
        self.assertEqual(by_id["a"]["catalog_evidence"][0]["performance_count"],1)
        self.assertEqual(by_id["b"]["evidence_status"],"ambiguous_source_url")
        self.assertEqual(by_id["c"]["evidence_status"],"no_direct_repository_link")
        self.assertEqual(by_id["d"]["evidence_status"],"not_applicable")
        self.assertEqual(by_id["a"]["venue_id"],"v1")

    def test_program_requires_known_components_and_performances(self):
        auto={"venues":[]}
        c={"schema_version":1,"candidates":[{"id":"p","source_key":"x","status":"already_catalogued","official_url":"https://example.org/p"}]}
        m={"schema_version":2,"files":{"stagings":{"sha256":"hash"}}}
        result=evidence(auto,c,m,{"works":[{"id":"w1"}]},{"stagings":[]},{"performances":[]},
                        {"programs":[{"id":"p1","source_url":"https://example.org/p",
                                      "components":[{"work_id":"w1"}],"performances":[{"id":"r"}]}]})
        self.assertEqual(result["candidates"][0]["evidence_status"],"linked_program_in_repository")
        self.assertIsNone(result["candidates"][0]["venue_id"])

if __name__=="__main__":
    unittest.main()
