"""Read-only LIVE validation of the Festival Verdi connector.

Uses the project's strict controlled HTTP fetch and robots policy.
Does not modify the canonical registry, candidates, public output or images.
A successful check demonstrates live index + real page parsing, NOT publication.
"""
from __future__ import annotations

import json
from collections import Counter
from opera_atlas.controlled_fetch import fetch_official_html
from opera_atlas.db import connect, migrate
from opera_atlas.festival_verdi_future import extract_index, parse_detail
from scripts.publish_catalog_v2 import ROOT

INDEX = "https://teatroregioparma.it/categoria-spettacoli/edizione-27-festival-verdi/"
EXPECTED = {
    "https://teatroregioparma.it/spettacolo/aroldo/": ("Aroldo", "Teatro Regio di Parma", 3),
    "https://teatroregioparma.it/spettacolo/la-traviata/": ("La traviata", "Teatro Regio di Parma", 4),
    "https://teatroregioparma.it/spettacolo/stiffelio/": ("Stiffelio", "Teatro Giuseppe Verdi", 4),
}


def verify(fetcher=fetch_official_html) -> dict:
    registry = json.loads((ROOT / "data/identity-registry.json").read_text(encoding="utf-8"))
    db = connect()
    try:
        migrate(db)
        db.execute("INSERT OR IGNORE INTO sources (official_url, access_status) VALUES (?, 'approved')",
                   ("https://teatroregioparma.it/",))
        source_id = db.execute(
            "SELECT id FROM sources WHERE official_url=?", ("https://teatroregioparma.it/",)
        ).fetchone()["id"]

        def read(url: str) -> str:
            page = fetcher(db, source_id=source_id, url=url, network_enabled=True)
            if page.url != url:
                raise ValueError("official source URL unexpectedly changed")
            return page.html

        # A festival index must never pull the general season or Verdi Off.
        urls = extract_index(read(INDEX), url=INDEX, min_links=3)
        if set(urls) != set(EXPECTED):
            raise ValueError(f"official 2027 repertoire differs: {urls!r}")
        rows = []
        for url in urls:
            facts = parse_detail(read(url), url=url, year=2027, registry=registry)
            title, venue, count = EXPECTED[url]
            if len(facts) != count or any(
                f["event_title"] != title or f["venue"] != venue or
                f["composer"] != "Giuseppe Verdi" or
                not f["date"].startswith("2027-10-")
                for f in facts
            ):
                raise ValueError(f"invalid confirmed dates or venue for {url}")
            rows.extend(facts)
    finally:
        db.close()
    identities = {(f["event_title"], f["venue"], f["date"], f["starts_at"]) for f in rows}
    if len(rows) != 11 or len(identities) != 11:
        raise ValueError("duplicate or missing Festival Verdi 2027 recite")
    return {
        "source_key": "festival-verdi-rolling",
        "result": "live_index_and_detail_parsing_verified",
        "edition": "2027",
        "opera_pages": len(urls),
        "performances": len(rows),
        "works": dict(Counter(f["event_title"] for f in rows)),
        "venues": dict(Counter(f["venue"] for f in rows)),
        "publication": "not_performed",
    }


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False, sort_keys=True))
