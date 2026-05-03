"""
Scrapes the YC company directory via their public Algolia search index.
Saves raw data to data/raw/yc_companies.json.
"""

import json
import time
import requests
from pathlib import Path
from tqdm import tqdm

ALGOLIA_APP_ID = "45BWZJ1SGC"
ALGOLIA_API_KEY = "NzllNTY5MzJiZGM2OTY2ZTQwMDEzOTNhYWZiZGRjODlhYzVkNjBmOGRjNzJiMWM4ZTU0ZDlhYTZjOTJiMjlhMWFuYWx5dGljc1RhZ3M9eWNkYyZyZXN0cmljdEluZGljZXM9WUNDb21wYW55X3Byb2R1Y3Rpb24lMkNZQ0NvbXBhbnlfQnlfTGF1bmNoX0RhdGVfcHJvZHVjdGlvbiZ0YWdGaWx0ZXJzPSU1QiUyMnljZGNfcHVibGljJTIyJTVE"
ALGOLIA_INDEX = "YCCompany_production"
ALGOLIA_URL = f"https://{ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/{ALGOLIA_INDEX}/query"

HEADERS = {
    "X-Algolia-Application-Id": ALGOLIA_APP_ID,
    "X-Algolia-API-Key": ALGOLIA_API_KEY,
    "Content-Type": "application/json",
}

def fetch_page(page: int, hits_per_page: int = 1000) -> dict:
    payload = {
        "hitsPerPage": hits_per_page,
        "page": page,
        "attributesToRetrieve": [
            "name", "slug", "one_liner", "long_description",
            "batch", "status", "industries", "subindustry",
            "regions", "country", "city", "team_size",
            "launched_at", "website", "tags", "top_company",
            "isHiring", "nonprofit", "question_answers",
        ],
        "filters": "",
    }
    resp = requests.post(ALGOLIA_URL, headers=HEADERS, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


YC_BATCHES = [
    f"Summer {y}" for y in range(2005, 2027)
] + [
    f"Winter {y}" for y in range(2006, 2027)
] + [
    f"Spring {y}" for y in range(2024, 2027)
] + [
    f"Fall {y}" for y in range(2024, 2027)
] + ["Unspecified"]


def fetch_by_filter(filters: str, page: int = 0, hits_per_page: int = 1000) -> dict:
    payload = {
        "hitsPerPage": hits_per_page,
        "page": page,
        "filters": filters,
        "attributesToRetrieve": [
            "name", "slug", "one_liner", "long_description",
            "batch", "status", "industries", "subindustry",
            "regions", "country", "city", "team_size",
            "launched_at", "website", "tags", "top_company",
            "isHiring", "nonprofit",
        ],
    }
    resp = requests.post(ALGOLIA_URL, headers=HEADERS, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def scrape_all() -> list[dict]:
    """Browse all companies by fetching one batch at a time to bypass 1000-hit Algolia cap."""
    all_companies: dict[str, dict] = {}

    # First get all without filter to understand total
    first = fetch_by_filter("")
    print(f"Total companies in index: {first['nbHits']}")

    # Fetch each batch separately
    for batch in tqdm(YC_BATCHES, desc="Fetching by batch"):
        data = fetch_by_filter(f'batch:"{batch}"')
        for c in data["hits"]:
            all_companies[c["objectID"]] = c
        time.sleep(0.05)

    # Also get remaining companies not captured by batch filter
    print(f"\nCaptured {len(all_companies)} via batch filters, fetching remaining...")
    # Fetch pages 0-5 of unfiltered to catch any strays
    for page in range(10):
        data = fetch_by_filter("", page=page)
        for c in data["hits"]:
            all_companies[c["objectID"]] = c
        if data["page"] >= data["nbPages"] - 1:
            break
        time.sleep(0.05)

    return list(all_companies.values())


if __name__ == "__main__":
    Path("data/raw").mkdir(parents=True, exist_ok=True)
    companies = scrape_all()
    out = Path("data/raw/yc_companies.json")
    out.write_text(json.dumps(companies, indent=2))
    print(f"\nSaved {len(companies)} companies to {out}")
