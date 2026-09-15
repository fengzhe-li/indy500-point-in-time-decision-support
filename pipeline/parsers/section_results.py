import re
import pdfplumber

CAR = re.compile(r"Section Data for Car\s+(\S+)\s+-\s+(.+)")
NUM = re.compile(r"\d+\.\d+")

def parse(path, year):
    observations = {}
    with pdfplumber.open(str(path)) as pdf:
        for page_number, page in enumerate(pdf.pages, 1):
            text = page.extract_text(layout=True) or ""
            car_match = CAR.search(text)
            if not car_match:
                continue
            car = car_match.group(1).strip()
            driver = car_match.group(2).strip()
            # The 2024 report is a fixed two-page layout per car. PDF text extraction
            # sometimes drops the "PI to PO" header, so page parity is the stable locator.
            part_b = year == 2024 and page_number % 2 == 0
            for lap_index, times, speeds, raw in _rows(text):
                key = (car, lap_index)
                row = observations.setdefault(key, {"year": year, "car_number": car, "driver_name": driver,
                    "source_report_lap_index": lap_index, "section_times": [], "section_speeds": [],
                    "official_lap_time": None, "pages": [], "raw_rows": []})
                row["pages"].append(page_number); row["raw_rows"].append(raw)
                if year <= 2023:
                    if len(times) >= 10:
                        row["section_times"] = times[:9]
                        row["official_lap_time"] = times[9]
                        row["section_speeds"] = speeds[:9]
                    elif lap_index % 5 != 0:
                        row["section_times"] = times[:9]
                        row["section_speeds"] = speeds[:len(row["section_times"])]
                elif part_b:
                    if lap_index <= 4 and len(times) >= 3:
                        row["section_times"].extend(times[:2])
                        row["section_speeds"].extend(speeds[:2])
                        row["official_lap_time"] = times[2]
                else:
                    row["section_times"] = times[:15]
                    row["section_speeds"] = speeds[:15]
    return list(observations.values())

def _rows(text):
    lines = text.splitlines()
    pending = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        match = re.match(r"^(\d+)\s+T\s+(.*)$", stripped)
        if match:
            lap = int(match.group(1)); payload = match.group(2)
        elif stripped.startswith("T "):
            payload = stripped[2:]
            lap = None
            for later in lines[i + 1:i + 3]:
                if later.strip().isdigit():
                    lap = int(later.strip()); break
            if lap is None:
                continue
        else:
            continue
        times = [float(x) for x in NUM.findall(payload)]
        speeds = []
        for later in lines[i + 1:i + 4]:
            s = later.strip()
            if re.match(r"^(?:\d+\s+)?S\s+", s):
                speeds = [float(x) for x in NUM.findall(s.split("S", 1)[1])]
                break
        pending = (lap, times, speeds, stripped)
        yield pending

def attempt_block(year, source_index):
    if year <= 2023:
        return ((source_index - 1) // 5 + 1, (source_index - 1) % 5 + 1)
    return (1, source_index if 1 <= source_index <= 4 else None)
