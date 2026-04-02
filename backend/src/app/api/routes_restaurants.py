from typing import Annotated

from fastapi import APIRouter, Query

from app.schemas.restaurants import (
    RestaurantDetail,
    RestaurantReviewsResponse,
    RestaurantSearchResponse,
    RestaurantSummary,
)
from app.services.yelp_data_service import (
    get_restaurant,
    get_restaurant_reviews,
    search_restaurants,
)


router = APIRouter(prefix="/restaurants", tags=["restaurants"])


@router.get("", response_model=RestaurantSearchResponse)
def list_restaurants(
    query: Annotated[str | None, Query(min_length=1)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> RestaurantSearchResponse:
    items = [RestaurantSummary.model_validate(item) for item in search_restaurants(query, limit)]
    return RestaurantSearchResponse(total=len(items), items=items)


@router.get("/{business_id}", response_model=RestaurantDetail)
def get_restaurant_detail(business_id: str) -> RestaurantDetail:
    return RestaurantDetail.model_validate(get_restaurant(business_id))


@router.get("/{business_id}/reviews", response_model=RestaurantReviewsResponse)
def list_restaurant_reviews(
    business_id: str,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> RestaurantReviewsResponse:
    items = get_restaurant_reviews(business_id, limit)
    return RestaurantReviewsResponse(business_id=business_id, total=len(items), items=items)
