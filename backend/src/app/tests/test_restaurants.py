from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Restaurant, RestaurantAspectSignal, Review
from app.services.restaurant_service import (
    get_restaurant,
    get_restaurant_reviews,
    list_restaurants,
)


def test_database_seed_creates_restaurants_reviews_and_aspects(db_session: Session) -> None:
    restaurant_count = db_session.scalar(select(func.count()).select_from(Restaurant))
    review_count = db_session.scalar(select(func.count()).select_from(Review))
    aspect_count = db_session.scalar(select(func.count()).select_from(RestaurantAspectSignal))

    assert restaurant_count == 60
    assert review_count == 4800
    assert aspect_count == 60


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
