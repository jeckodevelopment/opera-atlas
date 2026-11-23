"""A brand-new verified physical theatre cannot block catalog publication."""
import copy
import unittest
from scripts.venue_editorial_review_queue import build


class VenueEditorialQueueTests(unittest.TestCase):
    def setUp(self):
        self.registry={"venues":{"Pesaro|Auditorium Nuovo":{
            "id":"oa-v-009999","city":"Pesaro","name":"Auditorium Nuovo",
            "city_slug":"pesaro","slug":"auditorium-nuovo","region":"Marche"}}}
        self.facts={"productions":[{
            "municipality":"Pesaro","venue":"Auditorium Nuovo",
            "source_url":"https://example.org/official-opera",
            "dates":[["2027-08-11","20:00"]]}]}
        self.profiles={"venues":{}}

    def test_new_verified_venue_enqueues_without_fake_editorial(self):
        prior=copy.deepcopy(self.registry)
        result=build(self.registry,self.facts,self.profiles)
        self.assertEqual(result["count"],1)
        row=result["venues"][0]
        self.assertEqual(row["venue_id"],"oa-v-009999")
        self.assertEqual(row["source_urls"],["https://example.org/official-opera"])
        self.assertEqual(row["status"],"editorial_review_pending")
        self.assertNotIn("address",row)
        self.assertNotIn("history",row)
        self.assertNotIn("photo_file",row)
        self.assertEqual(self.registry,prior)

    def test_verified_profile_closes_queue(self):
        self.profiles["venues"]["Pesaro|Auditorium Nuovo"]={
            "address":"Some address","history":"Verified research"}
        self.assertEqual(build(self.registry,self.facts,self.profiles)["count"],0)

    def test_official_long_name_profile_resolves_legacy_source_alias(self):
        self.registry["venues"]={"Savona|Teatro Chiabrera":{
            "id":"oa-v-000053","city":"Savona","name":"Teatro Gabriello Chiabrera",
            "city_slug":"savona","slug":"teatro-chiabrera","region":"Liguria"}}
        self.facts["productions"][0].update({
            "municipality":"Savona","venue":"Teatro Chiabrera"})
        self.profiles["venues"]["Savona|Teatro Gabriello Chiabrera"]={
            "address":"Piazza Armando Diaz 2","history":"Official profile"}
        self.assertEqual(build(self.registry,self.facts,self.profiles)["count"],0)

    def test_unverified_venue_and_conflicting_identity_fail_closed(self):
        self.facts["productions"][0]["dates"]=[]
        with self.assertRaisesRegex(ValueError,"without verified staging"):
            build(self.registry,self.facts,self.profiles)
        self.facts["productions"][0]["dates"]=[["2027-08-11","20:00"]]
        self.registry["venues"]["Pesaro|Auditorium Nuovo"]["name"]="Another venue"
        with self.assertRaisesRegex(ValueError,"inconsistent canonical venue"):
            build(self.registry,self.facts,self.profiles)


if __name__=="__main__":
    unittest.main()
