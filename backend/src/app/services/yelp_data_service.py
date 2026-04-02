from __future__ import annotations

import json
from functools import lru_cache

from fastapi import HTTPException

from app.core.config import settings


def _split_categories(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@lru_cache(maxsize=1)
def _load_businesses() -> dict[str, dict]:
    businesses: dict[str, dict] = {}

    with settings.sample_businesses_file.open("r", encoding="utf-8") as handle:
        for line in handle:
            payload = json.loads(line)
            payload["categories"] = _split_categories(payload.get("categories"))
            businesses[payload["business_id"]] = payload

    return businesses


@lru_cache(maxsize=1)
def _load_reviews() -> dict[str, list[dict]]:
    reviews_by_business: dict[str, list[dict]] = {}

    with settings.sample_reviews_file.open("r", encoding="utf-8") as handle:
        for line in handle:
            payload = json.loads(line)
            reviews_by_business.setdefault(payload["business_id"], []).append(payload)

    for reviews in reviews_by_business.values():
        reviews.sort(key=lambda item: item["date"], reverse=True)

    return reviews_by_business


def search_restaurants(query: str | None = None, limit: int = 20) -> list[dict]:
    businesses = list(_load_businesses().values())

    if query:
        lowered = query.strip().lower()
        businesses = [
            business
            for business in businesses
            if lowered in business["name"].lower()
            or lowered in business["city"].lower()
            or any(lowered in category.lower() for category in business["categories"])
        ]

    businesses.sort(key=lambda item: (-item["review_count"], item["business_id"]))
    return businesses[:limit]


def get_restaurant(business_id: str) -> dict:
    business = _load_businesses().get(business_id)
    if business is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return business


def get_restaurant_reviews(business_id: str, limit: int = 20) -> list[dict]:
    _ = get_restaurant(business_id)
    reviews = _load_reviews().get(business_id, [])
    return reviews[:limit]
