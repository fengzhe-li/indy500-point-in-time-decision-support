from pathlib import Path
import requests
import pandas as pd
import json

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r6_regime_extension/evidence/official_api"
OUT.mkdir(parents=True, exist_ok=True)

BASE = "https://www.indycar.com"

SERIES_ID = "b856a4f1-e85c-4fac-8c36-fd58d962227a"

TARGET_YEARS = [2018, 2019, 2025, 2026]

HEADERS = {
    "User-Agent":
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 Chrome/153 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}

session = requests.Session()
session.headers.update(HEADERS)

def get_json(url, params=None):
    r = session.get(
        url,
        params=params,
        timeout=30
    )

    print(
        "GET",
        r.url,
        "status=",
        r.status_code,
        "type=",
        r.headers.get("content-type")
    )

    r.raise_for_status()

    try:
        return r.json()
    except Exception:
        print("NON-JSON RESPONSE:")
        print(r.text[:2000])
        raise


def dump_json(obj, path):
    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            obj,
            f,
            indent=2,
            ensure_ascii=False
        )


def object_to_records(obj):

    if isinstance(obj, list):
        return obj

    if isinstance(obj, dict):

        # common API wrappers
        for key in [
            "records",
            "Records",
            "data",
            "Data",
            "results",
            "Results",
            "events",
            "Events",
            "items",
            "Items",
        ]:
            if key in obj and isinstance(
                obj[key],
                list
            ):
                return obj[key]

        # fallback:
        # collect first list-valued field
        for k, v in obj.items():
            if isinstance(v, list):
                return v

    return []


all_event_rows = []
all_session_rows = []
all_qual_rows = []

print("=" * 150)
print("PART 1 — EVENT DISCOVERY")
print("=" * 150)

for year in TARGET_YEARS:

    print("\n" + "-" * 120)
    print("YEAR", year)
    print("-" * 120)

    url = (
        BASE
        + "/api/results/EventsByYearSeries"
    )

    # Try likely parameter combinations.
    attempts = [
        {
            "year": year,
            "series": SERIES_ID,
        },
        {
            "year": year,
            "seriesID": SERIES_ID,
        },
        {
            "year": year,
            "id": SERIES_ID,
        },
        {
            "year": year,
        },
    ]

    data = None
    successful_params = None

    for params in attempts:

        try:
            candidate = get_json(
                url,
                params=params
            )

            records = object_to_records(
                candidate
            )

            if records:
                data = candidate
                successful_params = params
                break

        except Exception as e:
            print(
                "attempt failed:",
                params,
                repr(e)
            )

    if data is None:
        print(
            "NO EVENT DATA FOR",
            year
        )
        continue

    dump_json(
        data,
        OUT /
        f"{year}_events_raw.json"
    )

    records = object_to_records(
        data
    )

    print(
        "EVENT RECORDS =",
        len(records)
    )

    if records:

        print(
            "FIRST EVENT KEYS =",
            sorted(records[0].keys())
        )

    # --------------------------------------------------------
    # locate Indy 500 event
    # --------------------------------------------------------

    event_candidates = []

    for rec in records:

        text = " ".join(
            str(v)
            for v in rec.values()
            if v is not None
        ).lower()

        if (
            "indianapolis 500" in text
            or "indy 500" in text
            or "500" in text
            and "indianapolis" in text
        ):
            event_candidates.append(
                rec
            )

    print(
        "INDY 500 EVENT CANDIDATES =",
        len(event_candidates)
    )

    for rec in event_candidates:

        print(
            json.dumps(
                rec,
                ensure_ascii=False
            )[:3000]
        )

        row = {
            "year": year,
            "successful_params":
                json.dumps(
                    successful_params
                ),
        }

        row.update(rec)

        all_event_rows.append(
            row
        )

# ============================================================
# discover session IDs
# ============================================================

print("\n" + "=" * 150)
print("PART 2 — SESSION DISCOVERY")
print("=" * 150)

# Candidate IDs can appear under different field names.
ID_FIELDS = [
    "EventsSessionID",
    "EventSessionID",
    "SessionID",
    "SessionId",
    "ID",
    "Id",
    "id",
]

URL_FIELDS = [
    "Url",
    "URL",
    "EventUrl",
    "RaceUrl",
    "Slug",
    "EventSlug",
]

def first_value(rec, fields):
    for k in fields:
        if k in rec and rec[k]:
            return rec[k]
    return None


for event_row in all_event_rows:

    year = event_row["year"]

    print(
        "\nYEAR",
        year
    )

    print(
        "EVENT ROW KEYS:",
        sorted(event_row.keys())
    )

    # Some EventsByYearSeries responses may already contain sessions.
    embedded_sessions = None

    for k, v in event_row.items():
        if isinstance(v, list):
            embedded_sessions = v
            print(
                "EMBEDDED LIST FIELD:",
                k,
                "rows=",
                len(v)
            )
            break

    if embedded_sessions:

        for s in embedded_sessions:

            row = {
                "year": year,
                "discovery_source":
                    "embedded_event_response"
            }

            if isinstance(s, dict):
                row.update(s)

            all_session_rows.append(
                row
            )

# ============================================================
# fallback: inspect raw year event JSON recursively
# for session-like dicts
# ============================================================

def recurse_dicts(obj):

    found = []

    if isinstance(obj, dict):

        found.append(obj)

        for v in obj.values():
            found.extend(
                recurse_dicts(v)
            )

    elif isinstance(obj, list):

        for x in obj:
            found.extend(
                recurse_dicts(x)
            )

    return found


for year in TARGET_YEARS:

    p = OUT / f"{year}_events_raw.json"

    if not p.exists():
        continue

    with open(
        p,
        "r",
        encoding="utf-8"
    ) as f:
        obj = json.load(f)

    dicts = recurse_dicts(obj)

    for d in dicts:

        keys_lower = {
            str(k).lower()
            for k in d.keys()
        }

        values_text = " ".join(
            str(v)
            for v in d.values()
            if not isinstance(
                v,
                (dict, list)
            )
        ).lower()

        if (
            "session" in " ".join(keys_lower)
            or "qual" in values_text
            or "practice" in values_text
        ):

            row = {
                "year": year,
                "discovery_source":
                    "recursive_event_json"
            }

            row.update(d)

            all_session_rows.append(
                row
            )

# dedupe rows
if all_session_rows:

    session_df = pd.DataFrame(
        all_session_rows
    )

    session_df = (
        session_df
        .astype(str)
        .drop_duplicates()
    )

else:
    session_df = pd.DataFrame()

SESSION_CSV = (
    OUT /
    "regime_extension_session_candidates_v1.csv"
)

session_df.to_csv(
    SESSION_CSV,
    index=False
)

print(
    "SESSION CANDIDATE ROWS =",
    len(session_df)
)

if not session_df.empty:

    print(
        session_df.head(100)
        .to_string(index=False)
    )

# ============================================================
# extract any plausible session IDs
# ============================================================

print("\n" + "=" * 150)
print("PART 3 — SESSION DETAIL FETCH")
print("=" * 150)

candidate_ids = []

if not session_df.empty:

    for idx, row in session_df.iterrows():

        row_dict = row.to_dict()

        text = " ".join(
            str(v)
            for v in row_dict.values()
        ).lower()

        # Only prioritize qualifying-like rows.
        if (
            "qual" not in text
            and "combined" not in text
            and "day 1" not in text
            and "day1" not in text
        ):
            continue

        sid = first_value(
            row_dict,
            ID_FIELDS
        )

        if (
            sid
            and sid != "nan"
        ):
            candidate_ids.append(
                (
                    int(row_dict.get(
                        "year"
                    )),
                    str(sid),
                    text[:500]
                )
            )

candidate_ids = list(
    dict.fromkeys(
        candidate_ids
    )
)

print(
    "QUALIFYING SESSION IDS FOUND =",
    len(candidate_ids)
)

for item in candidate_ids:
    print(item)

for year, sid, context in candidate_ids:

    try:

        data = get_json(
            BASE
            + "/api/results/EventsSessionDetails",
            params={
                "id": sid
            }
        )

    except Exception as e:

        print(
            "SESSION FETCH FAILED:",
            year,
            sid,
            repr(e)
        )

        continue

    dump_json(
        data,
        OUT /
        f"{year}_session_{sid}_raw.json"
    )

    print(
        "\nSESSION:",
        year,
        sid
    )

    if isinstance(data, dict):

        print(
            "SessionName =",
            data.get(
                "SessionName"
            )
        )

        print(
            "SessionType =",
            data.get(
                "SessionType"
            )
        )

        print(
            "EventName =",
            data.get(
                "EventName"
            )
        )

        print(
            "TrackType =",
            data.get(
                "TrackType"
            )
        )

        records = data.get(
            "records",
            []
        )

    else:

        records = []

    print(
        "records =",
        len(records)
    )

    if records:

        print(
            "record keys =",
            sorted(
                records[0].keys()
            )
        )

        print(
            json.dumps(
                records[0],
                indent=2,
                ensure_ascii=False
            )[:5000]
        )

        for r in records:

            row = {
                "year": year,
                "session_id": sid,
                "session_name":
                    data.get(
                        "SessionName"
                    ),
                "session_type":
                    data.get(
                        "SessionType"
                    ),
                "event_name":
                    data.get(
                        "EventName"
                    ),
                "track_type":
                    data.get(
                        "TrackType"
                    ),
            }

            row.update(r)

            all_qual_rows.append(
                row
            )

# ============================================================
# outputs
# ============================================================

event_df = pd.DataFrame(
    all_event_rows
)

EVENT_CSV = (
    OUT /
    "regime_extension_event_candidates_v1.csv"
)

event_df.to_csv(
    EVENT_CSV,
    index=False
)

qual_df = pd.DataFrame(
    all_qual_rows
)

QUAL_CSV = (
    OUT /
    "regime_extension_official_qualifying_records_v1.csv"
)

qual_df.to_csv(
    QUAL_CSV,
    index=False
)

print("\n" + "=" * 150)
print("PART 4 — FINAL API SUMMARY")
print("=" * 150)

print(
    "event candidate rows =",
    len(event_df)
)

print(
    "session candidate rows =",
    len(session_df)
)

print(
    "qualifying record rows =",
    len(qual_df)
)

if not qual_df.empty:

    print("\nROWS BY YEAR / SESSION:")

    print(
        qual_df.groupby(
            [
                "year",
                "session_name"
            ]
        )
        .size()
        .to_string()
    )

    wanted = [
        "year",
        "session_name",
        "PositionFinish",
        "CarNumber",
        "DriverName",
        "QualLap1",
        "QualLap2",
        "QualLap3",
        "QualLap4",
        "ElapsedTime",
        "SpeedAvg",
    ]

    wanted = [
        c
        for c in wanted
        if c in qual_df.columns
    ]

    print(
        "\nQUALIFYING SAMPLE:"
    )

    print(
        qual_df[wanted]
        .head(50)
        .to_string(index=False)
    )

print("\nOUTPUTS:")
print(
    EVENT_CSV.relative_to(ROOT)
)
print(
    SESSION_CSV.relative_to(ROOT)
)
print(
    QUAL_CSV.relative_to(ROOT)
)

print(
    "\nR6_INDIYCAR_OFFICIAL_API_FETCH_V1_COMPLETE"
)
