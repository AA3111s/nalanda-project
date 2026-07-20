"""
NGIS persistence layer — the grievance register.

One code path, two drivers, chosen by configuration:

  · `st.secrets["database"]["url"]` set  → Postgres (Supabase) — production
  · unset                                → SQLite at data/ngis.db — local/dev

So the app runs with zero setup and moves to Supabase by adding one secret.

Design notes that are load-bearing (do not "simplify" these away):

  · `case_no` is assigned from the DB-generated primary key INSIDE the insert
    transaction. The previous scheme derived it from `len(dataframe)`, which
    collides the moment two operators save at once and exhausts NLD-999 in
    about a month at 30 cases/day.

  · `Days_Open` is NEVER stored. It was previously a frozen integer written as
    0 on save, so every real case read 0 days forever and the >20d/>10d
    escalation in the UI could never fire. It is computed on read from
    `filed_on` (and `resolved_on` for closed cases).

  · `priority` is normalised at the write boundary. classifier.py emits
    "Normal", but every filter, badge class and sort in app.py expects
    High/Medium/Low — a "Normal" row matched no filter and sorted as NaN.
    The CHECK constraint stops that regressing.
"""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
from sqlalchemy import (
    Boolean, CheckConstraint, Column, Date, DateTime, Float, ForeignKey,
    Index, Integer, MetaData, String, Table, Text, create_engine, func,
    insert, select, update,
)
from sqlalchemy.pool import NullPool, QueuePool

# ── vocabularies (mirrored by CHECK constraints below) ────────────────────
PRIORITIES = ("High", "Medium", "Low")
STATUSES = ("Open", "In Progress", "Resolved")
OPEN_STATUSES = ("Open", "In Progress")

# classifier.py emits "Normal"; the UI speaks High/Medium/Low.
_PRIORITY_ALIASES = {"normal": "Medium", "med": "Medium", "urgent": "High"}

_SQLITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "data", "ngis.db")

# Timestamps are stored in UTC (correct for a database that may be read from
# anywhere) but every reader of this register is in one district of Bihar, so
# they are displayed in IST. India has no DST, so a fixed offset is exact and
# avoids depending on a tz database being present on the host.
IST_OFFSET = timedelta(hours=5, minutes=30)


def to_ist(ts):
    """UTC timestamp -> IST, for display only."""
    return None if ts is None or pd.isna(ts) else ts + IST_OFFSET

metadata = MetaData()

grievances = Table(
    "grievances", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    # Nullable because it is filled from `id` in the same transaction as the
    # insert; it is UNIQUE and never null once that transaction commits.
    Column("case_no", String(16), unique=True, index=True),
    Column("filed_on", Date, nullable=False),
    Column("category", String(120), nullable=False),
    Column("department", String(160), nullable=False),
    Column("block", String(80), nullable=False),
    Column("priority", String(10), nullable=False),
    Column("status", String(16), nullable=False, default="Open"),
    Column("source", String(32), nullable=False, default="Manual"),
    # PII — see the retention note in the plan before exporting any of this.
    Column("complainant_name", String(120)),
    Column("village", String(120)),
    Column("summary", Text),
    Column("transcription", Text),
    Column("confidence", Float),
    Column("is_demo", Boolean, nullable=False, default=False),
    Column("resolved_on", Date),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    Column("updated_at", DateTime, nullable=False, default=datetime.utcnow,
           onupdate=datetime.utcnow),
    CheckConstraint(f"priority IN {PRIORITIES}", name="ck_grievance_priority"),
    CheckConstraint(f"status IN {STATUSES}", name="ck_grievance_status"),
    Index("ix_grievances_status_filed", "status", "filed_on"),
    Index("ix_grievances_block", "block"),
    Index("ix_grievances_priority", "priority"),
    Index("ix_grievances_is_demo", "is_demo"),
)

status_history = Table(
    "status_history", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("grievance_id", Integer,
           ForeignKey("grievances.id", ondelete="CASCADE"),
           nullable=False, index=True),
    Column("from_status", String(16)),
    Column("to_status", String(16), nullable=False),
    Column("note", Text),
    Column("changed_by", String(80), nullable=False, default="operator"),
    Column("changed_at", DateTime, nullable=False, default=datetime.utcnow),
)


# ── engine ────────────────────────────────────────────────────────────────
def _secrets_file_exists() -> bool:
    """True if Streamlit has a secrets.toml to read.

    Checked explicitly because merely *touching* st.secrets when no file
    exists makes Streamlit render a red "No secrets files found" banner into
    the running app — once per rerun. Running on local SQLite is a supported
    default, not an error, so it must stay silent.
    """
    candidates = (
        os.path.join(os.path.expanduser("~"), ".streamlit", "secrets.toml"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     ".streamlit", "secrets.toml"),
    )
    return any(os.path.isfile(p) for p in candidates)


class ConfigError(RuntimeError):
    """A database was *attempted* and is unusable. Never fall back silently.

    Carries `.hint`: numbered remedy steps the UI renders verbatim. Streamlit
    Cloud redacts exception text, so app.py must catch this and draw the
    message itself — an uncaught raise shows the operator nothing.
    """

    def __init__(self, summary: str, hint: list[str]):
        super().__init__(summary + "  " + " ".join(hint))
        self.summary = summary
        self.hint = hint


_CLOUD_BLOCK = (
    '[database]\n'
    'url = "postgresql://postgres.<ref>:<password>'
    '@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require"'
)


def _database_url() -> str | None:
    """Configured Postgres URL, or None to fall back to local SQLite.

    Four distinct states, deliberately not conflated:

      1. NGIS_DATABASE_URL set          -> use it
      2. no secrets at all              -> None (SQLite, silent, intended)
      3. secrets present, no [database] -> None (SQLite, silent, intended)
      4. [database] present but broken  -> ConfigError

    (2) and (3) are "no database was asked for". (4) is "a database was
    asked for and cannot be used" — only that one may refuse to run,
    because falling back there would write real grievances to storage a
    redeploy deletes.

    An earlier version tested only for the *presence of a secrets file* and
    treated that as (4). Streamlit Cloud materialises a secrets file as soon
    as ANY secret is set, so every deployment with, say, only a Gemini key
    crashed on load. That is what took the live site down.
    """
    env = os.environ.get("NGIS_DATABASE_URL")
    if env:
        return env
    if not _secrets_file_exists():
        return None

    try:
        # Membership first: a missing section is an ordinary outcome, not an
        # exception, so it can never be mistaken for a broken config.
        has_section = "database" in st.secrets
    except Exception as exc:
        raise ConfigError(
            f"Your secrets could not be parsed as TOML ({type(exc).__name__}).",
            [
                "1. A bare connection URL is NOT valid TOML — the ':' in "
                "'postgresql://' is read as a key name.",
                "2. It must be a section and a quoted key, exactly:",
                _CLOUD_BLOCK,
                "3. On Streamlit Cloud paste that whole block into "
                "App → ⋮ → Settings → Secrets. Locally it goes in "
                ".streamlit/secrets.toml.",
            ],
        ) from exc

    if not has_section:
        return None          # secrets exist for other keys; no DB requested

    try:
        url = st.secrets["database"]["url"]
    except Exception as exc:
        raise ConfigError(
            "Your secrets have a [database] section but no readable 'url' key.",
            ["1. Add a quoted url key under [database]:", _CLOUD_BLOCK],
        ) from exc

    if not url or not str(url).strip():
        raise ConfigError(
            "[database] url is empty.",
            ["1. Paste the Supabase connection URI:", _CLOUD_BLOCK],
        )
    if any(tok in url for tok in ("<ref>", "<password>", "<region>",
                                  "YOUR-PASSWORD", "YOUR_PASSWORD")):
        raise ConfigError(
            "[database] url still contains the example placeholders.",
            [
                "1. Replace <ref>, <password> and <region> with real values "
                "— including the square brackets if you copied "
                "'[YOUR-PASSWORD]' from the Supabase dashboard.",
                "2. Get it from Supabase → Project Settings → Database → "
                "Connection string → Transaction pooler.",
            ],
        )
    return url


def storage_is_ephemeral() -> bool:
    """True when running on local SQLite.

    On a hosted deployment that means the container filesystem: every
    redeploy or sleep wipes it. The UI warns loudly on the strength of this.
    """
    return backend() == "sqlite"


@st.cache_resource
def get_engine():
    """One Engine per process.

    cache_resource (not cache_data) is required: an Engine is a live
    connection pool, not a serialisable value.
    """
    url = _database_url()

    if not url:
        os.makedirs(os.path.dirname(_SQLITE_PATH), exist_ok=True)
        eng = create_engine(
            f"sqlite:///{_SQLITE_PATH}",
            connect_args={"check_same_thread": False},
            future=True,
        )
        # WAL lets readers proceed during a write — Streamlit reruns read
        # constantly while an operator is saving.
        with eng.begin() as cx:
            cx.exec_driver_sql("PRAGMA journal_mode=WAL")
            cx.exec_driver_sql("PRAGMA synchronous=NORMAL")
            cx.exec_driver_sql("PRAGMA busy_timeout=5000")
        return eng

    # Keep connections warm. Measured against Supabase ap-southeast-1:
    # establishing a connection (TCP + TLS + auth) costs ~1220ms, while a
    # query on an already-open one costs ~64ms. NullPool discards the socket
    # after every statement, so it paid that handshake on every rerun —
    # 2.5s to load 90 rows. A client-side pool is correct even in front of
    # PgBouncer: the pooler exists to multiplex many clients onto few
    # backends, not to make per-query reconnection free.
    #
    # Safe in PgBouncer transaction mode because SQLAlchemy+psycopg2 does not
    # use server-side prepared statements by default. Pool stays small so
    # several app instances cannot exhaust the tenant's client slots.
    is_pgbouncer = ":6543" in url or "pooler.supabase.com" in url
    return create_engine(
        url,
        poolclass=QueuePool,
        pool_size=3 if is_pgbouncer else 5,
        max_overflow=5 if is_pgbouncer else 10,
        pool_pre_ping=True,     # a dropped idle socket is retried, not raised
        pool_recycle=1800 if is_pgbouncer else 300,
        future=True,
    )


def backend() -> str:
    """'postgresql' or 'sqlite' — for display and for the health probe."""
    return get_engine().dialect.name


@st.cache_resource
def init_schema() -> bool:
    """Create tables/indexes if absent. Idempotent; runs once per process."""
    metadata.create_all(get_engine())
    return True


# ── normalisation helpers ─────────────────────────────────────────────────
def normalise_priority(value) -> str:
    v = str(value or "").strip()
    if v in PRIORITIES:
        return v
    return _PRIORITY_ALIASES.get(v.lower(), "Medium")


def normalise_status(value) -> str:
    v = str(value or "").strip()
    return v if v in STATUSES else "Open"


def parse_date(value) -> date:
    """classifier.py's date_filed is regex-scraped free text.

    Accepts date/datetime, ISO, and dd/mm/yyyy or dd-mm-yyyy (Indian civil
    order — 03/04/2026 is 3 April). Anything else falls back to today rather
    than rejecting a citizen's complaint over a malformed date.
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text or text.lower() == "unknown":
        return date.today()
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        pass
    m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})$", text)
    if m:
        d, mo, y = (int(g) for g in m.groups())
        y += 2000 if y < 100 else 0
        try:
            return date(y, mo, d)
        except ValueError:
            pass
    return date.today()


# ── reads ─────────────────────────────────────────────────────────────────
def _compute_days_open(df: pd.DataFrame) -> pd.DataFrame:
    """Days_Open is derived, never stored (see module docstring)."""
    if df.empty:
        df["Days_Open"] = pd.Series(dtype="int64")
        return df
    filed = pd.to_datetime(df["filed_on"])
    resolved = pd.to_datetime(df["resolved_on"])
    # Closed cases freeze at their resolution age; open ones keep accruing.
    end = resolved.fillna(pd.Timestamp(date.today()))
    df["Days_Open"] = (end - filed).dt.days.clip(lower=0).astype("int64")
    return df


# Short TTL so several operators converge quickly; every write calls
# load_grievances.clear() so the person who made a change sees it at once.
# The dashboard renders nine columns and some aggregates. It never shows the
# letter transcription, which can be kilobytes per row — selecting it here
# dominated load time (1.1s vs 0.2s at 100k rows) and memory for no benefit.
# Fetch the heavy text per-case with load_case_detail() instead.
# complainant_name/village are light String columns (unlike transcription),
# so pulling them in is cheap and powers the applicant search + register
# display. created_at surfaces the "date registered" (system entry), distinct
# from filed_on ("date on the letter").
_LIST_COLS = (
    grievances.c.id, grievances.c.case_no, grievances.c.filed_on,
    grievances.c.category, grievances.c.department, grievances.c.block,
    grievances.c.priority, grievances.c.status, grievances.c.source,
    grievances.c.is_demo, grievances.c.resolved_on,
    grievances.c.complainant_name, grievances.c.village, grievances.c.created_at,
)


@st.cache_data(ttl=30, show_spinner=False)
def load_grievances(include_demo: bool = True) -> pd.DataFrame:
    """The register, shaped exactly as app.py's existing DataFrame expects."""
    init_schema()
    stmt = select(*_LIST_COLS)
    if not include_demo:
        stmt = stmt.where(grievances.c.is_demo.is_(False))
    stmt = stmt.order_by(grievances.c.filed_on.desc(), grievances.c.id.desc())

    with get_engine().connect() as cx:
        df = pd.DataFrame(cx.execute(stmt).mappings().all())

    if df.empty:
        cols = ["ID", "Date", "Category", "Department", "Block", "Priority",
                "Status", "Days_Open", "Source", "db_id", "is_demo",
                "Applicant", "Village", "Registered"]
        return pd.DataFrame({c: pd.Series(dtype="object") for c in cols})

    df = _compute_days_open(df)
    # Legacy column names — app.py, the charts and the CSS all key off these.
    df = df.rename(columns={
        "case_no": "ID", "filed_on": "Date", "category": "Category",
        "department": "Department", "block": "Block", "priority": "Priority",
        "status": "Status", "source": "Source", "id": "db_id",
        "complainant_name": "Applicant", "village": "Village",
        "created_at": "Registered",
    })
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    # created_at is stored UTC; show the IST calendar date it was registered on.
    df["Registered"] = (pd.to_datetime(df["Registered"], utc=True)
                        .dt.tz_convert("Asia/Kolkata").dt.strftime("%Y-%m-%d"))
    df["Applicant"] = df["Applicant"].fillna("—")
    df["Village"] = df["Village"].fillna("—")
    return df


def get_status_history(grievance_db_id: int) -> pd.DataFrame:
    stmt = (select(status_history)
            .where(status_history.c.grievance_id == int(grievance_db_id))
            .order_by(status_history.c.changed_at.asc()))
    with get_engine().connect() as cx:
        return pd.DataFrame(cx.execute(stmt).mappings().all())


def load_case_detail(grievance_db_id: int) -> dict:
    """Full row including the heavy text columns, for one case on demand."""
    stmt = select(grievances).where(grievances.c.id == int(grievance_db_id))
    with get_engine().connect() as cx:
        row = cx.execute(stmt).mappings().first()
    return dict(row) if row else {}


def case_options(include_demo: bool = True, only_open: bool = True,
                 limit: int = 500) -> pd.DataFrame:
    """Recent open cases for the workflow picker.

    Bounded deliberately: this fills a dropdown, and at scale the open set is
    tens of thousands of rows that nobody scrolls. Newest first, capped.
    """
    init_schema()
    stmt = select(grievances.c.id, grievances.c.case_no, grievances.c.status,
                  grievances.c.block, grievances.c.category)
    if only_open:
        stmt = stmt.where(grievances.c.status.in_(OPEN_STATUSES))
    if not include_demo:
        stmt = stmt.where(grievances.c.is_demo.is_(False))
    stmt = stmt.order_by(grievances.c.id.desc()).limit(limit)
    with get_engine().connect() as cx:
        return pd.DataFrame(cx.execute(stmt).mappings().all())


def find_duplicates(complainant_name: str, category: str,
                    block: str | None = None, open_only: bool = True,
                    limit: int = 20) -> list[dict]:
    """Existing grievances that look like the same complaint from the same
    person — same applicant (case-insensitive) and same category (and block,
    when given). Read-only; the caller decides whether to warn or block.
    Returns a list of dicts (empty when nothing matches or name is blank)."""
    name = (complainant_name or "").strip()
    if not name or not category:
        return []
    init_schema()
    stmt = (select(grievances.c.case_no, grievances.c.filed_on,
                   grievances.c.category, grievances.c.block,
                   grievances.c.status, grievances.c.summary)
            .where(grievances.c.is_demo.is_(False))
            .where(grievances.c.complainant_name.ilike(name))
            .where(grievances.c.category == category))
    if block and block != "Unknown":
        stmt = stmt.where(grievances.c.block == block)
    if open_only:
        stmt = stmt.where(grievances.c.status.in_(OPEN_STATUSES))
    stmt = stmt.order_by(grievances.c.id.desc()).limit(limit)
    with get_engine().connect() as cx:
        return [dict(r) for r in cx.execute(stmt).mappings().all()]


# ── writes ────────────────────────────────────────────────────────────────
def insert_grievance(payload: dict, *, is_demo: bool = False) -> str:
    """Insert one grievance, returning its assigned case number.

    case_no is derived from the DB-assigned primary key within this same
    transaction, so concurrent writers can never mint the same number.
    """
    init_schema()
    row = {
        "filed_on": parse_date(payload.get("date_filed") or payload.get("Date")),
        "category": str(payload.get("category") or payload.get("Category") or "Unknown"),
        "department": str(payload.get("department") or payload.get("Department") or "Unknown"),
        "block": str(payload.get("block") or payload.get("Block") or "Unknown"),
        "priority": normalise_priority(payload.get("priority") or payload.get("Priority")),
        "status": normalise_status(payload.get("status") or payload.get("Status") or "Open"),
        "source": str(payload.get("source") or payload.get("Source") or "Manual"),
        "complainant_name": payload.get("complainant_name"),
        "village": payload.get("village"),
        "summary": payload.get("summary"),
        "transcription": payload.get("transcription"),
        "confidence": payload.get("confidence"),
        "is_demo": bool(is_demo),
        "resolved_on": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    if row["status"] == "Resolved":
        row["resolved_on"] = row["filed_on"]

    eng = get_engine()
    with eng.begin() as cx:
        new_id = cx.execute(insert(grievances).values(**row)).inserted_primary_key[0]
        case_no = f"NLD-{new_id:05d}"
        cx.execute(update(grievances)
                   .where(grievances.c.id == new_id)
                   .values(case_no=case_no))
        cx.execute(insert(status_history).values(
            grievance_id=new_id, from_status=None, to_status=row["status"],
            note="Case registered", changed_by=payload.get("changed_by", "operator"),
            changed_at=datetime.utcnow(),
        ))

    load_grievances.clear()
    return case_no


def update_status(grievance_db_id: int, to_status: str, *,
                  note: str = "", changed_by: str = "operator") -> bool:
    """Move a case and record the transition. Returns False if it's a no-op.

    The grievance row and its audit row are written in one transaction, so a
    status can never change without a corresponding history entry.
    """
    init_schema()
    to_status = normalise_status(to_status)
    eng = get_engine()
    with eng.begin() as cx:
        current = cx.execute(
            select(grievances.c.status)
            .where(grievances.c.id == int(grievance_db_id))
        ).scalar_one_or_none()

        if current is None or current == to_status:
            return False

        values = {"status": to_status, "updated_at": datetime.utcnow()}
        # Resolution date drives the frozen age of a closed case; clearing it
        # on re-open keeps Days_Open accruing again.
        values["resolved_on"] = date.today() if to_status == "Resolved" else None

        cx.execute(update(grievances)
                   .where(grievances.c.id == int(grievance_db_id))
                   .values(**values))
        cx.execute(insert(status_history).values(
            grievance_id=int(grievance_db_id), from_status=current,
            to_status=to_status, note=(note or None), changed_by=changed_by,
            changed_at=datetime.utcnow(),
        ))

    load_grievances.clear()
    return True


# ── demo seed ─────────────────────────────────────────────────────────────
@st.cache_resource
def seed_demo_data() -> int:
    """Write the 90 synthetic rows once, flagged is_demo=True.

    Same generator (and seed) the app used inline, so demos look identical —
    but the rows are now separable from real cases at query time.
    """
    import numpy as np
    from classifier import SCHEMA
    from real_data import BLOCK_CENSUS

    init_schema()
    eng = get_engine()
    with eng.connect() as cx:
        existing = cx.execute(
            select(func.count()).select_from(grievances)
            .where(grievances.c.is_demo.is_(True))
        ).scalar_one()
    if existing:
        return 0

    blocks = list(BLOCK_CENSUS.keys())
    cats = list(SCHEMA.keys())
    depts = [SCHEMA[c]["department"].split("(")[0].strip() for c in cats]
    n = 90
    rng = np.random.default_rng(42)
    ci = rng.integers(0, len(cats) - 1, n)
    bi = rng.integers(0, len(blocks), n)
    pris = rng.choice(PRIORITIES, n, p=[0.22, 0.48, 0.30])
    stats = rng.choice(STATUSES, n, p=[0.50, 0.25, 0.25])
    ages = rng.integers(1, 35, n)
    today = date.today()

    rows = []
    for i in range(n):
        filed = today - timedelta(days=int(ages[i]))
        resolved = filed + timedelta(days=int(rng.integers(1, max(2, int(ages[i]) + 1)))) \
            if stats[i] == "Resolved" else None
        rows.append({
            "case_no": None, "filed_on": filed, "category": cats[ci[i]],
            "department": depts[ci[i]], "block": blocks[bi[i]],
            "priority": str(pris[i]), "status": str(stats[i]), "source": "Demo",
            "is_demo": True, "resolved_on": resolved,
            "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),
        })

    with eng.begin() as cx:
        first = cx.execute(insert(grievances).values(rows[0])).inserted_primary_key[0]
        if len(rows) > 1:
            cx.execute(insert(grievances), rows[1:])
        # Backfill case numbers for the batch in one statement per dialect.
        for offset in range(len(rows)):
            gid = first + offset
            cx.execute(update(grievances)
                       .where(grievances.c.id == gid)
                       .values(case_no=f"NLD-{gid:05d}"))

    load_grievances.clear()
    return len(rows)
