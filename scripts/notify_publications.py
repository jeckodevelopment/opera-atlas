"""Send diagnostic emails only for newly published canonical Atlas entities.

Called after a successful catalog push. Never runs during scans or CI.
"""
from __future__ import annotations

import argparse
from datetime import date
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
    for channel in ("works", "venues", "stagings", "performances"):
        path = "public/catalog/v2/" + manifest["files"][channel]["path"]
        contents = json.loads(git("show", f"{ref}:{path}"))
        channels[channel] = {record["id"]: record for record in contents[channel]}
    return channels


def new_entities(before: dict, after: dict) -> list[dict]:
    """Compare permanent *public* IDs, never title strings or performance dates."""
    notices = []
    works = after["works"]
    venues = after["venues"]
    performances_by_staging = {}
    for performance in after.get("performances", {}).values():
        if performance.get("status") == "cancelled":
            continue
        day = performance.get("local_date", "")
        try:
            scheduled = date.fromisoformat(day)
        except (TypeError, ValueError):
            continue
        if scheduled < date.today():
            continue
        performances_by_staging.setdefault(performance.get("staging_id"), []).append(performance)
    for scheduled in performances_by_staging.values():
        scheduled.sort(key=lambda performance: (
            performance["local_date"],
            performance.get("starts_at") or "",
            performance.get("id") or "",
        ))
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
                    "performances": performances_by_staging.get(record["id"], []),
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
    """Describe an HTTP rejection without exposing response text or headers.

    No untrusted response values are emitted except a tightly validated
    machine-readable error code. Useful for differentiating an API rejection
    from a CDN/WAF challenge, including an HTML 403.
    """
    headers = error.headers
    raw_type = headers.get("Content-Type", "") if headers else ""
    mime = raw_type.split(";", 1)[0].strip().lower()
    allowed_types = {
        "application/json", "application/problem+json", "text/html",
        "text/plain", "application/octet-stream",
    }
    content_type = mime if mime in allowed_types else "other/unknown"
    via_cloudflare = bool(headers and (headers.get("CF-Ray") or
                                       headers.get("CF-Cache-Status")))
    try:
        raw_body = error.read(8193)
    except OSError:
        raw_body = b""
    truncated = len(raw_body) > 8192
    sample = raw_body[:8192]
    body_format = "empty"
    code = None
    if sample:
        try:
            response = json.loads(sample.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            stripped = sample.lstrip().lower()
            if stripped.startswith((b"<!doctype html", b"<html", b"<head", b"<body")):
                body_format = "html"
            elif all(byte in (9, 10, 13) or 32 <= byte < 127 for byte in sample[:256]):
                body_format = "text"
            else:
                body_format = "other"
        else:
            body_format = "json"
            if isinstance(response, dict):
                code = response.get("name") or response.get("code")
                if not code and isinstance(response.get("error"), dict):
                    nested = response["error"]
                    code = nested.get("name") or nested.get("code")
    metadata = (
        f"Resend HTTP {error.code}; response-type={content_type}; "
        f"body-format={body_format}; edge-header-present={'yes' if via_cloudflare else 'no'}; "
        f"body-truncated={'yes' if truncated else 'no'}"
    )
    if isinstance(code, str) and 0 < len(code) <= 80 and all(
        char.isalnum() or char in "_-" for char in code
    ):
        metadata += f"; error-code={code}"
    else:
        metadata += "; error-code=unavailable"
    return metadata


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
            "User-Agent": "OperaAtlas-Notifications/1.0 (GitHub Actions; jeckodevelopment/opera-atlas)",
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
