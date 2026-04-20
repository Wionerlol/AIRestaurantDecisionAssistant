from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import Review, ReviewAspectSignal
from app.db.session import get_session_factory


TrendDirection = Literal["improving", "declining", "stable", "unknown"]

ASPECT_SCORE_FIELDS: dict[str, str] = {
    "food": "food_score",
    "service": "service_score",
    "price": "price_score",
    "ambience": "ambience_score",
    "waiting_time": "waiting_time_score",
}

RECENT_REVIEW_COLUMNS = [
    "review_id",
    "business_id",
    "stars",
    "text",
    "review_date",
]

RECENT_REVIEW_ASPECT_COLUMNS = [
    "review_id",
    "business_id",
    "overall_sentiment_score",
    "overall_sentiment_label",
    "food_score",
    "service_score",
    "price_score",
    "ambience_score",
    "waiting_time_score",
    "risk_flags",
    "confidence",
]


class RecentReviewTrendToolInput(BaseModel):
    """Input for `get_recent_review_trend`."""

    business_id: str = Field(
        min_length=1,
        description="Selected Yelp restaurant business ID used to fetch recent trend data.",
    )
    months: int | None = Field(
        default=None,
        ge=1,
        le=120,
        description=(
            "Optional window size in months, measured backwards from the selected "
            "restaurant's latest available review date."
        ),
    )
    limit: int = Field(
        default=12,
        ge=1,
        le=100,
        description="Maximum number of recent review rows to inspect and return.",
    )


class RecentReviewTrendItem(BaseModel):
    review_id: str
    business_id: str
    stars: float
    text: str
    review_date: datetime
    overall_sentiment_score: float | None = None
    overall_sentiment_label: str | None = None
    aspect_scores: dict[str, float | None]
    risk_flags: list[str]
    confidence: float | None = None


class RecentReviewTrendData(BaseModel):
    business_id: str
    total: int
    months: int | None = None
    date_range_start: datetime | None = None
    date_range_end: datetime | None = None
    average_stars: float | None = None
    average_sentiment_score: float | None = None
    sentiment_label_counts: dict[str, int]
    aspect_average_scores: dict[str, float | None]
    previous_average_stars: float | None = None
    star_trend: TrendDirection
    items: list[RecentReviewTrendItem]


class ToolDataSource(BaseModel):
    table: str
    columns: list[str]


class RecentReviewTrendToolOutput(BaseModel):
    tool_name: Literal["get_recent_review_trend"] = "get_recent_review_trend"
    status: Literal["ok", "empty"]
    data: RecentReviewTrendData
    data_sources: list[ToolDataSource]
    errors: list[str] = Field(default_factory=list)


def get_recent_review_trend(
    session: Session,
    tool_input: RecentReviewTrendToolInput,
) -> RecentReviewTrendToolOutput:
    """Summarize recent review sentiment, rating, and aspect trend.

    Supported intents:
    - scenario: quick_meal
    - risk: complaints, warnings
    - summary: summary

    Use this tool when an answer needs to know whether recent reviews look
    better, worse, or stable compared with older reviews. It is useful for
    surfacing recent quality changes, recent complaints, and whether older
    restaurant-level aggregates might be stale.

    Do not use this tool as the primary source for restaurant identity,
    restaurant-level aggregate aspects, broad positive strengths, or broad
    negative patterns. Use `get_restaurant_profile`,
    `get_restaurant_aspect_summary`, `get_positive_review_patterns`, or
    `get_negative_review_patterns` for those needs.

    Reads:
    - reviews.review_id
    - reviews.business_id
    - reviews.stars
    - reviews.text
    - reviews.review_date
    - review_aspect_signals.overall_sentiment_score
    - review_aspect_signals.overall_sentiment_label
    - review_aspect_signals.food_score
    - review_aspect_signals.service_score
    - review_aspect_signals.price_score
    - review_aspect_signals.ambience_score
    - review_aspect_signals.waiting_time_score
    - review_aspect_signals.risk_flags
    - review_aspect_signals.confidence

    Input:
    - business_id: required selected restaurant ID.
    - months: optional window size measured backwards from the restaurant's
      latest available review date.
    - limit: maximum number of recent review rows to inspect and return.

    Flow:
    1. Validate input through `RecentReviewTrendToolInput`.
    2. Find the selected restaurant's latest available review date.
    3. If `months` is provided, filter reviews to that relative window.
    4. Join `reviews` to `review_aspect_signals` by `review_id`.
    5. Sort recent reviews by recency and review ID.
    6. Compute average stars, average sentiment score, sentiment label counts,
       and average aspect scores from returned rows.
    7. Fetch the previous equally-sized window before the recent rows and
       compare average stars to produce a coarse trend direction.

    Output:
    - status: `ok` when recent rows exist, otherwise `empty`.
    - data.average_stars: mean Yelp stars in the recent window.
    - data.average_sentiment_score: mean model sentiment score when available.
    - data.sentiment_label_counts: label frequency map.
    - data.aspect_average_scores: average aspect score map.
    - data.previous_average_stars: prior comparison window mean stars.
    - data.star_trend: improving, declining, stable, or unknown.
    - data.items: representative recent review rows.
    - data_sources: table and column metadata for traceability.
    - errors: recoverable tool errors, empty on success.

    This tool does not generate recommendations or natural-language answers.
    """

    data_sources = [
        ToolDataSource(table="reviews", columns=RECENT_REVIEW_COLUMNS),
        ToolDataSource(
            table="review_aspect_signals",
            columns=RECENT_REVIEW_ASPECT_COLUMNS,
        ),
    ]
    latest_review_date = session.scalar(
        select(Review.review_date)
        .where(Review.business_id == tool_input.business_id)
        .order_by(desc(Review.review_date), Review.review_id)
        .limit(1)
    )
    if latest_review_date is None:
        return RecentReviewTrendToolOutput(
            status="empty",
            data=_empty_data(tool_input),
            data_sources=data_sources,
        )

    cutoff = _cutoff_date(latest_review_date, tool_input.months)
    statement = (
        select(Review, ReviewAspectSignal)
        .join(ReviewAspectSignal, Review.review_id == ReviewAspectSignal.review_id)
        .where(Review.business_id == tool_input.business_id)
        .order_by(desc(Review.review_date), Review.review_id)
        .limit(tool_input.limit)
    )
    if cutoff is not None:
        statement = statement.where(Review.review_date >= cutoff)

    rows = session.execute(statement).all()
    items = [_build_trend_item(review, signal) for review, signal in rows]
    if not items:
        return RecentReviewTrendToolOutput(
            status="empty",
            data=_empty_data(tool_input),
            data_sources=data_sources,
        )

    oldest_recent_date = min(item.review_date for item in items)
    previous_average_stars = _previous_average_stars(
        session,
        tool_input.business_id,
        oldest_recent_date,
        len(items),
    )

    return RecentReviewTrendToolOutput(
        status="ok",
        data=RecentReviewTrendData(
            business_id=tool_input.business_id,
            total=len(items),
            months=tool_input.months,
            date_range_start=oldest_recent_date,
            date_range_end=max(item.review_date for item in items),
            average_stars=_average([item.stars for item in items]),
            average_sentiment_score=_average(
                [
                    item.overall_sentiment_score
                    for item in items
                    if item.overall_sentiment_score is not None
                ]
            ),
            sentiment_label_counts=dict(
                Counter(
                    item.overall_sentiment_label
                    for item in items
                    if item.overall_sentiment_label is not None
                )
            ),
            aspect_average_scores=_aspect_average_scores(items),
            previous_average_stars=previous_average_stars,
            star_trend=_star_trend(
                _average([item.stars for item in items]),
                previous_average_stars,
            ),
            items=items,
        ),
        data_sources=data_sources,
    )


def _cutoff_date(latest_review_date: datetime, months: int | None) -> datetime | None:
    if months is None:
        return None
    return latest_review_date - timedelta(days=months * 30)


def _empty_data(tool_input: RecentReviewTrendToolInput) -> RecentReviewTrendData:
    return RecentReviewTrendData(
        business_id=tool_input.business_id,
        total=0,
        months=tool_input.months,
        sentiment_label_counts={},
        aspect_average_scores={aspect: None for aspect in ASPECT_SCORE_FIELDS},
        star_trend="unknown",
        items=[],
    )


def _build_trend_item(review: Review, signal: ReviewAspectSignal) -> RecentReviewTrendItem:
    return RecentReviewTrendItem(
        review_id=review.review_id,
        business_id=review.business_id,
        stars=review.stars,
        text=review.text,
        review_date=review.review_date,
        overall_sentiment_score=signal.overall_sentiment_score,
        overall_sentiment_label=signal.overall_sentiment_label,
        aspect_scores={
            aspect: getattr(signal, score_field)
            for aspect, score_field in ASPECT_SCORE_FIELDS.items()
        },
        risk_flags=signal.risk_flags,
        confidence=signal.confidence,
    )


def _previous_average_stars(
    session: Session,
    business_id: str,
    oldest_recent_date: datetime,
    limit: int,
) -> float | None:
    previous_stars = list(
        session.scalars(
            select(Review.stars)
            .where(Review.business_id == business_id)
            .where(Review.review_date < oldest_recent_date)
            .order_by(desc(Review.review_date), Review.review_id)
            .limit(limit)
        )
    )
    return _average(previous_stars)


def _aspect_average_scores(items: list[RecentReviewTrendItem]) -> dict[str, float | None]:
    return {
        aspect: _average(
            [item.aspect_scores[aspect] for item in items if item.aspect_scores[aspect] is not None]
        )
        for aspect in ASPECT_SCORE_FIELDS
    }


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def _star_trend(
    recent_average_stars: float | None,
    previous_average_stars: float | None,
) -> TrendDirection:
    if recent_average_stars is None or previous_average_stars is None:
        return "unknown"
    delta = recent_average_stars - previous_average_stars
    if delta >= 0.25:
        return "improving"
    if delta <= -0.25:
        return "declining"
    return "stable"


@tool(
    "get_recent_review_trend",
    args_schema=RecentReviewTrendToolInput,
    return_direct=False,
)
def get_recent_review_trend_tool(
    business_id: str,
    months: int | None = None,
    limit: int = 12,
) -> dict:
    """Summarize recent review sentiment, rating, and aspect trend.

    Supported intents:
    - scenario: quick_meal
    - risk: complaints, warnings
    - summary: summary

    Use this tool when an answer needs to know whether recent reviews look
    better, worse, or stable compared with older reviews. It is useful for
    recent quality changes, recent complaints, and stale aggregate checks.

    Do not use this tool as the primary source for restaurant identity,
    restaurant-level aggregate aspects, broad positive strengths, or broad
    negative patterns. Use `get_restaurant_profile`,
    `get_restaurant_aspect_summary`, `get_positive_review_patterns`, or
    `get_negative_review_patterns` for those needs.

    Reads:
    - reviews.review_id, business_id, stars, text, review_date
    - review_aspect_signals overall sentiment fields, aspect scores,
      risk_flags, confidence

    Input:
    - business_id: required selected restaurant ID.
    - months: optional window size measured backwards from the restaurant's
      latest available review date.
    - limit: maximum number of recent review rows to inspect and return.

    Flow:
    1. Validate arguments through the LangChain args schema.
    2. Open a SQLAlchemy session using the configured application database.
    3. Find the restaurant's latest review date and optional relative cutoff.
    4. Join `reviews` with `review_aspect_signals`.
    5. Compute recent averages, sentiment label counts, aspect averages, and
       a coarse star trend versus the previous review window.

    Output:
    - tool_name: get_recent_review_trend.
    - status: ok or empty.
    - data.average_stars and data.average_sentiment_score.
    - data.sentiment_label_counts.
    - data.aspect_average_scores.
    - data.previous_average_stars and data.star_trend.
    - data.items: representative recent review rows.
    - data_sources: table and column metadata for traceability.
    - errors: recoverable tool errors, empty on success.

    This tool does not generate recommendations or natural-language answers.
    """

    with get_session_factory()() as session:
        result = get_recent_review_trend(
            session,
            RecentReviewTrendToolInput(
                business_id=business_id,
                months=months,
                limit=limit,
            ),
        )
    return result.model_dump()
