from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import json
import time


# ============================================================
# PHASE
# ============================================================

PHASE = "R1E.4"

BASE_URL = "https://www.indycar.com"

ENDPOINT = (
    BASE_URL
    + "/api/results/SeasonDropDown"
)

SERIES_ID = (
    "b856a4f1-e85c-4fac-8c36-fd58d962227a"
)

TARGET_YEARS = [
    2020,
    2021,
    2022,
    2023,
    2024,
]


# ============================================================
# OUTPUT
# ============================================================

OUTPUT_DIR = Path(
    "weather/evidence/rescue/"
    "official_indy500_season_dropdown"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

RAW_OUTPUT = (
    OUTPUT_DIR
    / "season_dropdown_ntt_indycar.json"
)


# ============================================================
# NETWORK
# ============================================================

USER_AGENT = (
    "Mozilla/5.0 "
    "(compatible; Indy500HistoricalEvidenceResearch/1.0)"
)

TIMEOUT = 30


# ============================================================
# HELPERS
# ============================================================

def fetch(url):

    request = Request(
        url,
        headers={
            "User-Agent":
                USER_AGENT,

            "Accept":
                "application/json,*/*;q=0.8",
        },
    )

    try:

        with urlopen(
            request,
            timeout=TIMEOUT,
        ) as response:

            body = response.read()

            return {
                "ok":
                    True,

                "status":
                    getattr(
                        response,
                        "status",
                        200,
                    ),

                "content_type":
                    response.headers.get(
                        "Content-Type",
                        "",
                    ),

                "final_url":
                    response.geturl(),

                "body":
                    body,

                "error":
                    "",
            }

    except HTTPError as exc:

        return {
            "ok":
                False,

            "status":
                exc.code,

            "content_type":
                "",

            "final_url":
                url,

            "body":
                b"",

            "error":
                f"HTTPError: {exc}",
        }

    except URLError as exc:

        return {
            "ok":
                False,

            "status":
                None,

            "content_type":
                "",

            "final_url":
                url,

            "body":
                b"",

            "error":
                f"URLError: {exc}",
        }

    except Exception as exc:

        return {
            "ok":
                False,

            "status":
                None,

            "content_type":
                "",

            "final_url":
                url,

            "body":
                b"",

            "error":
                (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
        }


def decode(body):

    for encoding in [
        "utf-8",
        "utf-8-sig",
        "latin-1",
    ]:

        try:

            return body.decode(
                encoding
            )

        except Exception:
            pass

    return body.decode(
        "utf-8",
        errors="replace",
    )


def first_value(
    obj,
    keys,
):

    if not isinstance(
        obj,
        dict,
    ):

        return None

    for key in keys:

        if key in obj:

            value = obj[
                key
            ]

            if value is not None:

                return value

    return None


def normalize_year(value):

    try:

        return int(
            str(value).strip()
        )

    except Exception:

        return None


def looks_like_indy500(name):

    lower = (
        str(
            name or ""
        )
        .lower()
    )

    return (
        (
            "indianapolis"
            in lower
            and
            "500"
            in lower
        )
        or
        "indy 500"
        in lower
    )


def session_id(session):

    return first_value(
        session,
        [
            "EventsSessionID",
            "EventsSessionId",
            "eventsSessionID",
            "eventsSessionId",
            "SessionID",
            "SessionId",
            "sessionID",
            "sessionId",
            "ID",
            "Id",
            "id",
        ],
    )


def session_name(session):

    return first_value(
        session,
        [
            "SessionName",
            "sessionName",
            "Name",
            "name",
        ],
    )


def normalize_root(data):

    if isinstance(
        data,
        list,
    ):

        return data

    if isinstance(
        data,
        dict,
    ):

        for key in [
            "Seasons",
            "seasons",
            "Data",
            "data",
            "Results",
            "results",
        ]:

            value = data.get(
                key
            )

            if isinstance(
                value,
                list,
            ):

                return value

    return None


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 110)

    print(
        "R1E.4 — OFFICIAL SEASON DROPDOWN "
        "HIERARCHY AUDIT V1"
    )

    print("=" * 110)

    print()
    print(
        "SERIES ID:",
        SERIES_ID,
    )

    query = urlencode(
        {
            "id":
                SERIES_ID,
        }
    )

    url = (
        ENDPOINT
        + "?"
        + query
    )

    print()
    print(
        "REQUEST:",
        url,
    )

    result = fetch(
        url
    )

    print(
        "STATUS:",
        result[
            "status"
        ],
    )

    print(
        "CONTENT-TYPE:",
        result[
            "content_type"
        ],
    )

    if not result[
        "ok"
    ]:

        print(
            "ERROR:",
            result[
                "error"
            ],
        )

        print()
        print(
            "FINAL STATUS: "
            "SEASON_DROPDOWN_FETCH_FAILED"
        )

        return

    text = decode(
        result[
            "body"
        ]
    )

    RAW_OUTPUT.write_text(
        text,
        encoding="utf-8",
    )

    try:

        data = json.loads(
            text
        )

    except Exception as exc:

        print(
            "JSON PARSE ERROR:",
            exc,
        )

        print(
            "RAW PREVIEW:",
            text[:5000],
        )

        print()
        print(
            "FINAL STATUS: "
            "SEASON_DROPDOWN_JSON_REVIEW_REQUIRED"
        )

        return

    print()
    print(
        "TOP-LEVEL TYPE:",
        type(
            data
        ).__name__,
    )

    if isinstance(
        data,
        dict,
    ):

        print(
            "TOP-LEVEL KEYS:",
            list(
                data.keys()
            ),
        )

    seasons = normalize_root(
        data
    )

    if seasons is None:

        print()
        print(
            "COULD NOT IDENTIFY SEASON LIST."
        )

        print(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2,
            )[:10000]
        )

        print()
        print(
            "FINAL STATUS: "
            "SEASON_DROPDOWN_SCHEMA_REVIEW_REQUIRED"
        )

        return

    print(
        "SEASON ROW COUNT:",
        len(
            seasons
        ),
    )

    target_years_found = []
    indy500_years_found = []
    indy500_years_with_sessions = []
    day1_like_sessions = []

    # ========================================================
    # AUDIT TARGET YEARS
    # ========================================================

    for year in TARGET_YEARS:

        print()
        print("=" * 110)

        print(
            f"YEAR {year}"
        )

        print("=" * 110)

        matching_seasons = []

        for season in seasons:

            if not isinstance(
                season,
                dict,
            ):

                continue

            season_year = normalize_year(
                first_value(
                    season,
                    [
                        "Year",
                        "year",
                        "Season",
                        "season",
                    ],
                )
            )

            if (
                season_year
                == year
            ):

                matching_seasons.append(
                    season
                )

        print(
            "MATCHING YEAR ROWS:",
            len(
                matching_seasons
            ),
        )

        if not matching_seasons:

            continue

        target_years_found.append(
            year
        )

        for season_index, season in enumerate(
            matching_seasons,
            start=1,
        ):

            print()
            print(
                f"SEASON OBJECT {season_index}"
            )

            print(
                "KEYS:",
                list(
                    season.keys()
                ),
            )

            events = first_value(
                season,
                [
                    "Events",
                    "events",
                    "SeasonEvents",
                    "seasonEvents",
                ],
            )

            if not isinstance(
                events,
                list,
            ):

                print(
                    "EVENTS:",
                    repr(
                        events
                    )[:2000],
                )

                continue

            print(
                "EVENT COUNT:",
                len(
                    events
                ),
            )

            indy_matches = []

            for event_index, event in enumerate(
                events,
                start=1,
            ):

                if not isinstance(
                    event,
                    dict,
                ):

                    continue

                event_id = first_value(
                    event,
                    [
                        "EventID",
                        "EventId",
                        "eventID",
                        "eventId",
                        "ID",
                        "Id",
                        "id",
                    ],
                )

                event_name = first_value(
                    event,
                    [
                        "EventName",
                        "eventName",
                        "Name",
                        "name",
                    ],
                )

                sessions = first_value(
                    event,
                    [
                        "Sessions",
                        "sessions",
                        "EventSessions",
                        "eventSessions",
                    ],
                )

                if isinstance(
                    sessions,
                    list,
                ):

                    session_state = (
                        f"LIST({len(sessions)})"
                    )

                elif sessions is None:

                    session_state = (
                        "NULL"
                    )

                else:

                    session_state = (
                        type(
                            sessions
                        ).__name__
                    )

                indy_flag = (
                    looks_like_indy500(
                        event_name
                    )
                )

                if indy_flag:

                    indy_matches.append(
                        event
                    )

                print(
                    f"{event_index:02d} | "
                    f"EventID={event_id} | "
                    f"Sessions={session_state} | "
                    f"INDY500={indy_flag} | "
                    f"{event_name}"
                )

            print()
            print(
                "INDY500 MATCH COUNT:",
                len(
                    indy_matches
                ),
            )

            if not indy_matches:

                continue

            if (
                year
                not in indy500_years_found
            ):

                indy500_years_found.append(
                    year
                )

            for match_index, event in enumerate(
                indy_matches,
                start=1,
            ):

                print()
                print(
                    f"INDY500 MATCH "
                    f"{match_index}"
                )

                print(
                    json.dumps(
                        event,
                        ensure_ascii=False,
                        indent=2,
                    )[:12000]
                )

                sessions = first_value(
                    event,
                    [
                        "Sessions",
                        "sessions",
                        "EventSessions",
                        "eventSessions",
                    ],
                )

                if not isinstance(
                    sessions,
                    list,
                ):

                    print(
                        "SESSIONS NOT A LIST."
                    )

                    continue

                if sessions:

                    if (
                        year
                        not in
                        indy500_years_with_sessions
                    ):

                        indy500_years_with_sessions.append(
                            year
                        )

                print()
                print(
                    "SESSION INVENTORY"
                )

                print(
                    "-" * 110
                )

                for session_index, session in enumerate(
                    sessions,
                    start=1,
                ):

                    if not isinstance(
                        session,
                        dict,
                    ):

                        print(
                            f"{session_index:02d} | "
                            f"{repr(session)[:1000]}"
                        )

                        continue

                    sid = session_id(
                        session
                    )

                    sname = session_name(
                        session
                    )

                    lower_name = (
                        str(
                            sname or ""
                        )
                        .lower()
                    )

                    day1_like = (
                        "qual"
                        in lower_name
                        and
                        (
                            "day 1"
                            in lower_name
                            or
                            "day one"
                            in lower_name
                            or
                            "day-1"
                            in lower_name
                            or
                            "saturday"
                            in lower_name
                        )
                    )

                    if day1_like:

                        day1_like_sessions.append(
                            {
                                "year":
                                    year,

                                "session_id":
                                    sid,

                                "session_name":
                                    sname,
                            }
                        )

                    print(
                        f"{session_index:02d} | "
                        f"EventsSessionID={sid} | "
                        f"DAY1_LIKE={day1_like} | "
                        f"{sname}"
                    )

                    print(
                        "     KEYS:",
                        list(
                            session.keys()
                        ),
                    )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 110)

    print(
        "SUMMARY"
    )

    print("=" * 110)

    print()
    print(
        "Target years found:",
        target_years_found,
    )

    print(
        "Years with Indy 500:",
        indy500_years_found,
    )

    print(
        "Years with Indy 500 non-empty Sessions:",
        indy500_years_with_sessions,
    )

    print()
    print(
        "DAY-1-LIKE SESSION CANDIDATES"
    )

    print(
        "-" * 110
    )

    if not day1_like_sessions:

        print(
            "NONE"
        )

    else:

        for row in (
            day1_like_sessions
        ):

            print(
                f"{row['year']} | "
                f"{row['session_id']} | "
                f"{row['session_name']}"
            )

    print()
    print(
        "RAW OUTPUT:",
        RAW_OUTPUT,
    )

    print()

    if (
        len(
            indy500_years_with_sessions
        )
        == 5
    ):

        print(
            "FINAL STATUS: "
            "OFFICIAL_SEASON_SESSION_HIERARCHY_RECOVERED_5_OF_5"
        )

    elif (
        len(
            indy500_years_with_sessions
        )
        > 0
    ):

        print(
            "FINAL STATUS: "
            "OFFICIAL_SEASON_SESSION_HIERARCHY_PARTIAL"
        )

    else:

        print(
            "FINAL STATUS: "
            "OFFICIAL_SEASON_SESSION_HIERARCHY_REVIEW_REQUIRED"
        )

    print()
    print(
        "NO CANONICAL DATA WAS MODIFIED."
    )

    print(
        "NO QUEUE WAIT WAS INFERRED."
    )

    print(
        "NO LEADERBOARD STATE WAS INVENTED."
    )


if __name__ == "__main__":
    main()
