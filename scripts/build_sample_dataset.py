#!/usr/bin/env python3
"""Build a deterministic demo subset from the Yelp academic dataset."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "yelp_dataset"
OUTPUT_DIR = ROOT / "backend" / "data" / "samples"

BUSINESS_SOURCE = SOURCE_DIR / "yelp_academic_dataset_business.json"
REVIEW_SOURCE = SOURCE_DIR / "yelp_academic_dataset_review.json"

BUSINESS_OUTPUT = OUTPUT_DIR / "demo_businesses.jsonl"
REVIEW_OUTPUT = OUTPUT_DIR / "demo_reviews.jsonl"
METADATA_OUTPUT = OUTPUT_DIR / "demo_metadata.json"

TARGET_CITIES = [
    ("Philadelphia", "PA"),
    ("Tampa", "FL"),
    ("Indianapolis", "IN"),
    ("Nashville", "TN"),
    ("Tucson", "AZ"),
    ("New Orleans", "LA"),
]
BUSINESSES_PER_CITY = 10
MAX_REVIEWS_PER_BUSINESS = 80
MIN_REVIEW_COUNT = 50


@dataclass(frozen=True)
class BusinessRecord:
    business_id: str
    name: str
    city: str
    state: str
    review_count: int
    stars: float | None
    payload: dict


def parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def load_candidate_businesses() -> list[BusinessRecord]:
    per_city: dict[tuple[str, str], list[BusinessRecord]] = defaultdict(list)

    with BUSINESS_SOURCE.open("r", encoding="utf-8") as handle:
        for line in handle:
            payload = json.loads(line)
            categories = set((payload.get("categories") or "").split(", "))
            city = (payload.get("city") or "").strip()
            state = (payload.get("state") or "").strip()

            if "Restaurants" not in categories:
                continue
            if (city, state) not in TARGET_CITIES:
                continue
            if payload.get("review_count", 0) < MIN_REVIEW_COUNT:
                continue

            per_city[(city, state)].append(
                BusinessRecord(
                    business_id=payload["business_id"],
                    name=payload["name"],
                    city=city,
                    state=state,
                    review_count=payload["review_count"],
                    stars=payload.get("stars"),
                    payload=payload,
                )
            )

    selected: list[BusinessRecord] = []
    for city_state in TARGET_CITIES:
        city_records = sorted(
            per_city[city_state],
            key=lambda item: (-item.review_count, item.business_id),
        )[:BUSINESSES_PER_CITY]
        selected.extend(city_records)

    return selected


def load_reviews_for_businesses(business_ids: set[str]) -> dict[str, list[dict]]:
    reviews_by_business: dict[str, list[dict]] = defaultdict(list)

    with REVIEW_SOURCE.open("r", encoding="utf-8") as handle:
        for line in handle:
            payload = json.loads(line)
            business_id = payload["business_id"]
            if business_id not in business_ids:
                continue
            reviews_by_business[business_id].append(payload)

    for business_id, reviews in reviews_by_business.items():
        reviews.sort(key=lambda item: parse_timestamp(item["date"]), reverse=True)
        reviews_by_business[business_id] = reviews[:MAX_REVIEWS_PER_BUSINESS]

    return reviews_by_business


def write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    selected_businesses = load_candidate_businesses()
    selected_ids = {record.business_id for record in selected_businesses}
    reviews_by_business = load_reviews_for_businesses(selected_ids)

    business_payloads = [record.payload for record in selected_businesses]
    review_payloads: list[dict] = []
    for business in selected_businesses:
        review_payloads.extend(reviews_by_business.get(business.business_id, []))

    metadata = {
        "selection_strategy": {
            "target_cities": TARGET_CITIES,
            "businesses_per_city": BUSINESSES_PER_CITY,
            "min_review_count": MIN_REVIEW_COUNT,
            "max_reviews_per_business": MAX_REVIEWS_PER_BUSINESS,
        },
        "dataset_summary": {
            "business_count": len(business_payloads),
            "review_count": len(review_payloads),
        },
        "seed_examples": [
            {
                "business_id": business.business_id,
                "name": business.name,
                "city": business.city,
                "state": business.state,
            }
            for business in selected_businesses[:5]
        ],
    }

    write_jsonl(BUSINESS_OUTPUT, business_payloads)
    write_jsonl(REVIEW_OUTPUT, review_payloads)
    with METADATA_OUTPUT.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    print(json.dumps(metadata, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
