from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import json
import time


# ============================================================
# PHASE
# ============================================================

PHASE = "R1E.3"

BASE_URL = "https://www.indycar.com"

ENDPOINT = (
    BASE_URL
    + "/api/results/EventsByYearSeries"
)

SERIES_ID = (
    "b856a4f1-e85c-4fac-8c36-fd58d962227a"
)

YEARS = [
    2020,
    2021,
    2022,
    2023,
    2024,
]


# ============================================================
# OUTPUT
# ============================================================

RAW_DIR = Path(
    "weather/evidence/rescue/"
    "official_indy500_correct_series"
)

RAW_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# NETWORK
# ============================================================

USER_AGENT = (
    "Mozilla/5.0 "
    "(compatible; Indy500HistoricalEvidenceResearch/1.0)"
)

TIMEOUT = 30
DELAY = 0.8


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

            "body":
                b"",

            "error":
                f"{type(exc).__name__}: {exc}",
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


def normalize_events(data):

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
            "Events",
            "events",
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


def session_summary(value):

    if value is None:
        return "NULL"

    if isinstance(
        value,
        list,
    ):
        return (
            f"LIST({len(value)})"
        )

    return (
        f"{type(value).__name__}: "
        f"{repr(value)[:500]}"
    )


def looks_like_indy500(name):

    lower = (
        str(name)
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


def main():

    print()
    print("=" * 110)
    print(
        "R1E.3 — CORRECT NTT INDYCAR "
        "EVENTS-BY-YEAR AUDIT V1"
    )
    print("=" * 110)

    print()
    print(
        "SERIES ID:",
        SERIES_ID,
    )

    years_with_indy500 = []
    years_with_sessions = []

    for year in YEARS:

        query = urlencode(
            {
                "year":
                    year,

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
        print("=" * 110)
        print(
            f"YEAR {year}"
        )
        print("=" * 110)

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

            continue

        text = decode(
            result[
                "body"
            ]
        )

        raw_path = (
            RAW_DIR
            /
            f"{year}_events_by_year_series_correct.json"
        )

        raw_path.write_text(
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
                text[:2000],
            )

            continue

        events = normalize_events(
            data
        )

        if events is None:

            print(
                "COULD NOT IDENTIFY EVENT LIST."
            )

            print(
                "TOP-LEVEL TYPE:",
                type(
                    data
                ).__name__,
            )

            print(
                "RAW PREVIEW:",
                repr(
                    data
                )[:3000],
            )

            continue

        print(
            "EVENT COUNT:",
            len(
                events
            ),
        )

        indy_matches = []

        any_sessions = False

        print()
        print(
            "EVENT INVENTORY"
        )
        print("-" * 110)

        for index, event in enumerate(
            events,
            start=1,
        ):

            if not isinstance(
                event,
                dict,
            ):

                print(
                    f"{index:02d} | "
                    f"NON-DICT | "
                    f"{repr(event)[:800]}"
                )

                continue

            event_id = (
                event.get(
                    "EventID"
                )
                or event.get(
                    "EventId"
                )
                or event.get(
                    "ID"
                )
                or event.get(
                    "Id"
                )
                or ""
            )

            event_name = (
                event.get(
                    "EventName"
                )
                or event.get(
                    "Name"
                )
                or ""
            )

            sessions = event.get(
                "Sessions"
            )

            if isinstance(
                sessions,
                list,
            ):

                if len(
                    sessions
                ) > 0:

                    any_sessions = True

            indy_flag = looks_like_indy500(
                event_name
            )

            if indy_flag:

                indy_matches.append(
                    event
                )

            print(
                f"{index:02d} | "
                f"EventID={event_id} | "
                f"Sessions={session_summary(sessions)} | "
                f"INDY500={indy_flag} | "
                f"{event_name}"
            )

            if (
                indy_flag
                and
                isinstance(
                    sessions,
                    list,
                )
                and
                sessions
            ):

                print(
                    "     SESSION PREVIEW:"
                )

                for s_index, session in enumerate(
                    sessions[:20],
                    start=1,
                ):

                    print(
                        f"       {s_index:02d} | "
                        f"{json.dumps(session, ensure_ascii=False)[:1200]}"
                    )

        print()
        print(
            "INDIANAPOLIS 500 MATCH COUNT:",
            len(
                indy_matches
            ),
        )

        if indy_matches:

            years_with_indy500.append(
                year
            )

            for match_index, match in enumerate(
                indy_matches,
                start=1,
            ):

                print()
                print(
                    f"INDY500 MATCH {match_index}:"
                )

                print(
                    json.dumps(
                        match,
                        indent=2,
                        ensure_ascii=False,
                    )[:8000]
                )

        if any_sessions:

            years_with_sessions.append(
                year
            )

        time.sleep(
            DELAY
        )

    print()
    print("=" * 110)
    print(
        "SUMMARY"
    )
    print("=" * 110)

    print()
    print(
        "Years with Indianapolis 500 match:",
        years_with_indy500,
    )

    print(
        "Years where EventsByYearSeries "
        "returned non-empty Sessions:",
        years_with_sessions,
    )

    print()
    print(
        "RAW OUTPUT DIRECTORY:"
    )

    print(
        RAW_DIR
    )

    print()
    print(
        "FINAL STATUS:"
    )

    if len(
        years_with_indy500
    ) == 5:

        print(
            "CORRECT_INDYCAR_EVENTS_CHAIN_CONFIRMED_5_OF_5"
        )

    elif len(
        years_with_indy500
    ) > 0:

        print(
            "CORRECT_INDYCAR_EVENTS_CHAIN_PARTIAL"
        )

    else:

        print(
            "CORRECT_INDYCAR_EVENTS_CHAIN_REVIEW_REQUIRED"
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
