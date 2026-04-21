from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.bootstrap import seed_demo_data
from app.db.models import Restaurant, RestaurantAspectSignal, Review, ReviewAspectSignal
from app.services.restaurant_service import (
    get_restaurant,
    get_restaurant_reviews,
    list_restaurants,
)


def test_database_seed_creates_restaurants_reviews_and_aspects(db_session: Session) -> None:
    restaurant_count = db_session.scalar(select(func.count()).select_from(Restaurant))
    review_count = db_session.scalar(select(func.count()).select_from(Review))
    aspect_count = db_session.scalar(select(func.count()).select_from(RestaurantAspectSignal))
    review_aspect_count = db_session.scalar(select(func.count()).select_from(ReviewAspectSignal))

    expected_restaurants = _count_jsonl_rows(settings.sample_businesses_file)
    expected_reviews = _count_jsonl_rows(settings.sample_reviews_file)

    assert restaurant_count == expected_restaurants
    assert review_count == expected_reviews
    assert aspect_count == expected_restaurants
    assert review_aspect_count == expected_reviews


def _count_jsonl_rows(path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def test_list_restaurants_returns_seeded_data(db_session: Session) -> None:
    restaurants = list_restaurants(db_session, limit=5)

    assert len(restaurants) == 5
    assert restaurants[0].business_id
    assert restaurants[0].review_count >= restaurants[-1].review_count


def test_can_fetch_restaurant_and_reviews(db_session: Session) -> None:
    restaurant = list_restaurants(db_session, limit=1)[0]

    detail = get_restaurant(db_session, restaurant.business_id)
    reviews = get_restaurant_reviews(db_session, restaurant.business_id, limit=3)

    assert detail is not None
    assert detail.business_id == restaurant.business_id
    assert len(reviews) == 3
    assert reviews[0].business_id == restaurant.business_id


def test_seeded_review_aspect_signal_links_review_and_restaurant(db_session: Session) -> None:
    review = db_session.scalars(select(Review).limit(1)).one()
    signal = db_session.get(ReviewAspectSignal, review.review_id)

    assert signal is not None
    assert signal.review_id == review.review_id
    assert signal.business_id == review.business_id
    assert signal.review.review_id == review.review_id
    assert signal.restaurant.business_id == review.business_id
    assert signal.overall_sentiment_score is None
    assert signal.aspect_sentiments == {}
    assert signal.pros == []
    assert signal.cons == []
    assert signal.risk_flags == []


def test_seed_backfills_missing_review_aspect_signals(db_session: Session) -> None:
    db_session.query(ReviewAspectSignal).delete()
    db_session.commit()

    seed_demo_data(db_session)

    review_count = db_session.scalar(select(func.count()).select_from(Review))
    review_aspect_count = db_session.scalar(select(func.count()).select_from(ReviewAspectSignal))

    assert review_aspect_count == review_count
