from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.schemas.restaurants import (
    RestaurantDetail,
    RestaurantReviewsResponse,
    RestaurantSearchResponse,
    RestaurantSummary,
)
from app.db.session import get_db_session
from app.schemas.restaurants import RestaurantReview
from app.services.restaurant_service import (
    get_restaurant,
    get_restaurant_reviews,
    list_restaurants as fetch_restaurants,
)


router = APIRouter(prefix="/restaurants", tags=["restaurants"])


@router.get("", response_model=RestaurantSearchResponse)
def list_restaurants(
    query: Annotated[str | None, Query(min_length=1)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    session: Session = Depends(get_db_session),
) -> RestaurantSearchResponse:
    items = [
        RestaurantSummary.model_validate(item, from_attributes=True)
        for item in fetch_restaurants(session, query, limit)
    ]
    return RestaurantSearchResponse(total=len(items), items=items)


@router.get("/{business_id}", response_model=RestaurantDetail)
def get_restaurant_detail(
    business_id: str,
    session: Session = Depends(get_db_session),
) -> RestaurantDetail:
    restaurant = get_restaurant(session, business_id)
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return RestaurantDetail.model_validate(restaurant, from_attributes=True)


@router.get("/{business_id}/reviews", response_model=RestaurantReviewsResponse)
def list_restaurant_reviews(
    business_id: str,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    session: Session = Depends(get_db_session),
) -> RestaurantReviewsResponse:
    restaurant = get_restaurant(session, business_id)
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    items = [
        RestaurantReview.model_validate(
            {
                "review_id": review.review_id,
                "user_id": review.user_id,
                "business_id": review.business_id,
                "stars": review.stars,
                "useful": review.useful,
                "funny": review.funny,
                "cool": review.cool,
                "text": review.text,
                "date": review.review_date.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        for review in get_restaurant_reviews(session, business_id, limit)
    ]
    return RestaurantReviewsResponse(business_id=business_id, total=len(items), items=items)
