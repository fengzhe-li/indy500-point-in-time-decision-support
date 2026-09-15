import datetime as dt
import json
import re
import zipfile

STAMP = re.compile(r"(\d{11})\.json$")

def parse_capture_events(path, year):
    events = []
    with zipfile.ZipFile(path) as archive:
        names = sorted(name for name in archive.namelist() if STAMP.search(name) and not name.endswith("i.json"))
        prior = None
        for name in names:
            try:
                payload = json.loads(archive.read(name))
            except Exception:
                continue
            qualifier = _find_qualifier(payload)
            if qualifier and qualifier != prior:
                stamp = int(STAMP.search(name).group(1))
                # Timing71 filenames encode Unix seconds with a leading zero.
                timestamp = dt.datetime.fromtimestamp(stamp, dt.timezone.utc).isoformat().replace("+00:00", "Z")
                events.append({"year": year, "car_number": qualifier, "capture_time_utc": timestamp,
                    "source_locator": name, "source_text": json.dumps({"currentQualifier": qualifier})})
            prior = qualifier
    # Full snapshots can expose the same run twice (RUN state and qualifier panel)
    # around its finish. Collapse only same-car onsets within three minutes; retain
    # the first recorder time and do not manufacture an event timestamp.
    collapsed=[]; last_by_car={}
    for event in events:
        stamp=dt.datetime.fromisoformat(event["capture_time_utc"].replace("Z","+00:00"))
        prior=last_by_car.get(event["car_number"])
        if prior is not None and (stamp-prior).total_seconds() <= 180:
            continue
        collapsed.append(event); last_by_car[event["car_number"]]=stamp
    return collapsed

def _find_qualifier(payload):
    if isinstance(payload, dict):
        session = payload.get("session")
        if isinstance(session, dict) and isinstance(session.get("trackData"), list) and session["trackData"]:
            match = re.match(r"#?(\w+)", str(session["trackData"][0]).strip())
            if match:
                return match.group(1)
        running = []
        for car in payload.get("cars", []):
            if isinstance(car, list) and len(car) > 1 and str(car[1]).upper() == "RUN":
                running.append(str(car[0]).strip())
        if len(running) == 1:
            return running[0]
    candidates = [payload]
    for key in ("session", "state", "data", "trackData", "raceState"):
        if isinstance(payload, dict) and isinstance(payload.get(key), dict):
            candidates.append(payload[key])
    def walk(value, depth=0):
        if depth > 5:
            return None
        if isinstance(value, dict):
            for key, item in value.items():
                if key.lower() in ("currentqualifier", "qualifier") and item not in (None, "", {}):
                    if isinstance(item, dict):
                        return str(item.get("carNumber") or item.get("number") or item.get("racingNumber") or "").strip() or None
                    return str(item).strip()
            for item in value.values():
                found = walk(item, depth + 1)
                if found: return found
        return None
    for candidate in candidates:
        found = walk(candidate)
        if found: return found
    return None
