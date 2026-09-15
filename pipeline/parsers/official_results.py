import json
import re
from pypdf import PdfReader
from ..io_utils import total_seconds

CHASSIS = re.compile(r"^(\s*\d+\s+)(\S+)\s+(.+?)\s+(D/[CH]/F)\s+(.*?)\s+Day 1\s*(.*?)\s*$")

def parse_json(path, year):
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for index, record in enumerate(data.get("records", []), 1):
        laps = [_number(record.get(f"QualLap{i}")) for i in range(1, 5)]
        status = (record.get("Status") or "").strip()
        if status.lower() == "no attempt" and not any(laps):
            continue
        rows.append({
            "year": year, "rank": record.get("PositionFinish"),
            "car_number": str(record.get("CarNumber", "")).strip(),
            "driver_name": record.get("DriverName"), "team_name": record.get("TeamName"),
            "laps": laps, "total_seconds": total_seconds(record.get("ElapsedTime")),
            "average_speed_mph": _number(record.get("SpeedAvg")), "status_raw": status,
            "source_locator": f"records[{index}]", "source_text": json.dumps(record, sort_keys=True),
            "official_session_id": str(record.get("EventsSessionsID") or ""),
            "event_name": data.get("EventName"), "session_name": data.get("SessionName"),
            "event_date": data.get("SessionDate"),
        })
    return rows

def parse_pdf(path, year):
    rows = []
    for page_number, page in enumerate(PdfReader(str(path)).pages, 1):
        text = page.extract_text(extraction_mode="layout") or ""
        for line_number, line in enumerate(text.splitlines(), 1):
            if "Day 1" not in line or not line.lstrip()[:1].isdigit():
                continue
            match = CHASSIS.match(line)
            if not match:
                raise ValueError(f"Unparsed Results row {path.name}:{page_number}:{line_number}: {line}")
            rank = int(match.group(1).strip())
            car, driver, _, body, status = match.groups()[1:]
            values = body.split()
            if len(values) not in (5, 6):
                raise ValueError(f"Unexpected Results columns {path.name}:{page_number}:{line_number}: {values}")
            laps = [float(x) for x in values[:4]]
            total = total_seconds(values[4])
            speed = float(values[5]) if len(values) == 6 else None
            rows.append({
                "year": year, "rank": rank, "car_number": car, "driver_name": _driver(driver),
                "team_name": None, "laps": laps, "total_seconds": total,
                "average_speed_mph": speed, "status_raw": status.strip(),
                "source_locator": f"page={page_number};line={line_number};rank={rank}", "source_text": line.strip(),
                "official_session_id": None, "event_name": f"{year} Indianapolis 500",
                "session_name": "Qualifications - Day One", "event_date": None,
            })
    expected = 84 if year == 2023 else 74
    if len(rows) != expected:
        raise ValueError(f"Expected {expected} rows in {path.name}; parsed {len(rows)}")
    return rows

def _number(value):
    if value in (None, ""):
        return None
    return float(str(value).strip())

def _driver(value):
    if "," not in value:
        return value.strip()
    last, first = value.split(",", 1)
    return f"{first.strip()} {last.strip()}"

