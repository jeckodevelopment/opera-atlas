"""Automation is based on real source checks, never venue directory labels."""
import unittest
from scripts.source_automation import build


class SourceAutomationTests(unittest.TestCase):
    def test_haydn_and_vicenza_secondary_venues(self):
        import json
        from scripts.source_automation import DIRECTORY, DAILY, INDEX
        from opera_atlas.haydn_rolling_opera import parse_detail
        html = """<h1>note to a friend</h1><p>David Lang</p><p>Opera</p>
        <p>Musica di David Lang Libretto di David Lang</p>
        <p>Mercoledì 11.03.2026 alle 20.00</p><p>Teatro SanbàPolis</p>
        <p>Via della Malpensada, 80-88 - Trento</p>"""
        self.assertEqual(parse_detail(html, url="https://www.haydn.it/eventi/note-to-a-friend-2"),
                         ("note to a friend", "David Lang", "Sanbàpolis", [("2026-03-11", "20:00")]))
        with self.assertRaises(ValueError):
            parse_detail(html.replace("80-88 - Trento", "80-88 - Bolzano"),
                         url="https://www.haydn.it/eventi/note-to-a-friend-2")
        report = build(json.loads(DIRECTORY.read_text()), json.loads(DAILY.read_text()),
                       {"sources":[]}, json.loads(INDEX.read_text()), {"sources":[
                           {"key":key,"status":"success","current_scan_verified":True}
                           for key in ("haydn-rolling-opera","vicenza-olimpico-rolling-opera")]})
        rows = {v["venue"]:v for v in report["venues"]}
        for venue in ("Sanbàpolis","Villa Pisani Bonetti"):
            self.assertEqual(rows[venue]["status"], "operational")

    def test_actual_success_and_missing_sources(self):
        # Mapping integrity requires the complete reference directory.
        from scripts.source_automation import DIRECTORY, DAILY, INDEX
        import json
        directory=json.loads(DIRECTORY.read_text())
        daily=json.loads(DAILY.read_text())
        index=json.loads(INDEX.read_text())
        dh={"sources":[{"key":"regio-traviata-2027","outcome":"success"}]}
        ih={"sources":[{"key":"opera-roma-season-2026-27",
                        "status":"success","current_scan_verified":True},
                       {"key":"petruzzelli-opera-2026",
                        "status":"unavailable_or_invalid","current_scan_verified":False}]}
        report=build(directory,daily,dh,index,ih)
        rows={(x["city"],x["venue"]):x for x in report["venues"]}
        self.assertEqual(rows["Torino","Teatro Regio di Torino"]["status"],"operational")
        self.assertEqual(rows["Roma","Teatro dell'Opera di Roma"]["status"],"operational")
        self.assertEqual(rows["Napoli","Teatro di San Carlo"]["status"],"configured_not_operational")
        self.assertEqual(rows["Napoli","Teatro di San Carlo"]["source_attention"],"not_checked")
        self.assertEqual(rows["Roma","Teatro dell\'Opera di Roma"]["source_attention"],"none")
        self.assertEqual(report["total_venues"],len(directory["venues"]))
        self.assertEqual(report["automation_remaining"],
                         report["not_automated"]+report["configured_not_operational"])

    def test_trapani_shared_festival_source_covers_both_verified_physical_venues(self):
        from scripts.source_automation import DIRECTORY, DAILY, INDEX, INDEX_VENUES, build
        import json
        key = "trapani-luglio-musicale-2026"
        mapped = set(INDEX_VENUES[key])
        self.assertEqual(mapped, {
            "Trapani|Teatro Giuseppe Di Stefano",
            "Trapani|Teatro M° Tonino Pardo",
        })
        directory = json.loads(DIRECTORY.read_text(encoding="utf-8"))
        daily = json.loads(DAILY.read_text(encoding="utf-8"))
        index = json.loads(INDEX.read_text(encoding="utf-8"))
        report = build(directory, daily, {"sources":[]}, index,
                       {"sources":[{"key":key, "status":"success",
                                    "current_scan_verified":True}]})
        venues = {(v["city"],v["venue"]):v for v in report["venues"]}
        for venue in ("Teatro Giuseppe Di Stefano", "Teatro M° Tonino Pardo"):
            entry = venues["Trapani",venue]
            self.assertEqual(entry["status"],"operational")
            self.assertTrue(any(s["source_key"] == key and s["recent_success"]
                                for s in entry["sources"]))
        self.assertNotEqual(venues["Trapani","Teatro Giuseppe Di Stefano"]["venue_id"],
                            venues["Trapani","Teatro M° Tonino Pardo"]["venue_id"])
        unverified = build(directory, daily, {"sources":[]}, index, {"sources":[]})
        missing = {(v["city"],v["venue"]):v for v in unverified["venues"]}
        for venue in ("Teatro Giuseppe Di Stefano", "Teatro M° Tonino Pardo"):
            self.assertEqual(missing["Trapani",venue]["status"],
                             "configured_not_operational")

    def test_secondary_festival_venues_are_explicitly_mapped(self):
        from scripts.source_automation import (
            DIRECTORY, DAILY, INDEX, INDEX_VENUES, build
        )
        import json
        targets = {
            "sassari-de-carolis-rolling-opera": "Alghero|Forte della Maddalena",
            "goldoni-livorno-rolling-lirica": "Livorno|Piazza Goldoni",
            "coccia-novara-rolling-opera": "Novara|Giardini di Palazzo Natta",
            "pesaro-rof-2026": "Pesaro|Auditorium Scavolini",
            "savona-giocosa-rolling-opera": "Savona|Teatro Gabriello Chiabrera",
        }
        directory = json.loads(DIRECTORY.read_text(encoding="utf-8"))
        configured = {x["key"] for x in json.loads(INDEX.read_text(encoding="utf-8"))["sources"]}
        by_name = {v["city"]+"|"+v["name"]:v for v in directory["venues"]}
        for key, venue in targets.items():
            self.assertIn(key, configured)
            self.assertIn(venue, INDEX_VENUES[key])
            self.assertIn(venue, by_name)
        checks = {"sources":[{"key":key,"status":"success",
                    "current_scan_verified":True} for key in targets]}
        report = build(directory,
                       json.loads(DAILY.read_text(encoding="utf-8")),
                       {"sources":[]},
                       json.loads(INDEX.read_text(encoding="utf-8")), checks)
        by_venue = {v["city"]+"|"+v["venue"]:v for v in report["venues"]}
        for source_key, venue in targets.items():
            row = by_venue[venue]
            self.assertEqual(row["status"], "operational", (source_key,venue))
            self.assertTrue(any(s["source_key"] == source_key
                                for s in row["sources"]))
        # Separate physical venues must not be merged by common organizer.
        self.assertNotEqual(by_venue["Livorno|Piazza Goldoni"]["venue_id"],
                            by_venue["Livorno|Teatro Goldoni"]["venue_id"])
        self.assertNotEqual(by_venue["Pesaro|Auditorium Scavolini"]["venue_id"],
                            by_venue["Pesaro|Teatro Gioachino Rossini"]["venue_id"])

    def test_ravenna_pisa_rolling_sources_have_real_venue_mapping(self):
        from scripts.source_automation import INDEX_VENUES, DIRECTORY, DAILY, INDEX, build
        import json
        expected = {
            "ravenna-cherubini-rolling-opera":"Ravenna|Teatro Dante Alighieri",
            "pisa-future-calendar":"Pisa|Teatro Verdi",
        }
        configured=json.loads(INDEX.read_text(encoding="utf-8"))
        directory=json.loads(DIRECTORY.read_text(encoding="utf-8"))
        daily=json.loads(DAILY.read_text(encoding="utf-8"))
        for source, venue in expected.items():
            self.assertIn(venue, INDEX_VENUES[source])
        scans={"sources":[{"key":key,"status":"success",
                            "current_scan_verified":True} for key in expected]}
        report=build(directory,daily,{"sources":[]},configured,scans)
        rows={x["city"]+"|"+x["venue"]:x for x in report["venues"]}
        for key,venue in expected.items():
            self.assertEqual(rows[venue]["status"],"operational")
            self.assertIn(key,[s["source_key"] for s in rows[venue]["sources"]])
        failed=build(directory,daily,{"sources":[]},configured,{"sources":[]})
        rows={x["city"]+"|"+x["venue"]:x for x in failed["venues"]}
        for venue in expected.values():
            self.assertNotEqual(rows[venue]["status"],"operational")

    def test_san_carlo_secondary_publication_counts_as_operational(self):
        from scripts.source_automation import (
            DIRECTORY, DAILY, INDEX, SAN_CARLO_SECONDARY,
            SAN_CARLO_CANONICAL, SAN_CARLO_CANDIDATES, SAN_CARLO_PUBLIC,
            san_carlo_verified_fallback
        )
        import json
        def read(path):
            return json.loads(path.read_text(encoding="utf-8"))
        secondary, canonical = read(SAN_CARLO_SECONDARY), read(SAN_CARLO_CANONICAL)
        candidates, public = read(SAN_CARLO_CANDIDATES), read(SAN_CARLO_PUBLIC)
        fallback = san_carlo_verified_fallback(secondary, canonical, candidates, public)
        self.assertIsNotNone(fallback)
        self.assertEqual(fallback["published_performances"], 58)
        report = build(read(DIRECTORY), read(DAILY), {"sources":[]},
                       read(INDEX), {"sources":[{"key":"napoli-san-carlo-rolling-opera",
                       "status":"unavailable_or_invalid",
                       "diagnostic":"official_anti_bot_challenge",
                       "current_scan_verified":False}]},
                       san_carlo_fallback=fallback)
        napoli = next(v for v in report["venues"]
                      if v["city"]=="Napoli" and v["venue"]=="Teatro di San Carlo")
        self.assertEqual(napoli["status"], "operational")
        self.assertEqual(napoli["recent_successful_connectors"], 1)
        self.assertEqual(napoli["configured_connectors"], 2)
        official = next(x for x in napoli["sources"]
                        if x["source_key"]=="napoli-san-carlo-rolling-opera")
        self.assertEqual(official["failure_reason"], "official_anti_bot_challenge")
        self.assertFalse(official["recent_success"])
        self.assertFalse(fallback["direct_official_scan_verified"])

    def test_san_carlo_secondary_requires_real_canonical_publication(self):
        from scripts.source_automation import (
            SAN_CARLO_SECONDARY, SAN_CARLO_CANONICAL,
            SAN_CARLO_CANDIDATES, SAN_CARLO_PUBLIC,
            san_carlo_verified_fallback
        )
        import json
        def read(path):
            return json.loads(path.read_text(encoding="utf-8"))
        secondary, canonical = read(SAN_CARLO_SECONDARY), read(SAN_CARLO_CANONICAL)
        candidates, public = read(SAN_CARLO_CANDIDATES), read(SAN_CARLO_PUBLIC)
        self.assertIsNotNone(san_carlo_verified_fallback(
            secondary,canonical,candidates,public))
        corrupted = {**public, "performances": [
            p for p in public["performances"]
            if not (p.get("venue")=="Teatro di San Carlo" and
                    p.get("title")=="Peter Grimes")]}
        self.assertIsNone(san_carlo_verified_fallback(
            secondary,canonical,candidates,corrupted))
        bad = {**secondary,"performance_count":57}
        self.assertIsNone(san_carlo_verified_fallback(
            bad,canonical,candidates,public))
        bad = {**canonical,"productions":[
            {**x, "status":"canonical_candidate_evidence_ready"}
            if x["title"]=="Luisa Miller" else x for x in canonical["productions"]]}
        self.assertIsNone(san_carlo_verified_fallback(
            secondary,bad,candidates,public))

    def test_secondary_venues_have_exact_first_party_published_productions(self):
        from scripts.source_automation import DIRECTORY, DAILY, INDEX, ROOT
        import json
        from urllib.parse import urlsplit
        directory=json.loads(DIRECTORY.read_text())
        daily=json.loads(DAILY.read_text())
        index=json.loads(INDEX.read_text())
        published=json.loads((ROOT/"data/verified-launch-catalog.json").read_text())
        expected={
            ("Reggio Emilia","Teatro Ariosto"):"www.iteatri.re.it",
            ("Roma","Teatro Nazionale"):"www.operaroma.it",
            ("Roma","Teatro Valle Franca Valeri"):"www.operaroma.it",
            ("Catania","Teatro Sangiorgi"):"www.teatromassimobellini.it",
        }
        for (city,venue),host in expected.items():
            matches=[x for x in published["productions"]
                     if x["municipality"]==city and x["venue"]==venue
                     and urlsplit(x["source_url"]).hostname==host and x["dates"]]
            self.assertTrue(matches,(city,venue))
        healthy={"sources":[
            {"key":"reggio-valli-opera-2026-27",
             "status":"success","current_scan_verified":True},
            {"key":"opera-roma-season-2026-27",
             "status":"success","current_scan_verified":True},
            {"key":"bellini-catania-opera-2026-27",
             "status":"success","current_scan_verified":True},
        ]}
        report=build(directory,daily,{"sources":[]},index,healthy)
        by_venue={(x["city"],x["venue"]):x for x in report["venues"]}
        for key in expected:
            self.assertEqual(by_venue[key]["status"],"operational")
        unhealthy=build(directory,daily,{"sources":[]},index,{"sources":[]})
        by_venue={(x["city"],x["venue"]):x for x in unhealthy["venues"]}
        for key in expected:
            self.assertNotEqual(by_venue[key]["status"],"operational")

    def test_scan_attention_separates_unverified_future_from_technical_failure(self):
        from scripts.source_automation import INDEX, scan_attention, classify_index_scan
        import json
        index=json.loads(INDEX.read_text())
        health={"sources":[
            {"key":"chieti-marrucino-season-2027",
             "status":"unavailable_or_invalid",
             "diagnostic":"future_official_programme_unverified"},
            {"key":"modena-opera-2026-27",
             "status":"unavailable_or_invalid",
             "diagnostic":"official_html_unavailable_or_invalid"},
            {"key":"modena-teatro-opera-2026-27",
             "status":"success","current_scan_verified":True},
            {"key":"napoli-san-carlo-rolling-opera",
             "status":"unavailable_or_invalid",
             "diagnostic":"official_anti_bot_challenge"},
            {"key":"salerno-verdi-rolling-opera",
             "status":"unavailable_or_invalid",
             "diagnostic":"invalid_index_or_source_config"}]}
        report=scan_attention(index,health)
        by_key={x["source_key"]:x for x in report["sources"]}
        self.assertEqual(by_key["chieti-marrucino-season-2027"]["scan_classification"],
                         "future_programme_not_verified")
        self.assertFalse(by_key["chieti-marrucino-season-2027"]["requires_technical_attention"])
        modena=by_key["modena-opera-2026-27"]
        self.assertEqual(modena["scan_classification"],"fetch_unavailable")
        self.assertFalse(modena["requires_technical_attention"])
        self.assertEqual(modena["failure_state"],"transient")
        self.assertIn("modena-teatro-opera-2026-27",modena["other_successful_official_sources"])
        self.assertEqual(by_key["napoli-san-carlo-rolling-opera"]["scan_classification"],
                         "access_blocked")
        self.assertEqual(by_key["salerno-verdi-rolling-opera"]["scan_classification"],
                         "parser_or_source_validation_failed")
        self.assertEqual(classify_index_scan({"status":"success",
                          "current_scan_verified":False}),
                         "parser_or_source_validation_failed")
        self.assertEqual(report["total"],len(index["sources"]))

    def test_unpublished_venue_alternative_is_not_catalogued(self):
        from scripts.source_automation import INDEX, CANDIDATE_REGISTRY, scan_attention
        import json
        index=json.loads(INDEX.read_text())
        candidates=json.loads(CANDIDATE_REGISTRY.read_text())
        checks={"sources":[
            {"key":key,"status":"success","current_scan_verified":True}
            for key in ("cosenza-inprimafila-rolling-opera",
                        "taormina-opera-festival-rolling",
                        "rovigo-regione-programma-2026-27",
                        "modena-teatro-opera-2026-27")]}
        report=scan_attention(index,checks,candidates=candidates)
        by_key={x["source_key"]:x for x in report["sources"]}
        # Cosenza's first-party Le nozze di Figaro has now entered the
        # canonical catalog. A healthy alternative there is also catalogued,
        # while Taormina/Rovigo still have no such evidence.
        cosenza=by_key["cosenza-rendano-rolling-opera"]
        self.assertTrue(cosenza["has_healthy_alternative"])
        self.assertTrue(cosenza["has_catalogued_alternative"])
        self.assertEqual(cosenza["other_successful_catalogued_sources"],
                         ["cosenza-inprimafila-rolling-opera"])
        for key in ("taormina-fondazione-rolling-opera",
                    "rovigo-sociale-opera-2026-27"):
            x=by_key[key]
            self.assertTrue(x["has_healthy_alternative"],key)
            self.assertFalse(x["has_catalogued_alternative"],key)
            self.assertEqual(x["other_successful_catalogued_sources"],[])
        modena=by_key["modena-opera-2026-27"]
        self.assertTrue(modena["has_catalogued_alternative"])
        self.assertEqual(modena["other_successful_catalogued_sources"],
                         ["modena-teatro-opera-2026-27"])
        # The live candidate queue may legitimately reach zero. Exercise
        # unresolved-status counting with a controlled candidate snapshot;
        # do not fail simply because automatic reconciliation succeeded.
        checked_source=index["sources"][0]["key"]
        original_count=by_key[checked_source]["candidate_yield"]["needs_review"]
        fixture=json.loads(json.dumps(candidates))
        fixture["candidates"].append({
            "source_key":checked_source,"status":"needs_review",
            "id":"fixture-awaiting-official-review"})
        with_pending=scan_attention(index,checks,candidates=fixture)
        fixture_source=next(row for row in with_pending["sources"]
                            if row["source_key"]==checked_source)
        self.assertEqual(fixture_source["candidate_yield"]["needs_review"],
                         original_count+1)
        self.assertGreater(with_pending["sources_with_unresolved_candidates"],0)

    def test_scan_yield_distinguishes_successful_crawl_from_publication(self):
        from scripts.source_automation import INDEX, scan_attention, CANDIDATE_REGISTRY
        import json
        index=json.loads(INDEX.read_text())
        candidates=json.loads(CANDIDATE_REGISTRY.read_text())
        report=scan_attention(index,{"sources":[
            {"key":"cosenza-inprimafila-rolling-opera",
             "status":"success","current_scan_verified":True},
            {"key":"taormina-opera-festival-rolling",
             "status":"success","current_scan_verified":True},
        ]},candidates=candidates)
        by_key={r["source_key"]:r for r in report["sources"]}
        for key in ("cosenza-inprimafila-rolling-opera",
                    "taormina-opera-festival-rolling"):
            row=by_key[key]
            self.assertEqual(row["scan_classification"],"verified_success")
            yield_=row["candidate_yield"]
            self.assertEqual(yield_["total"],sum(yield_[k] for k in (
                "already_catalogued","needs_review","excluded_nonopera",
                "not_in_official_season")))
            # A fully reconciled source may have no pending candidates.
            self.assertGreater(yield_["total"],0)
            self.assertGreaterEqual(yield_["needs_review"],0)
        san=by_key["napoli-san-carlo-rolling-opera"]["candidate_yield"]
        self.assertEqual(san["already_catalogued"],10)
        self.assertEqual(san["needs_review"],0)
        self.assertEqual(san["total"],10)

    def test_candidate_yield_rejects_unknown_and_duplicate_status(self):
        from scripts.source_automation import INDEX, scan_attention
        import json
        index=json.loads(INDEX.read_text())
        good={"schema_version":1,"candidates":[
            {"source_key":"modena-opera-2026-27","status":"needs_review"},
            {"source_key":"modena-opera-2026-27","status":"already_catalogued"},
        ]}
        row=next(x for x in scan_attention(index,{"sources":[]},
                        candidates=good)["sources"]
                 if x["source_key"]=="modena-opera-2026-27")
        self.assertEqual(row["candidate_yield"]["total"],2)
        for bad in (
            {"schema_version":1,"candidates":[{"source_key":"x","status":"published"}]},
            {"schema_version":2,"candidates":[]},
            {"schema_version":1,"candidates":[None]},
        ):
            with self.assertRaises(ValueError):
                scan_attention(index,{"sources":[]},candidates=bad)

    def test_scan_attention_does_not_mark_future_404_as_unpublished_season(self):
        from scripts.source_automation import INDEX, scan_attention
        import json
        index=json.loads(INDEX.read_text())
        health={"sources":[{"key":"modena-municipal-opera-2027-28",
                            "status":"unavailable_or_invalid",
                            "diagnostic":"official_html_unavailable_or_invalid"}]}
        result=scan_attention(index,health)
        future=next(x for x in result["sources"]
                    if x["source_key"]=="modena-municipal-opera-2027-28")
        self.assertEqual(future["scan_classification"],"fetch_unavailable")
        self.assertFalse(future["requires_technical_attention"])
        self.assertEqual(future["failure_state"],"transient")
        self.assertFalse(future["has_healthy_alternative"])
        self.assertNotIn("not_published",str(future))

    def test_24h_outage_alerts_preserve_raw_status_and_alternatives(self):
        from scripts.source_automation import DIRECTORY, DAILY, INDEX
        import json
        from opera_atlas.source_failure_history import with_history
        key="opera-roma-season-2026-27"
        failure={"key":key,"status":"unavailable_or_invalid",
                 "diagnostic":"official_html_unavailable_or_invalid"}
        first=with_history(failure,{},checked_at="2026-11-27T10:00:00+00:00")
        directory=json.loads(DIRECTORY.read_text())
        daily=json.loads(DAILY.read_text())
        index=json.loads(INDEX.read_text())
        for stamp,expected in (("2026-11-28T09:59:59+00:00",False),
                               ("2026-11-28T10:00:00+00:00",True)):
            row=with_history(failure,first,checked_at=stamp)
            report=build(directory,daily,{"sources":[]},index,{"sources":[row]})
            venue=next(x for x in report["venues"] if x["city"]=="Roma"
                       and x["venue"]=="Teatro dell'Opera di Roma")
            self.assertEqual(venue["status"],"configured_not_operational")
            self.assertEqual(venue["requires_technical_attention"],expected)
            self.assertEqual(venue["outage_state"],"persistent" if expected else "transient")
            source=next(x for x in report["index_scan_attention"]["sources"] if x["source_key"]==key)
            self.assertEqual(source["requires_technical_attention"],expected)
        # A successful alternative means the venue does not require escalation.
        key="modena-opera-2026-27"
        failed=dict(row,key=key)
        success={"key":"modena-teatro-opera-2026-27","status":"success",
                 "current_scan_verified":True}
        report=build(directory,daily,{"sources":[]},index,{"sources":[failed,success]})
        venue=next(x for x in report["venues"] if x["city"]=="Modena")
        self.assertEqual(venue["status"],"operational")
        self.assertFalse(venue["requires_technical_attention"])

    def test_index_link_does_not_equal_success(self):
        from scripts.source_automation import DIRECTORY, DAILY, INDEX
        import json
        report=build(json.loads(DIRECTORY.read_text()),
                     json.loads(DAILY.read_text()),{"sources":[]},
                     json.loads(INDEX.read_text()),
                     {"sources":[{"key":"opera-roma-season-2026-27",
                                  "status":"success","current_scan_verified":False,
                                  "links":20}]})
        roma=next(x for x in report["venues"] if x["city"]=="Roma"
                  and x["venue"]=="Teatro dell'Opera di Roma")
        self.assertEqual(roma["status"],"configured_not_operational")
        self.assertEqual(roma["source_attention"],"scan_failed")

    def test_blocked_and_never_checked_are_distinct(self):
        from scripts.source_automation import DIRECTORY, DAILY, INDEX
        import json
        report=build(json.loads(DIRECTORY.read_text()),
                     json.loads(DAILY.read_text()), {"sources":[]},
                     json.loads(INDEX.read_text()),
                     {"sources":[{"key":"modena-opera-2026-27",
                                  "status":"unavailable_or_invalid",
                                  "reason":"FetchUnavailable",
                                  "diagnostic":"official_robots_unavailable_or_invalid",
                                  "current_scan_verified":False}]})
        rows={(x["city"],x["venue"]):x for x in report["venues"]}
        modena=rows["Modena","Teatro Comunale Pavarotti-Freni"]
        self.assertEqual(modena["source_attention"],"scan_failed")
        self.assertEqual(next(s for s in modena["sources"] if s["source_key"]=="modena-opera-2026-27")["failure_reason"],
                         "official_robots_unavailable_or_invalid")
        self.assertEqual(rows["Livorno","Teatro Goldoni"]["source_attention"],"not_checked")
        self.assertIsNone(rows["Livorno","Teatro Goldoni"]["sources"][0]["failure_reason"])


if __name__=="__main__":
    unittest.main()
