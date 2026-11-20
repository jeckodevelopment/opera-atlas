"""Explicit one-page network scan; no periodic task or recursive spider."""
from __future__ import annotations

import argparse
import json

from .db import connect, migrate
from .scan import scan_regio_detail


def main():
    parser = argparse.ArgumentParser(description="One-page, opt-in Teatro Regio scan")
    parser.add_argument("--db", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--source-id", type=int, required=True)
    parser.add_argument("--venue-id", type=int, required=True)
    parser.add_argument("--production-id", type=int, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--composer", required=True)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    conn = connect(args.db)
    try:
        migrate(conn)
        outcome = scan_regio_detail(
            conn, url=args.url, source_id=args.source_id,
            venue_id=args.venue_id, production_id=args.production_id,
            title=args.title, composer=args.composer,
            network_enabled=args.allow_network,
        )
        if args.apply:
            conn.commit()
        else:
            conn.rollback()
        print(json.dumps({
            "outcome":outcome.outcome,
            "discovered":outcome.discovered,
            "linked":outcome.linked,
            "review":outcome.review,
            "committed":bool(args.apply),
        }))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
