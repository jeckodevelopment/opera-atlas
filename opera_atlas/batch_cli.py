"""Opt-in operator batch CLI. No network or commit by default."""
from __future__ import annotations

import argparse
import json

from .batch import load_manifest, run_batch
from .db import connect, migrate


def main() -> None:
    parser = argparse.ArgumentParser(description="Bounded operator-approved Regio detail batch")
    parser.add_argument("--db", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    entries = load_manifest(args.manifest)
    conn = connect(args.db)
    try:
        migrate(conn)
        summary = run_batch(conn, entries, network_enabled=args.allow_network)
        if args.apply:
            conn.commit()
        else:
            conn.rollback()
        print(json.dumps({**summary.__dict__, "committed": bool(args.apply)}))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
