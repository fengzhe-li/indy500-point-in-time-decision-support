from pathlib import Path
import csv
import hashlib
import time
import requests
from urllib.parse import urlparse


INPUT_CSV = Path("weather/evidence/indy500_discovered_sources.csv")
DOWNLOAD_ROOT = Path("weather/evidence/downloads")
MANIFEST_CSV = Path("weather/evidence/download_manifest.csv")

DOWNLOAD_ROOT.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 Chrome/152 Safari/537.36"
    )
}


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def safe_filename(url, fallback_name):
    parsed = urlparse(url)

    name = Path(parsed.path).name

    if not name:
        name = fallback_name

    if not name.lower().endswith(".pdf"):
        name = f"{fallback_name}.pdf"

    return name


def download_pdf(year, anchor_text, url):
    year_dir = DOWNLOAD_ROOT / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)

    fallback = (
        anchor_text.lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("–", "-")
        .replace("—", "-")
    )

    filename = safe_filename(url, fallback)
    output_path = year_dir / filename

    print(f"[{year}] {anchor_text}")
    print(f"    {url}")

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30,
        )
        response.raise_for_status()

    except requests.RequestException as exc:
        print(f"    ERROR: {exc}")

        return {
            "year": year,
            "anchor_text": anchor_text,
            "url": url,
            "status": "FAILED",
            "http_status": getattr(
                getattr(exc, "response", None),
                "status_code",
                "",
            ),
            "local_path": "",
            "bytes": "",
            "sha256": "",
            "notes": str(exc),
        }

    content_type = response.headers.get(
        "Content-Type",
        "",
    ).lower()

    data = response.content

    # 有些站 Content-Type 不规范，所以也检查 PDF magic bytes
    looks_like_pdf = data.startswith(b"%PDF")

    if "pdf" not in content_type and not looks_like_pdf:
        print(
            f"    SKIP: response does not look like PDF "
            f"({content_type})"
        )

        return {
            "year": year,
            "anchor_text": anchor_text,
            "url": url,
            "status": "NOT_PDF",
            "http_status": response.status_code,
            "local_path": "",
            "bytes": len(data),
            "sha256": sha256_bytes(data),
            "notes": f"Content-Type={content_type}",
        }

    output_path.write_bytes(data)

    digest = sha256_bytes(data)

    print(
        f"    saved: {output_path} "
        f"({len(data)} bytes)"
    )

    return {
        "year": year,
        "anchor_text": anchor_text,
        "url": url,
        "status": "DOWNLOADED",
        "http_status": response.status_code,
        "local_path": str(output_path),
        "bytes": len(data),
        "sha256": digest,
        "notes": "",
    }


def main():
    rows_to_download = []

    with INPUT_CSV.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        reader = csv.DictReader(f)

        for row in reader:
            if row["source_type"] != "PDF":
                continue

            rows_to_download.append(row)

    print(
        f"PDF candidates: {len(rows_to_download)}"
    )

    results = []

    for i, row in enumerate(
        rows_to_download,
        start=1,
    ):
        year = row["year"]
        anchor_text = row["anchor_text"]
        url = row["url"]

        print(
            f"\n{i}/{len(rows_to_download)}"
        )

        result = download_pdf(
            year,
            anchor_text,
            url,
        )

        results.append(result)

        # 放慢一点，避免再触发限流
        time.sleep(2.5)

    fieldnames = [
        "year",
        "anchor_text",
        "url",
        "status",
        "http_status",
        "local_path",
        "bytes",
        "sha256",
        "notes",
    ]

    with MANIFEST_CSV.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(results)

    downloaded = sum(
        1
        for r in results
        if r["status"] == "DOWNLOADED"
    )

    failed = sum(
        1
        for r in results
        if r["status"] == "FAILED"
    )

    print("\n========================")
    print("DONE")
    print("========================")
    print(f"Downloaded: {downloaded}")
    print(f"Failed: {failed}")
    print(f"Manifest: {MANIFEST_CSV}")


if __name__ == "__main__":
    main()