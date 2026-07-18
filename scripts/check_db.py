"""Connectivity + schema probe. Run this right after pasting your Supabase URL.

    python scripts/check_db.py

Reads .streamlit/secrets.toml (or NGIS_DATABASE_URL). Reports which backend it
reached, creates the schema if absent, and prints row counts. Never prints the
password — only the host, so it is safe to paste the output when asking for help.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, select

import db


def redacted(url: str) -> str:
    """host:port/dbname only — the password never reaches the terminal."""
    try:
        from sqlalchemy.engine import make_url
        u = make_url(url)
        return f"{u.drivername} → {u.host}:{u.port or ''}/{u.database}"
    except Exception:
        return "(unparseable URL)"


url = db._database_url()
print("\n=== NGIS database probe ===\n")
if url:
    print(f"  configured : {redacted(url)}")
else:
    print("  configured : none — falling back to local SQLite")
    print(f"               {db._SQLITE_PATH}")

try:
    engine = db.get_engine()
    with engine.connect() as cx:
        cx.execute(select(1))
    print(f"  connected  : OK ({db.backend()})")
except Exception as exc:
    print(f"  connected  : FAILED\n\n  {type(exc).__name__}: {exc}\n")
    print("  Common causes:")
    print("   · Supabase project is paused (free tier sleeps after ~7 days idle)")
    print("   · password not URL-encoded — @ : / must be percent-escaped")
    print("   · missing ?sslmode=require")
    print("   · using the direct host from a network that blocks 5432 —")
    print("     use the transaction pooler on 6543 instead")
    sys.exit(1)

db.init_schema()
print("  schema     : present")

with db.get_engine().connect() as cx:
    total = cx.execute(select(func.count()).select_from(db.grievances)).scalar_one()
    demo = cx.execute(select(func.count()).select_from(db.grievances)
                      .where(db.grievances.c.is_demo.is_(True))).scalar_one()
    hist = cx.execute(select(func.count()).select_from(db.status_history)).scalar_one()
    nulls = cx.execute(select(func.count()).select_from(db.grievances)
                       .where(db.grievances.c.case_no.is_(None))).scalar_one()

print(f"\n  grievances : {total:,}  ({demo:,} demo, {total - demo:,} real)")
print(f"  audit rows : {hist:,}")
print(f"  integrity  : {'OK' if nulls == 0 else f'{nulls} rows missing case_no'}\n")
