#!/usr/bin/env python3
"""Build a deterministic restaurant/review subset from the Yelp academic dataset."""

from __future__ import annotations

import json
import random
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
TARGET_BUSINESS_COUNT = 500
MAX_REVIEWS_PER_BUSINESS = 500
MIN_REVIEW_COUNT = 500
RANDOM_SEED = 20260421

RATING_BUCKETS = [
    ("excellent", 4.5, 5.1, 0.25),
    ("strong", 4.0, 4.5, 0.35),
    ("mixed", 3.0, 4.0, 0.30),
    ("weak", 0.0, 3.0, 0.10),
]

REVIEW_SAMPLE_PLAN = {
    "latest": 200,
    "useful": 125,
    "low_star": 100,
    "random": 75,
}


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

    city_quotas = allocate_city_quotas(per_city)
    selected: list[BusinessRecord] = []
    for city_state in TARGET_CITIES:
        selected.extend(
            select_city_businesses(per_city[city_state], city_quotas[city_state])
        )

    return selected


def allocate_city_quotas(
    per_city: dict[tuple[str, str], list[BusinessRecord]],
) -> dict[tuple[str, str], int]:
    base_quota, remainder = divmod(TARGET_BUSINESS_COUNT, len(TARGET_CITIES))
    quotas = {
        city_state: min(len(per_city[city_state]), base_quota + (index < remainder))
        for index, city_state in enumerate(TARGET_CITIES)
    }

    while sum(quotas.values()) < TARGET_BUSINESS_COUNT:
        candidates = [
            city_state
            for city_state in TARGET_CITIES
            if quotas[city_state] < len(per_city[city_state])
        ]
        if not candidates:
            break
        city_state = max(
            candidates, key=lambda item: len(per_city[item]) - quotas[item]
        )
        quotas[city_state] += 1

    return quotas


def select_city_businesses(
    records: list[BusinessRecord], quota: int
) -> list[BusinessRecord]:
    selected: list[BusinessRecord] = []
    selected_ids: set[str] = set()

    for _, lower, upper, ratio in RATING_BUCKETS:
        bucket = [
            record
            for record in records
            if record.stars is not None and lower <= record.stars < upper
        ]
        bucket = sorted(bucket, key=lambda item: (-item.review_count, item.business_id))
        bucket_quota = round(quota * ratio)
        for record in bucket[:bucket_quota]:
            if record.business_id not in selected_ids and len(selected) < quota:
                selected.append(record)
                selected_ids.add(record.business_id)

    if len(selected) < quota:
        remaining = sorted(
            [record for record in records if record.business_id not in selected_ids],
            key=lambda item: (-item.review_count, item.business_id),
        )
        for record in remaining:
            if len(selected) >= quota:
                break
            selected.append(record)
            selected_ids.add(record.business_id)

    return selected[:quota]


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
        reviews_by_business[business_id] = sample_reviews(reviews, business_id)

    return reviews_by_business


def sample_reviews(reviews: list[dict], business_id: str) -> list[dict]:
    rng = random.Random(f"{RANDOM_SEED}:{business_id}")
    selected: list[dict] = []
    selected_ids: set[str] = set()

    def add_candidates(candidates: list[dict], limit: int) -> None:
        added_count = 0
        for review in candidates:
            if len(selected) >= MAX_REVIEWS_PER_BUSINESS:
                break
            if added_count >= limit:
                break
            review_id = review["review_id"]
            if review_id in selected_ids:
                continue
            selected.append(review)
            selected_ids.add(review_id)
            added_count += 1

    latest_reviews = sorted(
        reviews, key=lambda item: parse_timestamp(item["date"]), reverse=True
    )
    useful_reviews = sorted(
        reviews,
        key=lambda item: (
            -(item.get("useful", 0) * 3 + item.get("cool", 0) + item.get("funny", 0)),
            -item.get("stars", 0),
            item["review_id"],
        ),
    )
    low_star_reviews = sorted(
        [review for review in reviews if review.get("stars", 0) <= 2],
        key=lambda item: (
            item.get("stars", 0),
            -item.get("useful", 0),
            item["review_id"],
        ),
    )
    random_reviews = reviews[:]
    rng.shuffle(random_reviews)

    add_candidates(latest_reviews, REVIEW_SAMPLE_PLAN["latest"])
    add_candidates(useful_reviews, REVIEW_SAMPLE_PLAN["useful"])
    add_candidates(low_star_reviews, REVIEW_SAMPLE_PLAN["low_star"])
    add_candidates(random_reviews, REVIEW_SAMPLE_PLAN["random"])

    if len(selected) < MAX_REVIEWS_PER_BUSINESS:
        remaining = [
            review
            for review in latest_reviews
            if review["review_id"] not in selected_ids
        ]
        add_candidates(remaining, MAX_REVIEWS_PER_BUSINESS - len(selected))

    return sorted(
        selected, key=lambda item: parse_timestamp(item["date"]), reverse=True
    )


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
            "target_business_count": TARGET_BUSINESS_COUNT,
            "min_review_count": MIN_REVIEW_COUNT,
            "max_reviews_per_business": MAX_REVIEWS_PER_BUSINESS,
            "rating_buckets": [
                {
                    "name": name,
                    "min_stars": lower,
                    "max_stars": upper,
                    "target_ratio": ratio,
                }
                for name, lower, upper, ratio in RATING_BUCKETS
            ],
            "review_sample_plan": REVIEW_SAMPLE_PLAN,
            "random_seed": RANDOM_SEED,
        },
        "dataset_summary": {
            "business_count": len(business_payloads),
            "review_count": len(review_payloads),
            "min_reviews_per_business": min(
                (len(reviews) for reviews in reviews_by_business.values()),
                default=0,
            ),
            "max_reviews_per_business": max(
                (len(reviews) for reviews in reviews_by_business.values()),
                default=0,
            ),
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
