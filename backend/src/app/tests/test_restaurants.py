from app.api.routes_restaurants import (
    get_restaurant_detail,
    list_restaurant_reviews,
    list_restaurants,
)


def test_list_restaurants_returns_demo_subset() -> None:
    payload = list_restaurants(limit=5)

    assert payload.total == 5
    assert len(payload.items) == 5
    assert payload.items[0].business_id


def test_can_fetch_restaurant_and_reviews() -> None:
    search_payload = list_restaurants(limit=1)
    business_id = search_payload.items[0].business_id

    detail_payload = get_restaurant_detail(business_id)
    reviews_payload = list_restaurant_reviews(business_id, limit=3)

    assert detail_payload.business_id == business_id
    assert reviews_payload.business_id == business_id
    assert reviews_payload.total >= 1
    assert len(reviews_payload.items) >= 1
    assert reviews_payload.items[0].business_id == business_id
