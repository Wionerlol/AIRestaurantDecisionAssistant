from pydantic import BaseModel, ConfigDict


class RestaurantSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    business_id: str
    name: str
    city: str
    state: str
    stars: float | None = None
    review_count: int
    categories: list[str]


class RestaurantDetail(RestaurantSummary):
    address: str | None = None
    postal_code: str | None = None
    is_open: int | None = None


class RestaurantReview(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    review_id: str
    user_id: str
    business_id: str
    stars: float
    useful: int
    funny: int
    cool: int
    text: str
    date: str


class RestaurantSearchResponse(BaseModel):
    total: int
    items: list[RestaurantSummary]


class RestaurantReviewsResponse(BaseModel):
    business_id: str
    total: int
    items: list[RestaurantReview]
