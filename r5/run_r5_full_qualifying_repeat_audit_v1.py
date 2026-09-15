from pathlib import Path
import csv
from collections import Counter, defaultdict

ROOT = Path("/Users/fengzhecharlieli/Documents/ChatGPT/indy500删圈")

ATTEMPTS = ROOT / "r4/output/r4p1_attempt_four_lap_panel_v1.csv"
CONTEXT = ROOT / "weather/output/performance_context_features.csv"

def clean(v):
    return "" if v is None else str(v).strip()

def truthy(v):
    return clean(v).lower() in {"1","true","yes","y","t"}

def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return r.fieldnames or [], list(r)

_, attempts = read_csv(ATTEMPTS)
_, context = read_csv(CONTEXT)

ctx = {
    clean(r["attempt_id"]): r
    for r in context
}

def is_complete(a):
    return (
        clean(a.get("four_lap_average_speed_mph")) != ""
        and clean(a.get("lap1_speed_mph")) != ""
        and clean(a.get("lap2_speed_mph")) != ""
        and clean(a.get("lap3_speed_mph")) != ""
        and clean(a.get("lap4_speed_mph")) != ""
    )

print("=" * 150)
print("R5 FULL QUALIFYING REPEAT / PHYSICS COVERAGE AUDIT")
print("=" * 150)

print("\nSESSION INVENTORY")
print("-" * 150)

session_counts = defaultdict(lambda: Counter())

for a in attempts:
    key = (
        clean(a["year"]),
        clean(a["session_id"])
    )

    session_counts[key]["all"] += 1

    if is_complete(a):
        session_counts[key]["complete4"] += 1

    if truthy(a.get("environment_alignment_usable")):
        session_counts[key]["env_usable_flag"] += 1

    if truthy(a.get("ptsc_track_temp_available")):
        session_counts[key]["track_temp_flag"] += 1

    if clean(a["attempt_id"]) in ctx:
        session_counts[key]["context_join"] += 1


for (year, session), c in sorted(session_counts.items()):
    print(
        f"{year} | {session:35s} | "
        f"all={c['all']:3d} | "
        f"complete4={c['complete4']:3d} | "
        f"env_flag={c['env_usable_flag']:3d} | "
        f"track_flag={c['track_temp_flag']:3d} | "
        f"context_join={c['context_join']:3d}"
    )


print("\nSAME-CAR REPEAT TRANSITIONS — ALL QUALIFYING SESSIONS")
print("-" * 150)

groups = defaultdict(list)

for a in attempts:
    if not is_complete(a):
        continue

    key = (
        clean(a["year"]),
        clean(a["session_id"]),
        clean(a["entry_key"]),
    )

    groups[key].append(a)


repeat_counts = Counter()
repeat_rows = []

for (year, session, entry), rows in groups.items():

    rows = sorted(
        rows,
        key=lambda r: (
            int(clean(r["car_attempt_index"]))
            if clean(r["car_attempt_index"]).isdigit()
            else 999
        )
    )

    for before, after in zip(rows, rows[1:]):

        repeat_counts["all_complete_repeat_transitions"] += 1

        bctx = ctx.get(clean(before["attempt_id"]))
        actx = ctx.get(clean(after["attempt_id"]))

        both_context = bctx is not None and actx is not None

        if both_context:
            repeat_counts["both_context_joined"] += 1

        both_track = (
            truthy(before.get("ptsc_track_temp_available"))
            and truthy(after.get("ptsc_track_temp_available"))
        )

        if both_track:
            repeat_counts["both_track_temp_flag"] += 1

        both_env = (
            truthy(before.get("environment_alignment_usable"))
            and truthy(after.get("environment_alignment_usable"))
        )

        if both_env:
            repeat_counts["both_env_usable"] += 1

        repeat_rows.append({
            "year": year,
            "session_id": session,
            "entry_key": entry,
            "driver_name": clean(before["driver_name"]),
            "car_number": clean(before["car_number"]),
            "before_attempt_id": clean(before["attempt_id"]),
            "after_attempt_id": clean(after["attempt_id"]),
            "both_context_joined": both_context,
            "both_track_temp_flag": both_track,
            "both_env_usable": both_env,
        })


print(f"All complete same-car repeat transitions: {repeat_counts['all_complete_repeat_transitions']}")
print(f"Both attempts context-joined:             {repeat_counts['both_context_joined']}")
print(f"Both attempts track-temp flagged:         {repeat_counts['both_track_temp_flag']}")
print(f"Both attempts environment-usable:         {repeat_counts['both_env_usable']}")


print("\nREPEAT TRANSITIONS BY SESSION")
print("-" * 150)

by_session = Counter(
    (r["year"], r["session_id"])
    for r in repeat_rows
)

for (year, session), n in sorted(by_session.items()):
    print(
        f"{year} | {session:35s} | repeat transitions={n}"
    )


print("\nROWS THAT LOOK LIKE LAST CHANCE")
print("-" * 150)

lc = [
    a for a in attempts
    if any(
        token in clean(a["session_id"]).upper()
        for token in ["LAST", "CHANCE", "BUMP"]
    )
]

print(f"Last-Chance-like attempt rows: {len(lc)}")
print(f"Complete four-lap:             {sum(is_complete(a) for a in lc)}")

for a in lc:
    print(
        f"{a['year']} | "
        f"{a['session_id']} | "
        f"{a['driver_name']} | "
        f"idx={a['car_attempt_index']} | "
        f"speed={a['four_lap_average_speed_mph']} | "
        f"time={a['time_point_utc']} | "
        f"env={a['environment_alignment_usable']} | "
        f"track={a['ptsc_track_temp_available']}"
    )

print()
print("R5_FULL_QUALIFYING_REPEAT_AUDIT_COMPLETE")
