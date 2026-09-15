from pathlib import Path
import hashlib
import requests


URL = (
    "https://ptscin.com/"
    "wp-content/uploads/2025/06/"
    "FirestoneTemperatures.xlsx"
)

OUTPUT = Path(
    "weather/evidence/ptsc/"
    "FirestoneTemperatures_current.xlsx"
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


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def main():

    print(f"Downloading:")
    print(URL)

    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=40,
    )

    response.raise_for_status()

    data = response.content

    OUTPUT.write_bytes(data)

    print()
    print("========================")
    print("DONE")
    print("========================")
    print(f"Saved to: {OUTPUT}")
    print(f"Bytes: {len(data)}")
    print(f"SHA-256: {sha256_bytes(data)}")
    print(
        "Content-Type:",
        response.headers.get(
            "Content-Type",
            "",
        ),
    )


if __name__ == "__main__":
    main()