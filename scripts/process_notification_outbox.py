"""Durable, automatically retried publication email outbox.

Only immutable work/staging IDs newly appearing after the bootstrap snapshot
are candidates. A dedicated Git branch records Resend acceptance; there is no
one-shot notification dependency on the catalog publisher finishing cleanly.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.error

from scripts.notify_publications import (
    new_entities, parse_recipients, published_at, safe_resend_error, send,
)

LEDGER_BRANCH = "atlas-notification-ledger"
LEDGER_PATH = "data/notification-ledger.json"


def git(*args: str, cwd: str | None = None) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def pending_notices(before: dict, current: dict, accepted_ids: set[str]) -> list[dict]:
    """Derive pending messages from public IDs, not mutable candidate records."""
    return [
        notice for notice in new_entities(before, current)
        if notice["id"] not in accepted_ids
    ]


def load_ledger() -> dict:
    git("fetch", "--quiet", "origin",
        f"refs/heads/{LEDGER_BRANCH}:refs/remotes/origin/{LEDGER_BRANCH}")
    ledger = json.loads(git("show", f"origin/{LEDGER_BRANCH}:{LEDGER_PATH}"))
    if (ledger.get("version") != 1
            or not isinstance(ledger.get("baseline_sha"), str)
            or not isinstance(ledger.get("accepted_ids"), list)
            or not isinstance(ledger.get("attempts"), dict)):
        raise ValueError("Invalid durable notification ledger")
    return ledger


def commit_ledger(ledger: dict) -> None:
    """Persist delivery results to an independent Git ref.

    Workflow-level concurrency serializes writers; a non-fast-forward push
    is deliberately not forced. It fails visibly and retries on the next run.
    """
    with tempfile.TemporaryDirectory(prefix="atlas-notifications-") as directory:
        git("worktree", "add", "--quiet", "--detach", directory, f"origin/{LEDGER_BRANCH}")
        try:
            path = Path(directory) / LEDGER_PATH
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
            git("add", LEDGER_PATH, cwd=directory)
            if git("diff", "--cached", "--quiet", "--exit-code", cwd=directory) == "":
                # git diff --quiet has no output; its return code is 1 if changed.
                return
        except subprocess.CalledProcessError as exc:
            if exc.returncode != 1:
                raise
            git("config", "user.name", "github-actions[bot]", cwd=directory)
            git("config", "user.email",
                "41898282+github-actions[bot]@users.noreply.github.com", cwd=directory)
            git("commit", "-m", "data(notifications): persist Resend acceptance and retries [skip ci]",
                cwd=directory)
            git("push", "origin", f"HEAD:refs/heads/{LEDGER_BRANCH}", cwd=directory)
        finally:
            git("worktree", "remove", "--force", directory)


def main() -> int:
    try:
        git("fetch", "--quiet", "origin", "main")
        git("checkout", "--quiet", "--detach", "origin/main")
        ledger = load_ledger()
        before = published_at(ledger["baseline_sha"])
        current = published_at("HEAD")
        accepted = set(ledger["accepted_ids"])
        notices = pending_notices(before, current, accepted)
    except (subprocess.CalledProcessError, KeyError, ValueError, OSError) as exc:
        print(f"::error::Cannot inspect public catalog or durable delivery ledger: {type(exc).__name__}",
              file=sys.stderr)
        return 1

    print(f"Atlas pending publication notifications: {len(notices)}")
    if not notices:
        return 0

    api_key = os.environ.get("RESEND_API_KEY", "")
    sender = os.environ.get("ATLAS_NOTIFICATION_FROM", "")
    to = os.environ.get("ATLAS_NOTIFICATION_TO", "")
    if not all((api_key, sender, to)):
        print("::error::Resend delivery secrets are incomplete; queue retained.", file=sys.stderr)
        return 1
    try:
        recipients = parse_recipients(to)
        if not recipients:
            raise ValueError("No recipients")
    except ValueError:
        print("::error::Invalid recipient configuration; queue retained.", file=sys.stderr)
        return 1

    failures = 0
    for notice in notices:
        entity_id = notice["id"]
        try:
            send(notice, api_key, sender, recipients)
        except urllib.error.HTTPError as exc:
            failures += 1
            print(f"::warning::Notification {entity_id} failed: {safe_resend_error(exc)}",
                  file=sys.stderr)
        except (urllib.error.URLError, TimeoutError, RuntimeError, OSError) as exc:
            failures += 1
            print(f"::warning::Notification {entity_id} failed: {type(exc).__name__}",
                  file=sys.stderr)
        else:
            accepted.add(entity_id)
            print(f"Resend accepted notification for {notice['kind']} {entity_id}")
        ledger["attempts"][entity_id] = ledger["attempts"].get(entity_id, 0) + 1
        # Persist each acceptance immediately, limiting replays after runner failure.
        ledger["accepted_ids"] = sorted(accepted)
        try:
            commit_ledger(ledger)
        except (subprocess.CalledProcessError, OSError):
            print(f"::error::Failed to persist notification state for {entity_id}; "
                  "will reconcile on next run.", file=sys.stderr)
            return 1

    if failures:
        print(f"::error::{failures} email notifications remain pending; automatic retry scheduled.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
