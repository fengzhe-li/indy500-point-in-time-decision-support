from .config import EVIDENCE, RUN_RECORDED_AT
from .io_utils import sha256_file

QUALITY_RANK = {"OFFICIAL_RAW": 1, "OFFICIAL_REPORT": 2, "OFFICIAL_EDITORIAL": 3, "THIRD_PARTY_CAPTURE": 4, "REPUTABLE_EDITORIAL": 4, "SECONDARY_COMPILATION": 5}

def register_file(filename, source_type, quality, coverage_note=""):
    path = EVIDENCE / filename
    return {
        "source_id": filename.replace(".", "_").replace("-", "_"),
        "source_name": filename,
        "source_type": source_type,
        "evidence_quality": quality,
        "source_priority_rank": QUALITY_RANK[quality],
        "source_uri": str(path),
        "content_hash": sha256_file(path),
        "retrieved_at_utc": RUN_RECORDED_AT,
        "coverage_note": coverage_note,
    }
