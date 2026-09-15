from pathlib import Path
import requests
import pandas as pd
import json

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")
OUT = ROOT / "r6_regime_extension/evidence/official_api_v2"
OUT.mkdir(parents=True, exist_ok=True)

BASE = "https://www.indycar.com"

SERIES_ID = "b856a4f1-e85c-4fac-8c36-fd58d962227a"

TARGET_YEARS = [2018, 2019, 2025, 2026]

HEADERS = {
    "User-Agent":
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 Chrome/153 Safari/537.36",
    "Accept":
        "application/json, text/plain, */*",
}

session = requests.Session()
session.headers.update(HEADERS)

# ============================================================
# helpers
# ============================================================

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

    return r.json()


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


def is_indy500_event(event_name):
    s = str(event_name).lower()

    return (
        "indianapolis 500" in s
        or (
            "500" in s
            and "indianapolis" in s
        )
    )


# ============================================================
# fetch season dropdown
# ============================================================

print("=" * 150)
print("PART 1 — SEASON DROPDOWN FETCH")
print("=" * 150)

season_data = get_json(
    BASE + "/api/results/SeasonDropDown",
    params={
        "id": SERIES_ID
    }
)

dump_json(
    season_data,
    OUT / "season_dropdown_raw.json"
)

print(
    "SEASON ROWS =",
    len(season_data)
)

print(
    "YEARS AVAILABLE =",
    [
        x.get("Year")
        for x in season_data
        if isinstance(x, dict)
    ]
)

# ============================================================
# extract target Indy 500 sessions
# ============================================================

print("\n" + "=" * 150)
print("PART 2 — TARGET EVENT / SESSION DISCOVERY")
print("=" * 150)

session_rows = []

for year in TARGET_YEARS:

    season_row = next(
        (
            x for x in season_data
            if isinstance(x, dict)
            and str(x.get("Year")) == str(year)
        ),
        None
    )

    print("\nYEAR =", year)

    if season_row is None:
        print("NO SEASON ROW")
        continue

    events = season_row.get(
        "Events",
        []
    ) or []

    print(
        "EVENTS =",
        len(events)
    )

    indy_events = [
        e for e in events
        if is_indy500_event(
            e.get("EventName")
        )
    ]

    print(
        "INDY500 EVENT MATCHES =",
        len(indy_events)
    )

    for event in indy_events:

        print(
            "EVENT:",
            event.get("EventName")
        )

        sessions = event.get(
            "Sessions",
            []
        ) or []

        print(
            "SESSIONS =",
            len(sessions)
        )

        for s in sessions:

            print(
                "  ",
                s.get("EventsSessionID"),
                "|",
                s.get("SessionName")
            )

            row = {
                "year": year,
                "event_name":
                    event.get("EventName"),
                "event_id":
                    event.get("EventID"),
            }

            row.update(s)

            session_rows.append(
                row
            )

session_df = pd.DataFrame(
    session_rows
)

SESSION_OUT = (
    OUT /
    "regime_extension_indy500_sessions_v1.csv"
)

session_df.to_csv(
    SESSION_OUT,
    index=False
)

# ============================================================
# fetch all session details
# ============================================================

print("\n" + "=" * 150)
print("PART 3 — SESSION DETAIL FETCH")
print("=" * 150)

detail_rows = []
summary_rows = []

for _, srow in session_df.iterrows():

    year = int(
        srow["year"]
    )

    sid = srow.get(
        "EventsSessionID"
    )

    sname = srow.get(
        "SessionName"
    )

    if pd.isna(sid):
        continue

    print(
        "\nFETCH",
        year,
        sid,
        sname
    )

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
            "FAILED:",
            repr(e)
        )

        summary_rows.append({
            "year": year,
            "session_id": sid,
            "session_name_seed": sname,
            "status": "FETCH_ERROR",
            "error": repr(e),
        })

        continue

    dump_json(
        data,
        OUT /
        f"{year}_session_{sid}_raw.json"
    )

    if not isinstance(
        data,
        dict
    ):
        continue

    records = data.get(
        "records",
        []
    ) or []

    print(
        "SessionName =",
        data.get("SessionName")
    )

    print(
        "SessionType =",
        data.get("SessionType")
    )

    print(
        "TrackType =",
        data.get("TrackType")
    )

    print(
        "records =",
        len(records)
    )

    summary_rows.append({
        "year": year,
        "session_id": sid,
        "session_name_seed": sname,
        "session_name":
            data.get("SessionName"),
        "session_type":
            data.get("SessionType"),
        "track_type":
            data.get("TrackType"),
        "session_date":
            data.get("SessionDateFormatted"),
        "record_count":
            len(records),
        "status":
            "OK",
    })

    for r in records:

        row = {
            "year": year,
            "session_id": sid,
            "session_name":
                data.get("SessionName"),
            "session_type":
                data.get("SessionType"),
            "track_type":
                data.get("TrackType"),
            "session_date":
                data.get("SessionDateFormatted"),
            "event_name":
                data.get("EventName"),
        }

        row.update(r)

        detail_rows.append(
            row
        )

# ============================================================
# save all records
# ============================================================

details_df = pd.DataFrame(
    detail_rows
)

summary_df = pd.DataFrame(
    summary_rows
)

DETAILS_OUT = (
    OUT /
    "regime_extension_all_session_records_v1.csv"
)

SUMMARY_OUT = (
    OUT /
    "regime_extension_session_summary_v1.csv"
)

details_df.to_csv(
    DETAILS_OUT,
    index=False
)

summary_df.to_csv(
    SUMMARY_OUT,
    index=False
)

# ============================================================
# qualifying-only summary
# ============================================================

print("\n" + "=" * 150)
print("PART 4 — QUALIFYING SESSION INVENTORY")
print("=" * 150)

if not summary_df.empty:

    qsum = summary_df[
        summary_df["session_type"]
        .astype(str)
        .eq("Q")
    ].copy()

    print(
        qsum[
            [
                "year",
                "session_id",
                "session_name",
                "session_date",
                "record_count",
            ]
        ]
        .to_string(index=False)
    )

else:
    qsum = pd.DataFrame()

# ============================================================
# qualifying sample
# ============================================================

print("\n" + "=" * 150)
print("PART 5 — QUALIFYING RECORD SAMPLE")
print("=" * 150)

if not details_df.empty:

    qdf = details_df[
        details_df["session_type"]
        .astype(str)
        .eq("Q")
    ].copy()

else:
    qdf = pd.DataFrame()

if not qdf.empty:

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
        "SpeedAvgFormatted",
        "Status",
    ]

    wanted = [
        c for c in wanted
        if c in qdf.columns
    ]

    print(
        qdf[wanted]
        .head(100)
        .to_string(index=False)
    )

    print(
        "\nQUALIFYING RECORDS BY YEAR / SESSION:"
    )

    print(
        qdf.groupby(
            [
                "year",
                "session_name"
            ]
        )
        .size()
        .to_string()
    )

# ============================================================
# identify likely Day1 / Combined qualifying sessions
# ============================================================

print("\n" + "=" * 150)
print("PART 6 — CORE-RELEVANT SESSION CANDIDATES")
print("=" * 150)

if not qsum.empty:

    qsum["name_lower"] = (
        qsum["session_name"]
        .astype(str)
        .str.lower()
    )

    core_mask = (
        qsum["name_lower"]
        .str.contains(
            "day 1|day1|combined qualifying|qualifications - day 1|qualifying - day 1",
            regex=True,
            na=False
        )
    )

    core = qsum[
        core_mask
    ].copy()

    if core.empty:

        # fallback: show all Q sessions
        core = qsum.copy()

    print(
        core[
            [
                "year",
                "session_id",
                "session_name",
                "session_date",
                "record_count",
            ]
        ]
        .to_string(index=False)
    )

else:
    core = pd.DataFrame()

CORE_OUT = (
    OUT /
    "regime_extension_core_qualifying_session_candidates_v1.csv"
)

core.to_csv(
    CORE_OUT,
    index=False
)

# ============================================================
# final
# ============================================================

print("\nOUTPUTS:")
print(
    SESSION_OUT.relative_to(ROOT)
)
print(
    SUMMARY_OUT.relative_to(ROOT)
)
print(
    DETAILS_OUT.relative_to(ROOT)
)
print(
    CORE_OUT.relative_to(ROOT)
)

print(
    "\nR6_SEASON_DROPDOWN_SESSION_FETCH_V1_COMPLETE"
)
