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


def published_at(ref: str) -> dict:
    """Read the actual public feed at a Git revision, not the draft registry."""
    manifest = json.loads(git("show", f"{ref}:public/catalog/v2/manifest.json"))
    channels = {}
    for channel in ("works", "venues", "stagings"):
        path = "public/catalog/v2/" + manifest["files"][channel]["path"]
        contents = json.loads(git("show", f"{ref}:{path}"))
        channels[channel] = {record["id"]: record for record in contents[channel]}
    return channels


def new_entities(before: dict, after: dict) -> list[dict]:
    """Compare permanent *public* IDs, never title strings or performance dates."""
    notices = []
    works = after["works"]
    venues = after["venues"]
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


def parse_recipients(config: str) -> list[str]:
    """Read a comma/newline-delimited secret without logging personal addresses."""
    import re
    recipients = []
    seen = set()
    for address in re.split(r"[,;\n]+", config):
        address = address.strip()
        if not address:
            continue
        if "@" not in address or any(char.isspace() for char in address):
            raise ValueError("invalid Atlas notification recipient configuration")
        if address.casefold() not in seen:
            recipients.append(address)
            seen.add(address.casefold())
    return recipients


def safe_resend_error(error: urllib.error.HTTPError) -> str:
    """Report only bounded, non-sensitive Resend error codes.

    The response can contain addresses, request payloads or tokens, so never
    print its free-form message or raw JSON in GitHub Actions logs.
    """
    try:
        response = json.loads(error.read(8192).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, OSError):
        response = {}
    code = response.get("name") or response.get("code") if isinstance(response, dict) else None
    if isinstance(code, str) and len(code) <= 80 and all(char.isalnum() or char in "_-" for char in code):
        return f"Resend HTTP {error.code}, error code: {code}"
    return f"Resend HTTP {error.code}, response code unavailable"


def send(notice: dict, api_key: str, sender: str, recipients: list[str]) -> None:
    from scripts.notification_email import render_email
    subject = f"[Opera+ Atlas] {notice['kind']}: {notice['title']}"
    html, plain = render_email(notice)
    payload = json.dumps({
        "from": sender,
        "to": recipients,
        "subject": subject,
        "html": html,
        "text": plain,
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
    parser.add_argument("--only-ids", default="", help="Optional comma-separated immutable entity IDs for a controlled replay")
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
        notices = new_entities(published_at(args.base), published_at(head))
    except (KeyError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"::warning::Atlas notification comparison failed: {exc}", file=sys.stderr)
        return 0
    if args.only_ids:
        selected = {item.strip() for item in args.only_ids.split(",") if item.strip()}
        notices = [notice for notice in notices if notice["id"] in selected]
    print(f"Newly published works/productions: {len(notices)}")
    if not notices:
        return 0
    api_key = os.environ.get("RESEND_API_KEY", "")
    sender = os.environ.get("ATLAS_NOTIFICATION_FROM", "")
    recipient_config = os.environ.get("ATLAS_NOTIFICATION_TO", "")
    if not all((api_key, sender, recipient_config)):
        print("::warning::Resend notifications not configured (RESEND_API_KEY, ATLAS_NOTIFICATION_FROM, ATLAS_NOTIFICATION_TO).")
        return 0
    try:
        recipients = parse_recipients(recipient_config)
    except ValueError:
        print("::warning::Invalid recipient secret configuration.", file=sys.stderr)
        return 0
    if not recipients:
        print("::warning::No valid diagnostic recipients configured.", file=sys.stderr)
        return 0
    failed = 0
    for notice in notices:
        try:
            send(notice, api_key, sender, recipients)
            print(f"Resend accepted notification for {notice['kind']} {notice['id']}")
        except urllib.error.HTTPError as exc:
            failed += 1
            print(f"::warning::Notification for {notice['id']} failed: {safe_resend_error(exc)}", file=sys.stderr)
        except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            failed += 1
            print(f"::warning::Notification for {notice['id']} failed: {type(exc).__name__}", file=sys.stderr)
    if failed:
        print(f"::warning::{failed} publication notifications failed; catalog remains published.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
