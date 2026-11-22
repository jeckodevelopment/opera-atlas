"""Browser-level audit of the public Opera+ Atlas production pages.

The Apache rewrite may respond 200 even for unknown dynamic routes. A passing
check therefore requires the frontend to render the expected canonical work
after loading the live catalog, with no fallback warning. HTTP failures and
blocked/timeout checks are tracked separately from demonstrable missing pages.
Never infer entire-season coverage from this audit.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

from scripts.publish_catalog_v2 import ROOT, payload

BASE = "https://opera.plus/atlas/"
CATALOG = ROOT / "public/catalog/v2"
PROGRAMS = ROOT / "public/catalog/programs.json"
OUTPUT = ROOT / "public/catalog/live-publication-health.json"


def targets(manifest: dict, works: dict, venues: dict, stagings: dict, performances: dict,
            programs: dict) -> list[dict]:
    """Check every published solo staging and composite program, once each."""
    by_work = {item["id"]: item for item in works["works"]}
    per_staging = Counter(item["staging_id"] for item in performances["performances"])
    output = []
    for staging in stagings["stagings"]:
        work = by_work.get(staging.get("work_id"))
        if not work or not staging.get("url") or per_staging[staging["id"]] == 0:
            continue
        output.append({
            "id": staging["id"], "type": "staging", "work_id": work["id"],
            "title": work["title"], "venue_id": staging.get("venue_id"),
            "route": staging["url"], "expected_recite": per_staging[staging["id"]],
        })
    for program in programs.get("programs", []):
        if not program.get("performances"):
            continue
        output.append({
            "id": program["id"], "type": "program", "work_id": None,
            "title": program["title"], "venue_id": None,
            "route": "/programmi/" + program["id"] + "/",
            "expected_recite": len(program["performances"]),
        })
    for work in works["works"]:
        slug = work.get("route_slug") or work.get("slug")
        if slug:
            output.append({"id": work["id"], "type": "work", "work_id": work["id"],
                           "title": work["title"], "venue_id": None,
                           "route": "/opere/" + slug + "/", "expected_recite": None})
    for venue in venues["venues"]:
        if venue.get("city_slug") and venue.get("slug"):
            output.append({"id": venue["id"], "type": "venue", "work_id": None,
                           "title": venue.get("display_name") or venue["name"], "venue_id": venue["id"],
                           "route": "/" + venue["city_slug"] + "/" + venue["slug"] + "/",
                           "expected_recite": None})
    output.sort(key=lambda x: (x["type"], x["id"]))
    if len({x["route"] for x in output}) != len(output):
        raise ValueError("duplicate public routes in audit targets")
    return output


def classify(http_status: int | None, rendered_title: str | None,
             rendered_kind: str | None, detail_status: str,
             expected_title: str, expected_kind: str,
             *, error: str | None = None) -> str:
    """Fail closed: never confuse a generic 200 HTML shell with real content."""
    if error:
        return "unverified"  # Network/bot defenses/transient browser errors.
    if http_status == 404:
        return "missing_route"
    if http_status is None or http_status in (403, 429) or http_status >= 500:
        return "unverified"
    if http_status != 200:
        return "unexpected_http"
    if not rendered_title or not rendered_kind or rendered_kind.casefold() not in (
        "produzione", "programma composto", "opera del repertorio", "teatro",
    ):
        return "unverified"  # Generic/loading/failed shell is not real content.
    if "aggiornamenti non sono momentaneamente disponibili" in detail_status.casefold():
        return "fallback_catalog"
    if "non è stato possibile aprire" in detail_status.casefold():
        return "unverified"
    if "non corrisponde a una scheda pubblicata" in detail_status.casefold():
        return "missing_content"
    if rendered_kind.casefold().strip() != expected_kind.casefold().strip() or rendered_title.casefold().strip() != expected_title.casefold().strip():
        return "content_mismatch"
    return "verified_live"


def read_targets() -> tuple[list[dict], str]:
    def load(path: Path):
        return json.loads(path.read_text(encoding="utf-8"))
    manifest = load(CATALOG / "manifest.json")
    docs = {key: load(CATALOG / manifest["files"][key]["path"])
            for key in ("works", "venues", "stagings", "performances")}
    return targets(manifest, docs["works"], docs["venues"], docs["stagings"],
                   docs["performances"], load(PROGRAMS)), manifest["files"]["stagings"]["sha256"]


async def scan(browser, candidate: dict, semaphore: asyncio.Semaphore) -> dict:
    async with semaphore:
        context = await browser.new_context(locale="it-IT", ignore_https_errors=False)
        # Block large secondary media, but allow scripts, JSON, and stylesheets.
        await context.route("**/*", lambda route:
            route.abort() if route.request.resource_type in ("image", "font", "media")
            else route.continue_())
        page = await context.new_page()
        url = urljoin(BASE, candidate["route"].lstrip("/"))
        http = None
        title = kind = detail_status = None
        error = None
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            http = response.status if response else None
            if http == 200:
                await page.wait_for_function(
                    """() => {
                      const t=document.querySelector('#detail-title');
                      return t && t.textContent.trim() !== 'Caricamento…'
                    }""",
                    timeout=15000,
                )
                title = (await page.locator("#detail-title").inner_text()).strip()
                kind = (await page.locator("#kind").text_content() or "").strip()
                detail_status = (await page.locator("#detail-status").inner_text()).strip()
        except Exception as exc:
            error = type(exc).__name__
        finally:
            await context.close()
        expected_kinds = {"staging": "Produzione", "program": "Programma composto",
                          "work": "Opera del repertorio", "venue": "Teatro"}
        state = classify(http, title, kind, detail_status or "", candidate["title"],
                         expected_kinds[candidate["type"]], error=error)
        return {
            "id": candidate["id"], "type": candidate["type"],
            "venue_id": candidate["venue_id"], "title": candidate["title"],
            "route": candidate["route"], "status": state, "http_status": http,
            "expected_recite": candidate["expected_recite"],
            "rendered_title": title, "rendered_kind": kind,
            "detail_message": (detail_status or "")[:150], "error_type": error,
        }


async def execute(limit: int = 0) -> dict:
    from playwright.async_api import async_playwright
    items, catalog_sha = read_targets()
    if limit:
        items = items[:limit]
    with_limit = asyncio.Semaphore(8)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            results = await asyncio.gather(*(scan(browser, x, with_limit) for x in items))
        finally:
            await browser.close()
    counts = Counter(item["status"] for item in results)
    return {
        "schema_version": 1,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "catalog_release_sha256": catalog_sha,
        "site": BASE,
        "scope": "browser_rendered_catalog_routes_current_release",
        "definition": "Browser-rendered presence of catalogued works, venues, stagings and programs; does not certify all seasons or ticket availability. HTTP/network failures are non-conclusive unless a route or content absence is independently observed.",
        "total_checked": len(results),
        "totals": dict(sorted(counts.items())),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="for small smoke checks only")
    opts = parser.parse_args()
    report = asyncio.run(execute(opts.limit))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(payload(report))
    print(json.dumps({"checked": report["total_checked"], "totals": report["totals"],
                      "sample": report["results"][:4]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
