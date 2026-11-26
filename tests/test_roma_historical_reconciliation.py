import hashlib
import unittest
from opera_atlas.roma_detail_parser import parse_roma_credited_detail, official_rome_other_season
from scripts.seed_roma_historical_candidates import seed,SOURCE

BASE="https://www.operaroma.it/spettacoli/"
def detail(title,composer,venue,calendar,season="2025/2026",credit="Musica di"):
    return (f"<p>Stagione {season}</p><h1>{title}</h1><p>{credit} {composer}</p>"
            f"<h3>Dove</h3><h3>{venue}</h3><h3>Le date</h3>"
            + "".join(f"<p>{d} ORE {t}</p>" for d,t in calendar)
            + "<h4>Anteprima giovani</h4><p>sabato 22 Nov ORE 16:00</p>")

class HistoricRomeTests(unittest.TestCase):
    def test_november_2025_and_october_2026(self):
        for slug,title,composer,day,expected in (
            ("lohengrin","Lohengrin","Richard Wagner","giovedì 27 Nov","2025-11-27"),
            ("falstaff","Falstaff","Giuseppe Verdi","domenica 11 Ott","2026-10-11")):
            url=BASE+slug+"/"
            html=detail(title,composer,"Teatro Costanzi",[(day,"17:00")])
            self.assertIsNone(official_rome_other_season(html,url=url))
            self.assertEqual(parse_roma_credited_detail(html,url=url)[-1],[(expected,"17:00")])
    def test_summer_aida_keeps_actual_venue(self):
        html=detail("Aida","Giuseppe Verdi","Circo Massimo",[("domenica 12 Lug","21:00")],credit="Musica")
        result=parse_roma_credited_detail(html,url=BASE+"aida-6/")
        self.assertEqual(result[2:],("Circo Massimo",[("2026-07-12","21:00")]))
    def test_unreviewed_old_season_and_wrong_weekday_rejected(self):
        html=detail("Lohengrin","Richard Wagner","Teatro Costanzi",[("lunedì 27 Nov","17:00")])
        with self.assertRaises(ValueError):parse_roma_credited_detail(html,url=BASE+"lohengrin/")
        with self.assertRaises(ValueError):parse_roma_credited_detail(html,url=BASE+"unreviewed/")
    def test_reopen_prior_exclusion_and_idempotency(self):
        url=BASE+"falstaff/"
        cid="oa-index-"+hashlib.sha256((SOURCE+"|"+url).encode()).hexdigest()[:20]
        candidates={"schema_version":1,"candidates":[{"id":cid,"source_key":SOURCE,
            "official_url":url,"status":"not_in_official_season","first_seen":"old","last_seen":"old"}]}
        evidence={"schema_version":1,"evidence":[{"candidate_id":cid,"source_key":SOURCE,
            "source_url":url,"official_season":"2025/2026","status":"out_of_monitored_season"}]}
        a,b=seed(candidates,evidence,set(),timestamp="now")
        row=next(x for x in a["candidates"] if x["id"]==cid)
        self.assertEqual(row["status"],"needs_review")
        self.assertEqual(row["first_seen"],"old")
        self.assertEqual(b["evidence"],[])
        self.assertEqual(seed(a,b,set(),timestamp="later"),(a,b))
