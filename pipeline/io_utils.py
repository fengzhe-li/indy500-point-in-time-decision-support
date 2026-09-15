import csv
import hashlib
import json
import uuid
from pathlib import Path
from .config import NAMESPACE

NS = uuid.UUID(NAMESPACE)

def stable_id(kind, *parts):
    return str(uuid.uuid5(NS, kind + "|" + "|".join(str(p) for p in parts)))

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def lineage_hash(value):
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()

def write_csv(path, rows, fields):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _flat(row.get(key)) for key in fields})

def _flat(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list, tuple)):
        return canonical_json(value)
    return value

def total_seconds(text):
    if not text:
        return None
    minutes, seconds = text.strip().split(":")
    return round(int(minutes) * 60 + float(seconds), 4)

