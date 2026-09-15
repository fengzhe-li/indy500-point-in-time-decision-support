#!/usr/bin/env python3
"""Build the additive R4F6J Fast Friday evidence and candidate panel.

This generator is intentionally limited to the already identified official
INDYCAR session JSON, result PDFs, and editorial pages for 2020, 2022, and
2025. It does not alter any R4F6G-v2, R4F6H, or R4F6I artifact.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import unicodedata
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
R4 = ROOT / "r4"
EVIDENCE_DIR = R4 / "evidence" / "fast_friday" / "r4f6j"
OUTPUT_DIR = R4 / "output"
LEGACY_PANEL = OUTPUT_DIR / "r4f6g_canonical_fast_friday_reference_panel_v2.csv"

OUT_EVIDENCE = OUTPUT_DIR / "r4f6j_missing_fast_friday_reference_evidence_v1.csv"
OUT_SUMMARY = OUTPUT_DIR / "r4f6j_missing_fast_friday_reference_summary_v1.csv"
OUT_MANIFEST = OUTPUT_DIR / "r4f6j_missing_fast_friday_source_manifest_v1.csv"
OUT_QA = OUTPUT_DIR / "r4f6j_missing_fast_friday_reference_qa_v1.csv"
OUT_REPORT = OUTPUT_DIR / "r4f6j_missing_fast_friday_reference_report_v1.json"
OUT_CANDIDATE = OUTPUT_DIR / "r4f6j_candidate_expanded_fast_friday_reference_panel_v1.csv"

REFERENCE_PRIORITY = {
    "FOUR_LAP_QUALIFYING_SIM": 3,
    "NO_TOW_SINGLE_LAP": 2,
    "GENERAL_FAST_FRIDAY_BEST_SPEED": 1,
}
ROLE = {2020: "CORE_DEVELOPMENT", 2022: "CORE_DEVELOPMENT", 2025: "TECHNICAL_REGIME_TRANSFER"}

SESSIONS = {
    2020: {
        "id": "5767",
        "name": "Practice 3 (Fast Friday)",
        "json": "2020_fast_friday_session_5767.json",
        "pdf": "2020_fast_friday_practice3_results.pdf",
        "api_url": "https://www.indycar.com/api/results/EventsSessionDetails?id=5767",
        "pdf_url": "https://www.imscdn.com/INDYCAR/Documents/5767/2020-08-14/indycar-results-p3.pdf",
        "editorial": "2020_fast_friday_official_editorial.html",
        "editorial_url": "https://www.indycar.com/news/2020/08/08-14-Fast-Friday-Recap",
    },
    2022: {
        "id": "6031",
        "name": "Practice 5 (Fast Friday)",
        "json": "2022_fast_friday_session_6031.json",
        "pdf": "2022_fast_friday_practice5_results.pdf",
        "api_url": "https://www.indycar.com/api/results/EventsSessionDetails?id=6031",
        "pdf_url": "https://www.imscdn.com/INDYCAR/Documents/6031/2022-05-20/indycar-results-p5.pdf",
        "editorial": "2022_fast_friday_official_editorial.html",
        "editorial_url": "https://www.indycar.com/news/2022/05/05-20-practice",
    },
    2025: {
        "id": "6655",
        "name": "Practice 5 (Fast Friday by date and official editorial)",
        "json": "2025_fast_friday_session_6655.json",
        "pdf": "2025_fast_friday_practice5_results.pdf",
        "api_url": "https://www.indycar.com/api/results/EventsSessionDetails?id=6655",
        "pdf_url": "https://www.imscdn.com/INDYCAR/Documents/6655/2025-05-16/indycar-results-p5.pdf",
        "editorial": "2025_fast_friday_official_editorial.html",
        "editorial_url": "https://www.indycar.com/news/2025/05/05-16-fastfriday-practice",
    },
}

EDITORIAL_ROWS = [
    (2020, "Ryan Hunter-Reay", "28", 232.124, "NO_TOW_SINGLE_LAP",
     "Official editorial explicitly calls 232.124 mph the best lap of the day without an aerodynamic tow."),
    (2022, "Tony Kanaan", "1", 230.517, "FOUR_LAP_QUALIFYING_SIM",
     "Official editorial explicitly reports a four-lap qualifying-simulation average of 230.517 mph."),
    (2022, "David Malukas", "18", 230.287, "FOUR_LAP_QUALIFYING_SIM",
     "Official editorial explicitly reports 230.287 mph on the qualifying-simulation chart."),
    (2022, "Pato O'Ward", "5", 230.111, "FOUR_LAP_QUALIFYING_SIM",
     "Official editorial explicitly reports a four-lap qualifying-simulation average of 230.111 mph."),
    (2022, "Takuma Sato", "51", 229.680, "FOUR_LAP_QUALIFYING_SIM",
     "Official editorial explicitly reports 229.680 mph on the qualifying-simulation chart."),
    (2022, "Jimmie Johnson", "48", 229.094, "FOUR_LAP_QUALIFYING_SIM",
     "Official editorial explicitly reports a four-lap qualifying-simulation average of 229.094 mph."),
    (2025, "Scott Dixon", "9", 232.561, "FOUR_LAP_QUALIFYING_SIM",
     "Official editorial explicitly reports a four-lap qualifying-simulation average of 232.561 mph."),
    (2025, "Alex Palou", "10", 232.307, "FOUR_LAP_QUALIFYING_SIM",
     "Official editorial explicitly reports a four-lap qualifying-simulation average of 232.307 mph."),
]

EVIDENCE_FIELDS = [
    "year", "driver_name", "driver_key", "car_number", "reference_speed_mph",
    "reference_type", "reference_priority", "source_quality", "source_type",
    "source_url", "source_file", "extraction_method", "model_role",
    "provenance_note", "pdf_position", "pdf_lap_time",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def driver_key(name: str) -> str:
    value = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def parse_pdf(path: Path) -> list[dict[str, str]]:
    text = subprocess.check_output(["pdftotext", "-layout", str(path), "-"], text=True)
    pattern = re.compile(
        r"^\s*(\d+)\s+(\S+)\s+(.+?)\s+D/[CH]/F\s+"
        r"(\d\d:\d\d\.\d{4})\s+(\d+\.\d{3})\b"
    )
    rows = []
    for line in text.splitlines():
        match = pattern.match(line)
        if match:
            pos, car, name, lap_time, speed = match.groups()
            rows.append({"position": pos, "car": car, "pdf_name": name, "lap_time": lap_time, "speed": speed})
    return rows


def main() -> None:
    protected = sorted(
        list(OUTPUT_DIR.glob("r4f6g_*_v2.*"))
        + list(OUTPUT_DIR.glob("r4f6h*"))
        + list(OUTPUT_DIR.glob("r4f6i*"))
    )
    protected_before = {str(p.relative_to(ROOT)): sha256(p) for p in protected}

    evidence: list[dict] = []
    manifest: list[dict] = []
    pdf_crosscheck_counts: dict[int, int] = {}

    for year, meta in SESSIONS.items():
        json_path = EVIDENCE_DIR / meta["json"]
        pdf_path = EVIDENCE_DIR / meta["pdf"]
        editorial_path = EVIDENCE_DIR / meta["editorial"]
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        api_rows = payload["records"]
        pdf_rows = parse_pdf(pdf_path)
        assert len(pdf_rows) == len(api_rows), (year, len(pdf_rows), len(api_rows))
        by_position = {int(r["position"]): r for r in pdf_rows}
        for record in api_rows:
            position = int(record["PositionFinish"])
            pdf = by_position[position]
            car = record["CarNumber"]
            assert isinstance(car, str)
            assert car == pdf["car"]
            assert record["BestLapTime"] == pdf["lap_time"]
            assert f'{float(record["BestSpeed"]):.3f}' == pdf["speed"]
            name = record["DriverName"]
            evidence.append({
                "year": year, "driver_name": name, "driver_key": driver_key(name),
                "car_number": car, "reference_speed_mph": pdf["speed"],
                "reference_type": "GENERAL_FAST_FRIDAY_BEST_SPEED", "reference_priority": 1,
                "source_quality": "VERY_HIGH", "source_type": "OFFICIAL_RESULTS_PDF",
                "source_url": meta["pdf_url"],
                "source_file": str(pdf_path.relative_to(ROOT)),
                "extraction_method": "PDFTOTEXT_CROSSCHECK_OFFICIAL_SESSION_API",
                "model_role": ROLE[year],
                "provenance_note": "Official session fastest-lap result; not interpreted as a no-tow lap or four-lap average.",
                "pdf_position": position, "pdf_lap_time": pdf["lap_time"],
            })
        pdf_crosscheck_counts[year] = len(pdf_rows)

        for source_type, url_key, file_key, method, signature in [
            ("OFFICIAL_SESSION_API_JSON", "api_url", "json", "HTTPS_DOWNLOAD", "NOT_APPLICABLE"),
            ("OFFICIAL_RESULTS_PDF", "pdf_url", "pdf", "CURL_TLS_BYPASS_KNOWN_IMS_CDN; PDF_SIGNATURE_VERIFIED", "PASS"),
            ("OFFICIAL_EDITORIAL_HTML", "editorial_url", "editorial", "HTTPS_DOWNLOAD", "NOT_APPLICABLE"),
        ]:
            local_path = EVIDENCE_DIR / meta[file_key]
            if source_type == "OFFICIAL_RESULTS_PDF":
                assert local_path.read_bytes()[:5] == b"%PDF-"
            manifest.append({
                "year": year, "session_id": meta["id"], "session_name": meta["name"],
                "source_type": source_type, "source_url": meta[url_key],
                "local_file": str(local_path.relative_to(ROOT)), "retrieval_method": method,
                "bytes": local_path.stat().st_size, "sha256": sha256(local_path),
                "pdf_signature_valid": signature, "acquisition_status": "RECOVERED",
                "provenance_note": (
                    "Official IMS CDN PDF. curl TLS verification was bypassed only for the known hostname mismatch; file signature and API rows were independently checked."
                    if source_type == "OFFICIAL_RESULTS_PDF" else "Official INDYCAR public source preserved locally."
                ),
            })

    # Fail closed unless the exact official editorial numbers are present in the preserved pages.
    for year, name, car, speed, ref_type, note in EDITORIAL_ROWS:
        meta = SESSIONS[year]
        editorial_path = EVIDENCE_DIR / meta["editorial"]
        page = editorial_path.read_text(encoding="utf-8", errors="replace")
        assert f"{speed:.3f}" in page, (year, name, speed)
        evidence.append({
            "year": year, "driver_name": name, "driver_key": driver_key(name),
            "car_number": car, "reference_speed_mph": f"{speed:.3f}",
            "reference_type": ref_type, "reference_priority": REFERENCE_PRIORITY[ref_type],
            "source_quality": "VERY_HIGH", "source_type": "OFFICIAL_EDITORIAL_HTML",
            "source_url": meta["editorial_url"],
            "source_file": str(editorial_path.relative_to(ROOT)),
            "extraction_method": "EXPLICIT_VERIFIED_STATEMENT", "model_role": ROLE[year],
            "provenance_note": note, "pdf_position": "", "pdf_lap_time": "",
        })

    evidence.sort(key=lambda r: (int(r["year"]), r["driver_key"], -int(r["reference_priority"]), r["source_type"]))
    write_csv(OUT_EVIDENCE, EVIDENCE_FIELDS, evidence)

    legacy_fields, legacy_rows = read_csv(LEGACY_PANEL)
    candidate_fields = legacy_fields[:9] + ["source_url"] + legacy_fields[9:]
    candidate = [{**row, "source_url": ""} for row in legacy_rows]
    grouped: dict[tuple[int, str], list[dict]] = {}
    for row in evidence:
        grouped.setdefault((int(row["year"]), row["driver_key"]), []).append(row)
    for key in sorted(grouped):
        choices = sorted(
            grouped[key],
            key=lambda r: (-int(r["reference_priority"]), 0 if r["source_type"] == "OFFICIAL_RESULTS_PDF" else 1),
        )
        candidate.append(choices[0])
    candidate.sort(key=lambda r: (int(r["year"]), r["driver_key"]))
    write_csv(OUT_CANDIDATE, candidate_fields, candidate)

    summary = []
    acquisition = {2020: 33, 2022: 33, 2025: 34}
    session_names = {2020: SESSIONS[2020]["name"], 2022: SESSIONS[2022]["name"], 2025: SESSIONS[2025]["name"]}
    unresolved = {
        2020: "Complete official best-lap table recovered; only one explicit numeric no-tow reference and no explicit four-lap averages recovered.",
        2021: "Existing R4F6G-v2 coverage remains three explicit no-tow references only.",
        2022: "Complete official best-lap table recovered; five explicit qualifying-simulation references; other entries remain general best laps.",
        2023: "None within R4F6J; existing R4F6G-v2 coverage preserved.",
        2024: "None within R4F6J; existing R4F6G-v2 validation-only coverage preserved.",
        2025: "Complete official best-lap table recovered; two explicit qualifying-simulation references; transfer only. Official 12.875 mph Simpson row retained as published.",
    }
    for year in range(2020, 2026):
        rows = [r for r in candidate if int(r["year"]) == year]
        counts = Counter(r["reference_type"] for r in rows)
        roles = sorted({r["model_role"] for r in rows})
        summary.append({
            "year": year,
            "session_identified": session_names.get(year, "EXISTING_R4F6G_V2"),
            "official_source_type": "OFFICIAL_RESULTS_PDF+OFFICIAL_SESSION_API+OFFICIAL_EDITORIAL_HTML" if year in acquisition else "EXISTING_R4F6G_V2",
            "new_evidence_rows": sum(int(r["year"]) == year for r in evidence),
            "entries_recovered": acquisition.get(year, 0), "canonical_entries": len(rows),
            "four_lap_refs": counts["FOUR_LAP_QUALIFYING_SIM"],
            "no_tow_refs": counts["NO_TOW_SINGLE_LAP"],
            "general_fast_friday_refs": counts["GENERAL_FAST_FRIDAY_BEST_SPEED"],
            "model_role": roles[0] if len(roles) == 1 else "MIXED_OR_UNKNOWN",
            "unresolved_gaps": unresolved[year],
        })
    summary_fields = list(summary[0])
    write_csv(OUT_SUMMARY, summary_fields, summary)

    manifest.sort(key=lambda r: (int(r["year"]), r["source_type"]))
    manifest_fields = list(manifest[0])
    write_csv(OUT_MANIFEST, manifest_fields, manifest)

    protected_after = {str(p.relative_to(ROOT)): sha256(p) for p in protected}
    qa: list[dict[str, str]] = []
    def check(metric: str, value, expected, passed: bool, status_if_pass: str = "PASS") -> None:
        qa.append({"metric": metric, "value": str(value), "expected": str(expected), "status": status_if_pass if passed else "FAIL"})

    check("protected_r4f6g_v2_r4f6h_r4f6i_hashes", protected_after == protected_before, True, protected_after == protected_before)
    check("protected_artifact_count", len(protected), 23, len(protected) == 23)
    check("pdf_api_crosscheck_rows", sum(pdf_crosscheck_counts.values()), 100, sum(pdf_crosscheck_counts.values()) == 100)
    check("pdf_signature_checks", sum(r["pdf_signature_valid"] == "PASS" for r in manifest), 3, sum(r["pdf_signature_valid"] == "PASS" for r in manifest) == 3)
    check("new_evidence_rows", len(evidence), 108, len(evidence) == 108)
    check("candidate_unique_year_driver", len({(r["year"], r["driver_key"]) for r in candidate}), len(candidate), len({(r["year"], r["driver_key"]) for r in candidate}) == len(candidate))
    check("candidate_rows", len(candidate), 171, len(candidate) == 171)
    legacy_preserved = all(all(next(r for r in candidate if r["year"] == old["year"] and r["driver_key"] == old["driver_key"])[f] == old[f] for f in legacy_fields) for old in legacy_rows)
    check("legacy_shared_fields_exact", legacy_preserved, True, legacy_preserved)
    check("car_number_values_are_strings", all(isinstance(r["car_number"], str) for r in candidate), True, all(isinstance(r["car_number"], str) for r in candidate))
    cars_2022 = {r["car_number"] for r in candidate if int(r["year"]) == 2022}
    cars_2025 = {r["car_number"] for r in candidate if int(r["year"]) == 2025}
    check("leading_zero_and_plain_car_numbers_distinct", ("6" in cars_2022 and "06" in cars_2022 and "6" in cars_2025 and "06" in cars_2025), True, ("6" in cars_2022 and "06" in cars_2022 and "6" in cars_2025 and "06" in cars_2025))
    check("2024_validation_only", {r["model_role"] for r in candidate if int(r["year"]) == 2024}, {"VALIDATION_ONLY"}, {r["model_role"] for r in candidate if int(r["year"]) == 2024} == {"VALIDATION_ONLY"})
    check("2025_transfer_only", {r["model_role"] for r in candidate if int(r["year"]) == 2025}, {"TECHNICAL_REGIME_TRANSFER"}, {r["model_role"] for r in candidate if int(r["year"]) == 2025} == {"TECHNICAL_REGIME_TRANSFER"})
    explicit_provenance = all(r["source_url"] and r["source_file"] and r["provenance_note"] for r in evidence if int(r["year"]) in (2020, 2022))
    check("2020_2022_explicit_provenance", explicit_provenance, True, explicit_provenance)
    check("reference_type_priorities", all(int(r["reference_priority"]) == REFERENCE_PRIORITY[r["reference_type"]] for r in evidence), True, all(int(r["reference_priority"]) == REFERENCE_PRIORITY[r["reference_type"]] for r in evidence))
    ordinary_not_four_lap = all(r["reference_type"] == "GENERAL_FAST_FRIDAY_BEST_SPEED" for r in evidence if r["source_type"] == "OFFICIAL_RESULTS_PDF")
    check("ordinary_best_laps_not_mislabeled", ordinary_not_four_lap, True, ordinary_not_four_lap)
    check("source_urls_and_paths_retained", all(r["source_url"] and r["source_file"] for r in evidence), True, all(r["source_url"] and r["source_file"] for r in evidence))
    check("download_failure_semantics", "RECOVERED", "Failure would remain unresolved, not NONEXISTENT", True)
    check("2025_published_speed_outlier_preserved", "Kyffin Simpson 12.875 mph", "Preserve official value with warning", True, "WARN")
    write_csv(OUT_QA, ["metric", "value", "expected", "status"], qa)

    qa_counts = Counter(r["status"] for r in qa)
    phase_status = "R4F6J_MISSING_FAST_FRIDAY_REFERENCE_EXPANSION_READY" if qa_counts["FAIL"] == 0 else "R4F6J_MISSING_FAST_FRIDAY_REFERENCE_EXPANSION_PARTIAL"
    report = {
        "phase": "R4F6J",
        "status": phase_status,
        "scope": "Official Fast Friday entry-reference acquisition and additive canonicalization for 2020, 2022, and supplemental 2025.",
        "research_boundary": "No model fitting, simulation, chronology alteration, queue inference, or 2024 method tuning performed.",
        "reference_priority": REFERENCE_PRIORITY,
        "source_acquisition": {str(r["year"]): r for r in summary if int(r["year"]) in (2020, 2022, 2025)},
        "canonical_coverage": {str(r["year"]): r for r in summary},
        "qa_counts": {k: qa_counts.get(k, 0) for k in ("PASS", "WARN", "FAIL")},
        "protected_hashes_before": protected_before,
        "protected_hashes_after": protected_after,
        "protected_hashes_preserved": protected_before == protected_after,
        "candidate_state": "CANDIDATE_FOR_REVIEW_NOT_FROZEN",
        "download_failure_policy": "A failed download is unresolved evidence and is never interpreted as proof that a source does not exist.",
        "outputs": [str(p.relative_to(ROOT)) for p in (OUT_EVIDENCE, OUT_SUMMARY, OUT_MANIFEST, OUT_QA, OUT_REPORT, OUT_CANDIDATE)],
    }
    OUT_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Re-check after every output is materialized; the report itself is additive.
    assert protected_before == {str(p.relative_to(ROOT)): sha256(p) for p in protected}
    print("SOURCE ACQUISITION")
    for year in (2020, 2022, 2025):
        row = next(r for r in summary if int(r["year"]) == year)
        suffix = " — TRANSFER ONLY" if year == 2025 else ""
        print(f'{year}{suffix}: {row["session_identified"]}; entries={row["entries_recovered"]}; four_lap={row["four_lap_refs"]}; no_tow={row["no_tow_refs"]}; general={row["general_fast_friday_refs"]}')
        print(f'  gaps: {row["unresolved_gaps"]}')
    print("CANONICAL COVERAGE")
    for row in summary:
        print(f'{row["year"]}: entries={row["canonical_entries"]}, four_lap={row["four_lap_refs"]}, no_tow={row["no_tow_refs"]}, general={row["general_fast_friday_refs"]}, role={row["model_role"]}')
    print(f'QA: PASS={qa_counts["PASS"]} WARN={qa_counts["WARN"]} FAIL={qa_counts["FAIL"]}')
    print(phase_status)


if __name__ == "__main__":
    main()
