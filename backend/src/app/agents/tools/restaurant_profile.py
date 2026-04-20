from __future__ import annotations

from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.models import Restaurant
from app.db.session import get_session_factory


RESTAURANT_PROFILE_COLUMNS = [
    "business_id",
    "name",
    "address",
    "city",
    "state",
    "postal_code",
    "latitude",
    "longitude",
    "stars",
    "review_count",
    "is_open",
    "categories",
]


class RestaurantProfileToolInput(BaseModel):
    """Input for `get_restaurant_profile`."""

    business_id: str = Field(
        min_length=1,
        description="Selected Yelp restaurant business ID to fetch from the restaurants table.",
    )


class RestaurantProfileData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    business_id: str
    name: str
    address: str | None = None
    city: str
    state: str
    postal_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    stars: float | None = None
    review_count: int
    is_open: int | None = None
    categories: list[str]


class ToolDataSource(BaseModel):
    table: str
    columns: list[str]


class RestaurantProfileToolOutput(BaseModel):
    tool_name: Literal["get_restaurant_profile"] = "get_restaurant_profile"
    status: Literal["ok", "not_found"]
    data: RestaurantProfileData | None
    data_sources: list[ToolDataSource]
    errors: list[str] = Field(default_factory=list)


def get_restaurant_profile(
    session: Session,
    tool_input: RestaurantProfileToolInput,
) -> RestaurantProfileToolOutput:
    """Fetch the selected restaurant's base profile from the database.

    Supported intents:
    - recommendation: worth_it, should_go
    - aspect: food, service, price, ambience
    - scenario: date, family, quick_meal
    - summary: summary

    Use this tool when an answer needs the selected restaurant's identity,
    location, category, rating, open flag, or review volume. This should usually
    be the first restaurant-specific tool in a tool plan because later evidence
    and final answers need a stable restaurant profile for grounding.

    Do not use this tool for unsupported or general non-restaurant questions.
    Do not use this tool to fetch reviews, aspect scores, sentiment outputs,
    complaints, evidence snippets, or scenario judgments.

    Reads:
    - restaurants.business_id
    - restaurants.name
    - restaurants.address
    - restaurants.city
    - restaurants.state
    - restaurants.postal_code
    - restaurants.latitude
    - restaurants.longitude
    - restaurants.stars
    - restaurants.review_count
    - restaurants.is_open
    - restaurants.categories

    Input:
    - business_id: required selected restaurant ID.

    Flow:
    1. Validate `business_id` through `RestaurantProfileToolInput`.
    2. Load one `Restaurant` row by primary key from the active SQLAlchemy session.
    3. If no row exists, return `status="not_found"` with no data and a clear error.
    4. If found, serialize only profile fields into `RestaurantProfileData`.
    5. Return database source metadata so downstream nodes can explain what was used.

    Output:
    - status: `ok` when a restaurant is found, otherwise `not_found`.
    - data: restaurant profile object or null.
    - data_sources: table and column metadata for traceability.
    - errors: recoverable tool errors, empty on success.

    This tool does not generate recommendations or natural-language answers.
    """

    data_sources = [ToolDataSource(table="restaurants", columns=RESTAURANT_PROFILE_COLUMNS)]
    restaurant = session.get(Restaurant, tool_input.business_id)

    if restaurant is None:
        return RestaurantProfileToolOutput(
            status="not_found",
            data=None,
            data_sources=data_sources,
            errors=[f"Restaurant not found: {tool_input.business_id}"],
        )

    return RestaurantProfileToolOutput(
        status="ok",
        data=RestaurantProfileData.model_validate(restaurant, from_attributes=True),
        data_sources=data_sources,
    )


@tool(
    "get_restaurant_profile",
    args_schema=RestaurantProfileToolInput,
    return_direct=False,
)
def get_restaurant_profile_tool(business_id: str) -> dict:
    """Fetch the selected restaurant's base profile from the database.

    Supported intents:
    - recommendation: worth_it, should_go
    - aspect: food, service, price, ambience
    - scenario: date, family, quick_meal
    - summary: summary

    Use this tool when an answer needs the selected restaurant's identity,
    location, category, rating, open flag, or review volume. This should usually
    be the first restaurant-specific tool in a tool plan because later evidence
    and final answers need a stable restaurant profile for grounding.

    Do not use this tool for unsupported or general non-restaurant questions.
    Do not use this tool to fetch reviews, aspect scores, sentiment outputs,
    complaints, evidence snippets, or scenario judgments.

    Reads:
    - restaurants.business_id
    - restaurants.name
    - restaurants.address
    - restaurants.city
    - restaurants.state
    - restaurants.postal_code
    - restaurants.latitude
    - restaurants.longitude
    - restaurants.stars
    - restaurants.review_count
    - restaurants.is_open
    - restaurants.categories

    Input:
    - business_id: required selected restaurant ID.

    Flow:
    1. Validate `business_id` through the LangChain args schema.
    2. Open a SQLAlchemy session using the configured application database.
    3. Load one `Restaurant` row by primary key.
    4. Return `status="not_found"` with an error if no restaurant exists.
    5. Return restaurant profile data plus source table metadata when found.

    Output:
    - tool_name: get_restaurant_profile.
    - status: ok or not_found.
    - data: restaurant profile object or null.
    - data_sources: table and column metadata for traceability.
    - errors: recoverable tool errors, empty on success.

    This tool does not generate recommendations or natural-language answers.
    """

    with get_session_factory()() as session:
        result = get_restaurant_profile(
            session,
            RestaurantProfileToolInput(business_id=business_id),
        )
    return result.model_dump()
