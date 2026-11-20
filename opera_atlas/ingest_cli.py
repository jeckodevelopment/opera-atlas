"""Offline import and export tools for local operator-approved snapshots."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .db import connect, migrate
from .ingestion import export_public_catalog, import_regio_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="Opera Atlas ingestion (offline snapshots)")
    parser.add_argument("--db", required=True, help="SQLite work database")
    sub = parser.add_subparsers(dest="command", required=True)
    imp = sub.add_parser("import-regio", help="Import saved official detail HTML")
    imp.add_argument("--html", required=True)
    imp.add_argument("--url", required=True)
    imp.add_argument("--source-id", required=True, type=int)
    imp.add_argument("--venue-id", required=True, type=int)
    imp.add_argument("--production-id", required=True, type=int)
    imp.add_argument("--title", required=True)
    imp.add_argument("--composer", required=True)
    imp.add_argument("--apply", action="store_true", help="Commit only when explicitly requested")
    exp = sub.add_parser("export", help="Export public JSON after review")
    exp.add_argument("--output", required=True)
    args = parser.parse_args()
    connection = connect(args.db)
    try:
        migrate(connection)
        if args.command == "export":
            print(json.dumps({"exported":export_public_catalog(connection,args.output)}))
            return
        html = Path(args.html).read_text(encoding="utf-8")
        summary = import_regio_snapshot(
            connection, html=html, source_url=args.url,
            source_id=args.source_id, venue_id=args.venue_id,
            production_id=args.production_id, expected_title=args.title,
            expected_composer=args.composer,
        )
        if args.apply:
            connection.commit()
        else:
            connection.rollback()
        print(json.dumps({"discovered":summary.discovered,
                          "linked":summary.linked,
                          "review":summary.review,
                          "committed":bool(args.apply)}))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
