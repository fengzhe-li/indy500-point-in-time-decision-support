from pathlib import Path
import csv
import time
import random
import requests

OUTPUT = Path(
    "weather/evidence/ptsc_firestone_history_probe.csv"
)

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 "
        "Chrome/152 Safari/537.36"
    )
}

YEARS = [
    2020,
    2021,
    2022,
    2023,
    2024,
    2025,
]

# WordPress 文件可能在不同月份上传。
# Indy 500 通常在 5 月，所以优先 04/05/06，
# 但也顺手扫全年，避免历史文件上传月份不同。
MONTHS = list(range(1, 13))

FILENAMES = [
    "FirestoneTemperatures.xlsx",
    "FirestoneTemps.xlsx",
    "FirestoneTemperature.xlsx",
]


def probe(url):

    try:

        response = requests.head(
            url,
            headers=HEADERS,
            timeout=20,
            allow_redirects=True,
        )

        # 有些服务器不支持 HEAD，
        # 遇到 403/405 再用 GET + stream。
        if response.status_code in {
            403,
            405,
        }:

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=20,
                allow_redirects=True,
                stream=True,
            )

        return {
            "status_code": response.status_code,
            "content_type": response.headers.get(
                "Content-Type",
                "",
            ),
            "content_length": response.headers.get(
                "Content-Length",
                "",
            ),
            "final_url": response.url,
        }

    except requests.RequestException as exc:

        return {
            "status_code": "",
            "content_type": "",
            "content_length": "",
            "final_url": "",
            "error": str(exc),
        }


def main():

    rows = []

    total = (
        len(YEARS)
        * len(MONTHS)
        * len(FILENAMES)
    )

    counter = 0

    for year in YEARS:

        for month in MONTHS:

            for filename in FILENAMES:

                counter += 1

                url = (
                    f"https://ptscin.com/"
                    f"wp-content/uploads/"
                    f"{year}/"
                    f"{month:02d}/"
                    f"{filename}"
                )

                print(
                    f"[{counter}/{total}] "
                    f"{url}"
                )

                result = probe(
                    url
                )

                row = {
                    "year": year,
                    "month": month,
                    "filename": filename,
                    "url": url,
                    "status_code": result.get(
                        "status_code",
                        "",
                    ),
                    "content_type": result.get(
                        "content_type",
                        "",
                    ),
                    "content_length": result.get(
                        "content_length",
                        "",
                    ),
                    "final_url": result.get(
                        "final_url",
                        "",
                    ),
                    "error": result.get(
                        "error",
                        "",
                    ),
                }

                rows.append(
                    row
                )

                status = row[
                    "status_code"
                ]

                if status == 200:

                    print(
                        "    >>> FOUND <<<"
                    )

                elif status == 429:

                    print(
                        "    rate limited, "
                        "waiting 60 sec"
                    )

                    time.sleep(
                        60
                    )

                # 请求频率保持很低
                time.sleep(
                    2.0
                    + random.uniform(
                        0,
                        1.5,
                    )
                )

    fieldnames = [
        "year",
        "month",
        "filename",
        "url",
        "status_code",
        "content_type",
        "content_length",
        "final_url",
        "error",
    ]

    with OUTPUT.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(
            rows
        )

    found = [
        row
        for row in rows
        if row["status_code"] == 200
    ]

    print()
    print("========================")
    print("DONE")
    print("========================")
    print(
        f"Total URLs tested: "
        f"{len(rows)}"
    )
    print(
        f"200 FOUND: "
        f"{len(found)}"
    )
    print(
        f"Output: {OUTPUT}"
    )

    if found:

        print()
        print("FOUND URLS:")

        for row in found:

            print(
                row["url"]
            )


if __name__ == "__main__":
    main()