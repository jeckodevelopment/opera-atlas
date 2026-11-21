"""Send diagnostic emails only for newly published canonical Atlas entities.

Called after a successful catalog push. Never runs during scans or CI.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

REPO = "jeckodevelopment/opera-atlas"
ROOT_URL = "https://opera.plus/atlas"


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def registry_at(ref: str) -> dict:
    return json.loads(git("show", f"{ref}:data/identity-registry.json"))


def new_entities(before: dict, after: dict) -> list[dict]:
    """Compare permanent *public* IDs, never title strings or performance dates."""
    notices = []
    works = {record["id"]: record for record in after["works"].values()}
    venues = {record["id"]: record for record in after["venues"].values()}
    for channel in ("works", "stagings"):
        previous_ids = {record["id"] for record in before[channel].values()}
        for record in after[channel].values():
            if record["id"] in previous_ids:
                continue
            if channel == "works":
                slug = record.get("route_slug", record["slug"])
                notices.append({
                    "kind": "Nuova opera",
                    "id": record["id"],
                    "title": record["title"],
                    "details": f"Compositore: {record.get('composer', 'Non indicato')}",
                    "url": f"{ROOT_URL}/opere/{slug}/",
                })
            else:
                work = works[record["work_id"]]
                venue = venues[record["venue_id"]]
                route = record.get("route_slug", work["slug"])
                notices.append({
                    "kind": "Nuova produzione",
                    "id": record["id"],
                    "title": work["title"],
                    "details": f"Teatro: {venue['name']} · Città: {venue['city']}",
                    "url": f"{ROOT_URL}/{venue['city_slug']}/{venue['slug']}/{route}/",
                })
    return notices


def send(notice: dict, api_key: str, sender: str, recipient: str) -> None:
    from html import escape
    subject = f"[Opera+ Atlas] {notice['kind']}: {notice['title']}"
    html = "<h2>" + escape(notice["kind"]) + "</h2>" + "".join(
        f"<p><b>{escape(label)}:</b> {escape(str(value))}</p>"
        for label, value in (
            ("Titolo", notice["title"]),
            ("ID", notice["id"]),
            ("Dettagli", notice["details"]),
        )
    ) + f'<p><a href="{escape(notice["url"], quote=True)}">Apri la scheda su Opera+ Atlas</a></p>'
    payload = json.dumps({
        "from": sender, "to": [recipient], "subject": subject, "html": html,
    }).encode("utf-8")
    request = urllib.request.Request(
        "https://api.resend.com/emails", payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": f"atlas-published-{notice['id']}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        if not (200 <= response.status < 300):
            raise RuntimeError(f"Resend HTTP {response.status}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True, help="Git SHA before this publication checkpoint")
    args = parser.parse_args()
    # Do not notify when GitHub has not actually accepted this catalog commit.
    git("fetch", "--quiet", "origin", "main")
    head = git("rev-parse", "HEAD")
    published = subprocess.run(
        ["git", "merge-base", "--is-ancestor", head, "origin/main"],
        check=False,
    ).returncode == 0
    if not published:
        print("No diagnostic emails: catalog publication deferred.")
        return 0
    try:
        notices = new_entities(registry_at(args.base), registry_at(head))
    except (KeyError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"::warning::Atlas notification comparison failed: {exc}", file=sys.stderr)
        return 0
    print(f"Newly published works/productions: {len(notices)}")
    if not notices:
        return 0
    api_key = os.environ.get("RESEND_API_KEY", "")
    sender = os.environ.get("ATLAS_NOTIFICATION_FROM", "")
    recipient = os.environ.get("ATLAS_NOTIFICATION_TO", "")
    if not all((api_key, sender, recipient)):
        print("::warning::Resend notifications not configured (RESEND_API_KEY, ATLAS_NOTIFICATION_FROM, ATLAS_NOTIFICATION_TO).")
        return 0
    failed = 0
    for notice in notices:
        try:
            send(notice, api_key, sender, recipient)
            print(f"Resend accepted notification for {notice['kind']} {notice['id']}")
        except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            failed += 1
            print(f"::warning::Notification for {notice['id']} failed: {exc}", file=sys.stderr)
    if failed:
        print(f"::warning::{failed} publication notifications failed; catalog remains published.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
