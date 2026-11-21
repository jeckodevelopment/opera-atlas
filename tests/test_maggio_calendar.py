"""Official Florence monthly cards become canonical, timed opera recite."""
import copy
import json
import unittest
from datetime import date
from opera_atlas.controlled_fetch import FetchResult
from scripts.collect_maggio_calendar import (
    SOURCE,month_url,months_from,parse_month,combine
)
from scripts.auto_catalogue import promote, SOURCE_ALLOWLIST
from scripts.build_verified_catalog import MANIFEST
from scripts.publish_catalog_v2 import REGISTRY,assemble
from scripts.discover_season_indexes import eligible,validate_config,CONFIG

INDEX="https://www.maggiofiorentino.com/calendario/2027/01/opera"
DETAIL="https://www.maggiofiorentino.com/events/la-traviata-2027"
OTHER="https://www.maggiofiorentino.com/events/il-mondo-alla-roversa"

def page():
    lines=['<a href="/events/la-traviata-2027">Opera '+d+
           ' January '+weekday+' '+hour+' Teatro del Maggio - Sala Grande '
           'La traviata Giuseppe Verdi</a>'
           for d,weekday,hour in [
             ("15","Friday","20:00"),("17","Sunday","15:30"),
             ("20","Wednesday","20:00"),("22","Friday","20:00")]]
    lines+=['<a href="/events/il-mondo-alla-roversa">'
            'Opera 30 January Saturday 17:00 Teatro Goldoni '
            'Il mondo alla roversa o sia le donne che comandano '
            'Baldassarre Galuppi</a>',
            '<a href="https://example.org/events/la-traviata-2027">'
            'Opera 23 January Saturday 20:00 Teatro del Maggio - Sala Grande '
            'La traviata Giuseppe Verdi</a>',
            '<a href="/events/la-traviata-2027">'
            'Opera 25 January Monday 20:00 Teatro del Maggio - Sala Grande '
            'La traviata Direttore Esemplare</a>']
    return "<h1>Calendario</h1>"+''.join(lines)

class FlorenceCalendarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.facts=json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_bounded_months_and_exact_source_allowlist(self):
        self.assertEqual(months_from(date(2026,11,21),count=4),[
            month_url(2026,11),month_url(2026,12),
            month_url(2027,1),month_url(2027,2)])
        self.assertTrue(eligible(SOURCE,DETAIL))
        self.assertFalse(eligible(SOURCE,"https://www.maggiofiorentino.com/blog/not-opera"))
        config=json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(len(validate_config(config)),14)

    def test_traviata_four_recite_with_real_clock_composer_venue(self):
        rows=parse_month(page(),url=INDEX,registry=self.registry,today=date(2026,11,21))
        self.assertEqual(len(rows),4)
        self.assertEqual({x["official_url"] for x in rows},{DETAIL})
        self.assertEqual([x["date"] for x in rows],
                         ["2027-01-15","2027-01-17","2027-01-20","2027-01-22"])
        self.assertEqual([x["starts_at"][11:16] for x in rows],
                         ["20:00","15:30","20:00","20:00"])
        self.assertEqual({x["composer"] for x in rows},{"Giuseppe Verdi"})
        self.assertEqual({x["venue"] for x in rows},{"Teatro del Maggio Musicale Fiorentino"})
        self.assertTrue(all(x["starts_at"].endswith("+01:00") for x in rows))

    def test_goldoni_unseen_composition_is_credited_from_official_calendar(self):
        import hashlib
        official="https://www.maggiofiorentino.com/events/il-mondo-alla-roversa-o-sia-le-donne-che-comandano"
        title="Il mondo alla roversa o sia le donne che comandano"
        cid="oa-index-"+hashlib.sha256((SOURCE+"|"+official).encode()).hexdigest()[:20]
        detail={"schema_version":1,"evidence":[{"candidate_id":cid,
            "source_key":SOURCE,"source_url":official,
            "status":"needs_editorial_review","event_facts":[{
                "event_title":title,"venue":"Teatro Goldoni",
                "date":"2027-01-30","starts_at":"2027-01-30T17:00:00+01:00"}]}]}
        page=('<a href="/events/il-mondo-alla-roversa-o-sia-le-donne-che-comandano">'
              'Opera 30 January Saturday 17:00 Teatro Goldoni '
              'Il mondo alla roversa o sia le donne che comandano '
              'Baldassarre Galuppi</a>')
        found=parse_month(page,url=INDEX,registry=self.registry,
                          today=date(2026,11,21),evidence=detail)
        self.assertEqual(len(found),1)
        self.assertEqual(found[0]["composer"],"Baldassarre Galuppi")
        self.assertEqual(found[0]["venue"],"Teatro Goldoni")
        candidates,evidence=combine({"schema_version":1,"candidates":[]},detail,
                                    found,at="2026-11-21T18:00:00+00:00")
        self.assertEqual(len(evidence["evidence"]),1)
        self.assertEqual(evidence["evidence"][0]["event_facts"][0]["composer"],
                         "Baldassarre Galuppi")
        fake=page.replace("Baldassarre Galuppi","Direttore Esemplare")
        self.assertEqual(parse_month(fake,url=INDEX,registry=self.registry,
                          today=date(2026,11,21),evidence=detail),[])
        changed=copy.deepcopy(detail)
        changed["evidence"][0]["event_facts"][0]["starts_at"]="2027-01-30T20:00:00+01:00"
        with self.assertRaises(ValueError):
            combine({"schema_version":1,"candidates":[]},changed,
                    found,at="2026-11-21T18:00:00+00:00")

    def test_unknown_work_other_venue_and_invalid_month_are_not_facts(self):
        self.assertEqual(parse_month(page().replace("La traviata Giuseppe Verdi",
                         "La traviata Wolfgang Amadeus Mozart"),
                         url=INDEX,registry=self.registry,today=date(2026,11,21)),[])
        with self.assertRaises(ValueError):
            parse_month(page(),url="https://evil.invalid/calendario/2027/01/opera",
                        registry=self.registry,today=date(2026,11,21))
        with self.assertRaises(ValueError):
            parse_month(page(),url=INDEX+"?preview=1",
                        registry=self.registry,today=date(2026,11,21))

    def test_end_to_end_florence_promotes_new_theatre_and_four_verified_performances(self):
        rows=parse_month(page(),url=INDEX,registry=self.registry,today=date(2026,11,21))
        candidates,evidence=combine(
            {"schema_version":1,"candidates":[]},{"schema_version":1,"evidence":[]},
            rows,at="2026-11-21T13:00:00+00:00")
        self.assertEqual(len(candidates["candidates"]),1)
        self.assertEqual(len(evidence["evidence"]),1)
        approved_before=json.loads(SOURCE_ALLOWLIST.read_text(encoding="utf-8"))["urls"]
        existing=next((x for x in self.facts["productions"]
                       if x["municipality"]=="Firenze" and x["title"]=="La traviata"),None)
        facts,registry,urls,report=promote(
            self.facts,self.registry,evidence,candidates,approved_before,
            today=date(2026,11,21))
        self.assertEqual(report["new_stagings"],0 if existing else 1,report)
        self.assertEqual(report["new_recite"],0 if existing else 4,report)
        new=[p for p in facts["productions"] if p["municipality"]=="Firenze" and p["source_url"]==DETAIL]
        self.assertEqual(len(new),1)
        self.assertEqual(new[0]["title"],"La traviata")
        self.assertEqual(new[0]["region"],"Toscana")
        self.assertEqual(new[0]["source_url"],DETAIL)
        self.assertEqual(registry["venues"]["Firenze|Teatro del Maggio Musicale Fiorentino"]["city"],"Firenze")
        feed=assemble(facts,registry,approved_extra=set(urls))
        self.assertEqual(sum(x["staging_id"]==registry["stagings"][new[0]["key"]]["id"]
                             for x in feed["performances"]),4)
        again,ids,approved,second=promote(
            facts,registry,evidence,candidates,urls,today=date(2026,11,21))
        self.assertEqual(second["new_recite"],0,second)
        self.assertEqual(again,facts)
        self.assertEqual(ids,registry)
        self.assertEqual(approved,urls)
        repeated_c,repeated_e=combine(candidates,evidence,rows,
                                      at="2026-11-21T14:00:00+00:00")
        self.assertEqual(len(repeated_c["candidates"]),1)
        self.assertEqual(repeated_e["evidence"][0]["event_facts"],
                         evidence["evidence"][0]["event_facts"])

if __name__=="__main__":
    unittest.main()
