from __future__ import annotations

from datetime import datetime
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.models import RestaurantAspectSignal
from app.db.session import get_session_factory


RESTAURANT_ASPECT_SUMMARY_COLUMNS = [
    "business_id",
    "overall_rating",
    "food_score",
    "service_score",
    "price_score",
    "ambience_score",
    "waiting_time_score",
    "pros",
    "cons",
    "risk_flags",
    "updated_at",
]


class RestaurantAspectSummaryToolInput(BaseModel):
    """Input for `get_restaurant_aspect_summary`."""

    business_id: str = Field(
        min_length=1,
        description=(
            "Selected Yelp restaurant business ID to fetch from the "
            "restaurant_aspect_signals table."
        ),
    )


class RestaurantAspectSummaryData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    business_id: str
    overall_rating: float | None = None
    food_score: float | None = None
    service_score: float | None = None
    price_score: float | None = None
    ambience_score: float | None = None
    waiting_time_score: float | None = None
    pros: list[str]
    cons: list[str]
    risk_flags: list[str]
    updated_at: datetime


class ToolDataSource(BaseModel):
    table: str
    columns: list[str]


class RestaurantAspectSummaryToolOutput(BaseModel):
    tool_name: Literal["get_restaurant_aspect_summary"] = "get_restaurant_aspect_summary"
    status: Literal["ok", "not_found"]
    data: RestaurantAspectSummaryData | None
    data_sources: list[ToolDataSource]
    errors: list[str] = Field(default_factory=list)


def get_restaurant_aspect_summary(
    session: Session,
    tool_input: RestaurantAspectSummaryToolInput,
) -> RestaurantAspectSummaryToolOutput:
    """Fetch restaurant-level precomputed aspect and risk summary.

    Supported intents:
    - recommendation: worth_it, should_go
    - aspect: food, service, price, ambience
    - scenario: date, family, quick_meal
    - risk: warnings
    - summary: summary

    Use this tool when an answer needs the restaurant-level aggregate view of
    aspect quality, overall rating, strengths, weaknesses, or risk flags. This
    tool should usually run after `get_restaurant_profile` and before fetching
    review-level evidence because it gives the final answer a compact summary
    of model-processed review signals.

    Do not use this tool to fetch individual review snippets, raw review text,
    per-review sentiment labels, recent trends, or scenario-specific evidence.
    Use `get_review_aspect_evidence`, `get_negative_review_patterns`,
    `get_positive_review_patterns`, or `get_scenario_fit` for those needs.

    Reads:
    - restaurant_aspect_signals.business_id
    - restaurant_aspect_signals.overall_rating
    - restaurant_aspect_signals.food_score
    - restaurant_aspect_signals.service_score
    - restaurant_aspect_signals.price_score
    - restaurant_aspect_signals.ambience_score
    - restaurant_aspect_signals.waiting_time_score
    - restaurant_aspect_signals.pros
    - restaurant_aspect_signals.cons
    - restaurant_aspect_signals.risk_flags
    - restaurant_aspect_signals.updated_at

    Input:
    - business_id: required selected restaurant ID.

    Flow:
    1. Validate `business_id` through `RestaurantAspectSummaryToolInput`.
    2. Load one `RestaurantAspectSignal` row by primary key from the active
       SQLAlchemy session.
    3. If no row exists, return `status="not_found"` with no data and a clear
       error.
    4. If found, serialize aggregate aspect fields into
       `RestaurantAspectSummaryData`.
    5. Return database source metadata so downstream nodes can explain what was
       used.

    Output:
    - status: `ok` when an aspect summary is found, otherwise `not_found`.
    - data: restaurant aspect summary object or null.
    - data_sources: table and column metadata for traceability.
    - errors: recoverable tool errors, empty on success.

    This tool does not generate recommendations or natural-language answers.
    """

    data_sources = [
        ToolDataSource(
            table="restaurant_aspect_signals",
            columns=RESTAURANT_ASPECT_SUMMARY_COLUMNS,
        )
    ]
    aspect_signal = session.get(RestaurantAspectSignal, tool_input.business_id)

    if aspect_signal is None:
        return RestaurantAspectSummaryToolOutput(
            status="not_found",
            data=None,
            data_sources=data_sources,
            errors=[f"Restaurant aspect summary not found: {tool_input.business_id}"],
        )

    return RestaurantAspectSummaryToolOutput(
        status="ok",
        data=RestaurantAspectSummaryData.model_validate(
            aspect_signal,
            from_attributes=True,
        ),
        data_sources=data_sources,
    )


@tool(
    "get_restaurant_aspect_summary",
    args_schema=RestaurantAspectSummaryToolInput,
    return_direct=False,
)
def get_restaurant_aspect_summary_tool(business_id: str) -> dict:
    """Fetch restaurant-level precomputed aspect and risk summary.

    Supported intents:
    - recommendation: worth_it, should_go
    - aspect: food, service, price, ambience
    - scenario: date, family, quick_meal
    - risk: warnings
    - summary: summary

    Use this tool when an answer needs the restaurant-level aggregate view of
    aspect quality, overall rating, strengths, weaknesses, or risk flags. This
    tool should usually run after `get_restaurant_profile` and before fetching
    review-level evidence because it gives the final answer a compact summary
    of model-processed review signals.

    Do not use this tool to fetch individual review snippets, raw review text,
    per-review sentiment labels, recent trends, or scenario-specific evidence.
    Use `get_review_aspect_evidence`, `get_negative_review_patterns`,
    `get_positive_review_patterns`, or `get_scenario_fit` for those needs.

    Reads:
    - restaurant_aspect_signals.business_id
    - restaurant_aspect_signals.overall_rating
    - restaurant_aspect_signals.food_score
    - restaurant_aspect_signals.service_score
    - restaurant_aspect_signals.price_score
    - restaurant_aspect_signals.ambience_score
    - restaurant_aspect_signals.waiting_time_score
    - restaurant_aspect_signals.pros
    - restaurant_aspect_signals.cons
    - restaurant_aspect_signals.risk_flags
    - restaurant_aspect_signals.updated_at

    Input:
    - business_id: required selected restaurant ID.

    Flow:
    1. Validate `business_id` through the LangChain args schema.
    2. Open a SQLAlchemy session using the configured application database.
    3. Load one `RestaurantAspectSignal` row by primary key.
    4. Return `status="not_found"` with an error if no summary exists.
    5. Return restaurant-level aspect data plus source table metadata when
       found.

    Output:
    - tool_name: get_restaurant_aspect_summary.
    - status: ok or not_found.
    - data: restaurant aspect summary object or null.
    - data_sources: table and column metadata for traceability.
    - errors: recoverable tool errors, empty on success.

    This tool does not generate recommendations or natural-language answers.
    """

    with get_session_factory()() as session:
        result = get_restaurant_aspect_summary(
            session,
            RestaurantAspectSummaryToolInput(business_id=business_id),
        )
    return result.model_dump()
