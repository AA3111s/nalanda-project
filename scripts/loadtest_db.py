"""Load test for the NGIS register.

Answers the real question: does this hold up at 25-35 cases/day for years,
with headroom for spike days?

  python scripts/loadtest_db.py [--rows 100000] [--keep]

Runs against a throwaway SQLite file by default so it never touches
data/ngis.db. Point NGIS_DATABASE_URL at a Postgres instance to run the
identical test there.
"""
import argparse, os, random, statistics, sys, tempfile, time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ap = argparse.ArgumentParser()
ap.add_argument("--rows", type=int, default=100_000)
ap.add_argument("--keep", action="store_true", help="don't delete the test DB")
args = ap.parse_args()

# Redirect to a scratch DB before importing db.py, unless a URL is supplied.
_tmp = None
if not os.environ.get("NGIS_DATABASE_URL"):
    _tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    _tmp.close()
    os.environ["NGIS_DATABASE_URL"] = f"sqlite:///{_tmp.name}"

import pandas as pd
from sqlalchemy import String, func, insert, select

import db
from classifier import SCHEMA
from real_data import BLOCK_CENSUS


def timed(fn, n=5):
    """Median wall time in ms over n runs (median resists one-off noise)."""
    ts = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        ts.append((time.perf_counter() - t0) * 1000)
    return statistics.median(ts)


def bulk_seed(total):
    """Insert `total` rows in chunks, mimicking years of real filings."""
    blocks = list(BLOCK_CENSUS.keys())
    cats = list(SCHEMA.keys())
    depts = [SCHEMA[c]["department"].split("(")[0].strip() for c in cats]
    rng = random.Random(7)
    eng = db.get_engine()
    today = date.today()
    chunk, done = 5_000, 0

    while done < total:
        batch = []
        for _ in range(min(chunk, total - done)):
            ci = rng.randrange(len(cats))
            age = rng.randrange(0, 365 * 3)          # 3 years of history
            filed = today - timedelta(days=age)
            status = rng.choices(db.STATUSES, weights=[45, 20, 35])[0]
            batch.append({
                "case_no": None, "filed_on": filed, "category": cats[ci],
                "department": depts[ci], "block": rng.choice(blocks),
                "priority": rng.choices(db.PRIORITIES, weights=[22, 48, 30])[0],
                "status": status, "source": "LoadTest", "is_demo": False,
                "resolved_on": filed + timedelta(days=rng.randrange(1, 30))
                               if status == "Resolved" else None,
                "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),
            })
        with eng.begin() as cx:
            first = cx.execute(insert(db.grievances).values(batch[0])).inserted_primary_key[0]
            if len(batch) > 1:
                cx.execute(insert(db.grievances), batch[1:])
            # Mirror what both production insert paths do: derive case_no from
            # the PK. Done set-wise here purely because this is a bulk seed.
            cx.execute(
                db.grievances.update()
                .where(db.grievances.c.case_no.is_(None))
                .values(case_no=("NLD-" + func.substr("00000" + func.cast(
                    db.grievances.c.id, String), -5, 5)))
                if db.backend() == "sqlite" else
                db.grievances.update()
                .where(db.grievances.c.case_no.is_(None))
                .values(case_no=func.concat("NLD-", func.lpad(
                    func.cast(db.grievances.c.id, String), 5, "0")))
            )
        done += len(batch)
        print(f"\r  seeded {done:,}/{total:,}", end="", flush=True)
    print()


print(f"\n=== NGIS load test — backend: {db.backend()} ===\n")
db.init_schema()

t0 = time.perf_counter()
bulk_seed(args.rows)
seed_s = time.perf_counter() - t0
with db.get_engine().connect() as cx:
    n = cx.execute(select(func.count()).select_from(db.grievances)).scalar_one()
print(f"  {n:,} rows in {seed_s:.1f}s  ({n/seed_s:,.0f} rows/sec)\n")

# ── read paths the pages actually drive ───────────────────────────────
print("Query latency (median of 5, cache bypassed):")
load = db.load_grievances.__wrapped__            # skip st.cache_data
ms_load = timed(lambda: load(True))
frame = load(True)
print(f"  full register load + Days_Open compute   {ms_load:8.1f} ms   ({len(frame):,} rows)")

print(f"  Today's Brief aggregates                 "
      f"{timed(lambda: (frame['Status'].eq('Open').sum(), frame['Priority'].eq('High').sum(), frame['Block'].value_counts().idxmax())):8.1f} ms")
print(f"  oldest-unresolved sort (register table)  "
      f"{timed(lambda: frame[frame['Status'] != 'Resolved'].sort_values('Days_Open', ascending=False).head(15)):8.1f} ms")
print(f"  Analytics groupby (Block x Priority)     "
      f"{timed(lambda: frame.groupby(['Block', 'Priority']).size()):8.1f} ms")
print(f"  Sankey groupby (Block->Dept->Status)     "
      f"{timed(lambda: (frame.groupby(['Block', 'Department']).size(), frame.groupby(['Department', 'Status']).size())):8.1f} ms")
print(f"  open-case picker (indexed, LIMIT-shaped) "
      f"{timed(lambda: db.case_options(True, True)):8.1f} ms")

# ── write path ────────────────────────────────────────────────────────
def one_insert(i):
    return db.insert_grievance({
        "category": "Water Supply", "department": "PHED", "block": "Hilsa",
        "priority": "Normal", "date_filed": date.today().isoformat(),
        "summary": f"load-test insert {i}", "source": "LoadTest",
    })

print("\nWrite path:")
print(f"  single insert (txn + case_no assign)     {timed(lambda: one_insert(-1), 5):8.1f} ms")

# ── spike day: 10x a normal day, all at once ──────────────────────────
SPIKE = 300
t0 = time.perf_counter()
spike_ids = [one_insert(i) for i in range(SPIKE)]
spike_s = time.perf_counter() - t0
print(f"  spike day: {SPIKE} cases sequentially     {spike_s*1000:8.1f} ms "
      f"({SPIKE/spike_s:,.0f}/sec)  unique={len(set(spike_ids))==SPIKE}")

# ── concurrency: the exact failure the old len()-based ID had ─────────
CONC, PER = 8, 25
t0 = time.perf_counter()
with ThreadPoolExecutor(max_workers=CONC) as pool:
    got = list(pool.map(one_insert, range(CONC * PER)))
conc_s = time.perf_counter() - t0
dupes = len(got) - len(set(got))
print(f"  {CONC} concurrent operators x {PER} cases    {conc_s*1000:8.1f} ms "
      f"({len(got)/conc_s:,.0f}/sec)")
print(f"  duplicate case numbers                   {dupes}  "
      f"{'PASS' if dupes == 0 else 'FAIL'}")

# ── status transitions ────────────────────────────────────────────────
with db.get_engine().connect() as cx:
    ids = [r[0] for r in cx.execute(
        select(db.grievances.c.id)
        .where(db.grievances.c.status == "Open").limit(200)).all()]
t0 = time.perf_counter()
for gid in ids:
    db.update_status(gid, "In Progress", note="load test", changed_by="bot")
tr_s = time.perf_counter() - t0
print(f"\n  {len(ids)} status transitions + audit rows    {tr_s*1000:8.1f} ms "
      f"({len(ids)/tr_s:,.0f}/sec)")

with db.get_engine().connect() as cx:
    final = cx.execute(select(func.count()).select_from(db.grievances)).scalar_one()
    hist = cx.execute(select(func.count()).select_from(db.status_history)).scalar_one()
    nulls = cx.execute(select(func.count()).select_from(db.grievances)
                       .where(db.grievances.c.case_no.is_(None))).scalar_one()
    distinct = cx.execute(select(func.count(func.distinct(db.grievances.c.case_no)))).scalar_one()

size = (os.path.getsize(_tmp.name) / 1e6) if _tmp else 0
print(f"\nIntegrity: {final:,} grievances · {hist:,} audit rows · "
      f"{nulls} null case_no · {distinct:,} distinct case_no "
      f"{'PASS' if nulls == 0 and distinct == final else 'FAIL'}")
if _tmp:
    print(f"On-disk size: {size:.1f} MB for {final:,} rows")

if _tmp and not args.keep:
    for suffix in ("", "-wal", "-shm"):
        try: os.unlink(_tmp.name + suffix)
        except OSError: pass
elif _tmp:
    print(f"\nTest DB kept at {_tmp.name}")
