"""Offline staged production evidence; no web access or public publication."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .db import connect, migrate
from .operalombardia import stage_dates


def main() -> None:
    parser=argparse.ArgumentParser(description="Stage OperaLombardia date-only evidence")
    parser.add_argument("--db",required=True)
    parser.add_argument("--html",required=True,help="Locally saved, permitted official HTML")
    parser.add_argument("--url",required=True)
    parser.add_argument("--title",required=True)
    parser.add_argument("--source-id",required=True,type=int)
    parser.add_argument("--apply",action="store_true")
    args=parser.parse_args()
    conn=connect(args.db)
    try:
        migrate(conn)
        count=stage_dates(
            conn,source_id=args.source_id,
            html=Path(args.html).read_text(encoding="utf-8"),
            url=args.url,title=args.title,
        )
        if args.apply:
            conn.commit()
        else:
            conn.rollback()
        print(json.dumps({"staged":count,"committed":bool(args.apply),
                          "public_performances_created":0}))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__=="__main__":
    main()
