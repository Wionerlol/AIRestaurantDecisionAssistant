from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import Base
from app.db.models import Restaurant, RestaurantAspectSignal, Review
from app.db.session import get_engine


def init_database() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    if settings.database_auto_seed:
        with Session(engine) as session:
            seed_demo_data(session)


def seed_demo_data(session: Session) -> None:
    existing = session.scalar(select(Restaurant.business_id).limit(1))
    if existing is not None:
        return

    restaurants = []
    with settings.sample_businesses_file.open("r", encoding="utf-8") as handle:
        for line in handle:
            payload = json.loads(line)
            restaurants.append(
                Restaurant(
                    business_id=payload["business_id"],
                    name=payload["name"],
                    address=payload.get("address"),
                    city=payload["city"],
                    state=payload["state"],
                    postal_code=payload.get("postal_code"),
                    latitude=payload.get("latitude"),
                    longitude=payload.get("longitude"),
                    stars=payload.get("stars"),
                    review_count=payload.get("review_count", 0),
                    is_open=payload.get("is_open"),
                    categories=_split_categories(payload.get("categories")),
                )
            )

    session.add_all(restaurants)
    session.flush()

    aspects = [
        RestaurantAspectSignal(
            business_id=restaurant.business_id,
            overall_rating=restaurant.stars,
            pros=[],
            cons=[],
            risk_flags=[],
        )
        for restaurant in restaurants
    ]
    session.add_all(aspects)

    reviews = []
    with settings.sample_reviews_file.open("r", encoding="utf-8") as handle:
        for line in handle:
            payload = json.loads(line)
            reviews.append(
                Review(
                    review_id=payload["review_id"],
                    user_id=payload["user_id"],
                    business_id=payload["business_id"],
                    stars=payload["stars"],
                    useful=payload.get("useful", 0),
                    funny=payload.get("funny", 0),
                    cool=payload.get("cool", 0),
                    text=payload["text"],
                    review_date=datetime.strptime(payload["date"], "%Y-%m-%d %H:%M:%S"),
                )
            )

    session.add_all(reviews)
    session.commit()


def _split_categories(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]
