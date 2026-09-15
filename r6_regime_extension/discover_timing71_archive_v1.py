from pathlib import Path
import json
import requests
import pandas as pd

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")

OUT = (
    ROOT /
    "r6_regime_extension/output/timing71_archive_v1"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

BASE = "https://archive.timing71.org"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0"
})

print("=" * 150)
print("PART 1 — OPENAPI DISCOVERY")
print("=" * 150)

openapi_url = BASE + "/openapi.json"

r = session.get(
    openapi_url,
    timeout=60
)

print(
    "HTTP",
    r.status_code
)

r.raise_for_status()

spec = r.json()

OPENAPI_OUT = (
    OUT /
    "timing71_archive_openapi_v1.json"
)

OPENAPI_OUT.write_text(
    json.dumps(
        spec,
        indent=2
    ),
    encoding="utf-8"
)

paths = spec.get(
    "paths",
    {}
)

path_rows = []

for path, methods in paths.items():

    for method, meta in methods.items():

        if method.lower() not in {
            "get",
            "post",
            "put",
            "delete",
            "patch"
        }:
            continue

        path_rows.append({
            "path": path,
            "method": method.upper(),
            "summary": meta.get(
                "summary"
            ),
            "operationId": meta.get(
                "operationId"
            ),
        })

path_df = pd.DataFrame(
    path_rows
)

print(
    path_df.to_string(
        index=False
    )
)

PATH_OUT = (
    OUT /
    "timing71_archive_api_paths_v1.csv"
)

path_df.to_csv(
    PATH_OUT,
    index=False
)

# ============================================================
# Try likely catalogue endpoints discovered from OpenAPI
# ============================================================

print("\n" + "=" * 150)
print("PART 2 — CATALOGUE ENDPOINT CANDIDATES")
print("=" * 150)

candidate_paths = []

for path in paths:

    low = path.lower()

    if any(
        token in low
        for token in [
            "recording",
            "replay",
            "archive",
            "event",
            "session",
            "manifest",
            "catalog",
            "search",
        ]
    ):
        candidate_paths.append(
            path
        )

for p in candidate_paths:
    print(p)

# ============================================================
# GET endpoints with no required path parameters
# ============================================================

print("\n" + "=" * 150)
print("PART 3 — ZERO-ARG GET PROBES")
print("=" * 150)

probe_rows = []
json_payloads = []

for path, methods in paths.items():

    get_meta = methods.get(
        "get"
    )

    if not get_meta:
        continue

    # skip paths requiring {something}
    if "{" in path:
        continue

    url = BASE + path

    try:

        rr = session.get(
            url,
            timeout=60
        )

        content_type = rr.headers.get(
            "content-type",
            ""
        )

        rec = {
            "path": path,
            "http_status": rr.status_code,
            "content_type": content_type,
            "bytes": len(
                rr.content
            ),
        }

        probe_rows.append(
            rec
        )

        print(
            path,
            "HTTP",
            rr.status_code,
            content_type,
            "bytes",
            len(rr.content)
        )

        if (
            rr.status_code == 200
            and "json" in content_type.lower()
        ):

            try:

                payload = rr.json()

                json_payloads.append({
                    "path": path,
                    "payload": payload,
                })

                safe_name = (
                    path.strip("/")
                    .replace("/", "__")
                    or "root"
                )

                (
                    OUT /
                    f"probe_{safe_name}.json"
                ).write_text(
                    json.dumps(
                        payload,
                        indent=2
                    ),
                    encoding="utf-8"
                )

            except Exception:
                pass

    except Exception as e:

        print(
            path,
            "ERROR",
            repr(e)
        )

probe_df = pd.DataFrame(
    probe_rows
)

PROBE_OUT = (
    OUT /
    "timing71_archive_zeroarg_probe_v1.csv"
)

probe_df.to_csv(
    PROBE_OUT,
    index=False
)

# ============================================================
# Search every successful JSON response for Indy / Indianapolis
# ============================================================

print("\n" + "=" * 150)
print("PART 4 — INDY STRING HITS")
print("=" * 150)

hits = []

def walk(obj, path="$"):

    if isinstance(
        obj,
        dict
    ):

        for k, v in obj.items():

            walk(
                v,
                f"{path}.{k}"
            )

    elif isinstance(
        obj,
        list
    ):

        for i, v in enumerate(
            obj
        ):

            walk(
                v,
                f"{path}[{i}]"
            )

    else:

        s = str(
            obj
        )

        low = s.lower()

        if any(
            term in low
            for term in [
                "indy",
                "indianapolis",
                "indycar",
                "500"
            ]
        ):

            hits.append({
                "json_path": path,
                "value": s[:1000],
            })

for item in json_payloads:

    before = len(
        hits
    )

    walk(
        item["payload"]
    )

    for h in hits[
        before:
    ]:
        h[
            "endpoint"
        ] = item[
            "path"
        ]

if not hits:

    print(
        "NO INDY HITS IN ZERO-ARG JSON RESPONSES"
    )

else:

    hit_df = pd.DataFrame(
        hits
    )

    print(
        hit_df[
            [
                "endpoint",
                "json_path",
                "value",
            ]
        ]
        .head(300)
        .to_string(
            index=False
        )
    )

    HIT_OUT = (
        OUT /
        "timing71_archive_indy_hits_v1.csv"
    )

    hit_df.to_csv(
        HIT_OUT,
        index=False
    )

print("\nOUTPUTS:")
print(
    OPENAPI_OUT.relative_to(
        ROOT
    )
)
print(
    PATH_OUT.relative_to(
        ROOT
    )
)
print(
    PROBE_OUT.relative_to(
        ROOT
    )
)

print(
    "\nR6_TIMING71_ARCHIVE_DISCOVERY_V1_COMPLETE"
)
