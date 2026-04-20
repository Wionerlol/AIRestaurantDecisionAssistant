from __future__ import annotations

from datetime import datetime
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import Review, ReviewAspectSignal
from app.db.session import get_session_factory


AspectName = Literal["food", "service", "price", "ambience", "waiting_time"]
SentimentLabel = Literal["positive", "negative", "neutral", "mixed"]

ASPECT_SCORE_FIELDS: dict[str, str] = {
    "food": "food_score",
    "service": "service_score",
    "price": "price_score",
    "ambience": "ambience_score",
    "waiting_time": "waiting_time_score",
}

REVIEW_EVIDENCE_COLUMNS = [
    "review_id",
    "business_id",
    "stars",
    "text",
    "review_date",
]

REVIEW_ASPECT_EVIDENCE_COLUMNS = [
    "review_id",
    "business_id",
    "overall_sentiment_score",
    "overall_sentiment_label",
    "food_score",
    "service_score",
    "price_score",
    "ambience_score",
    "waiting_time_score",
    "aspect_sentiments",
    "evidence_terms",
    "pros",
    "cons",
    "risk_flags",
    "model_name",
    "model_version",
    "confidence",
    "updated_at",
]


class ReviewAspectEvidenceToolInput(BaseModel):
    """Input for `get_review_aspect_evidence`."""

    business_id: str = Field(
        min_length=1,
        description="Selected Yelp restaurant business ID used to fetch review evidence.",
    )
    aspect: AspectName | None = Field(
        default=None,
        description="Optional single aspect to focus on.",
    )
    aspects: list[AspectName] = Field(
        default_factory=list,
        description="Optional list of aspects to focus on.",
    )
    sentiment: SentimentLabel | None = Field(
        default=None,
        description="Optional sentiment label filter: positive, negative, neutral, or mixed.",
    )
    limit: int = Field(
        default=8,
        ge=1,
        le=50,
        description="Maximum number of review evidence rows to return.",
    )

    @model_validator(mode="after")
    def merge_single_aspect(self) -> "ReviewAspectEvidenceToolInput":
        if self.aspect is not None and self.aspect not in self.aspects:
            self.aspects.insert(0, self.aspect)
        return self


class ReviewAspectEvidenceItem(BaseModel):
    review_id: str
    business_id: str
    stars: float
    text: str
    review_date: datetime
    overall_sentiment_score: float | None = None
    overall_sentiment_label: str | None = None
    aspect_scores: dict[str, float | None]
    selected_aspect_scores: dict[str, float | None]
    aspect_sentiments: dict[str, float | str | None]
    evidence_terms: list[str]
    pros: list[str]
    cons: list[str]
    risk_flags: list[str]
    model_name: str | None = None
    model_version: str | None = None
    confidence: float | None = None


class ReviewAspectEvidenceData(BaseModel):
    business_id: str
    total: int
    items: list[ReviewAspectEvidenceItem]


class ToolDataSource(BaseModel):
    table: str
    columns: list[str]


class ReviewAspectEvidenceToolOutput(BaseModel):
    tool_name: Literal["get_review_aspect_evidence"] = "get_review_aspect_evidence"
    status: Literal["ok", "empty"]
    data: ReviewAspectEvidenceData
    data_sources: list[ToolDataSource]
    errors: list[str] = Field(default_factory=list)


def get_review_aspect_evidence(
    session: Session,
    tool_input: ReviewAspectEvidenceToolInput,
) -> ReviewAspectEvidenceToolOutput:
    """Fetch review-level aspect and sentiment evidence for a restaurant.

    Supported intents:
    - aspect: food, service, price, ambience
    - scenario: date, family, quick_meal
    - risk: complaints
    - summary: summary

    Use this tool when an answer needs evidence from individual reviews and
    review-level static model outputs. It connects raw review text from
    `reviews` with per-review aspect and sentiment predictions from
    `review_aspect_signals`.

    Use this tool for questions such as:
    - How is the food?
    - How is the service?
    - Is it expensive?
    - How is the ambience?
    - Is it good for a date?
    - Any common complaints?
    - Give me a summary.

    Do not use this tool for restaurant identity or high-level profile fields;
    use `get_restaurant_profile` for that. Do not use this tool for the
    restaurant-level aggregate summary; use `get_restaurant_aspect_summary` for
    that. Do not use this tool to generate the final answer directly.

    Reads:
    - reviews.review_id
    - reviews.business_id
    - reviews.stars
    - reviews.text
    - reviews.review_date
    - review_aspect_signals.review_id
    - review_aspect_signals.business_id
    - review_aspect_signals.overall_sentiment_score
    - review_aspect_signals.overall_sentiment_label
    - review_aspect_signals.food_score
    - review_aspect_signals.service_score
    - review_aspect_signals.price_score
    - review_aspect_signals.ambience_score
    - review_aspect_signals.waiting_time_score
    - review_aspect_signals.aspect_sentiments
    - review_aspect_signals.evidence_terms
    - review_aspect_signals.pros
    - review_aspect_signals.cons
    - review_aspect_signals.risk_flags
    - review_aspect_signals.model_name
    - review_aspect_signals.model_version
    - review_aspect_signals.confidence

    Input:
    - business_id: required selected restaurant ID.
    - aspect: optional single aspect filter or focus.
    - aspects: optional list of aspect focuses.
    - sentiment: optional strict sentiment label filter.
    - limit: maximum number of evidence rows, default 8, max 50.

    Flow:
    1. Validate input through `ReviewAspectEvidenceToolInput`.
    2. Join `reviews` to `review_aspect_signals` by `review_id`.
    3. Restrict rows to the selected `business_id`.
    4. If `sentiment` is provided, filter by
       `review_aspect_signals.overall_sentiment_label`.
    5. Sort deterministically by review recency and review ID.
    6. Return bounded evidence rows with all aspect scores and selected aspect
       scores separated for easier downstream prompting.

    Output:
    - status: `ok` when one or more rows are returned, otherwise `empty`.
    - data.total: number of returned evidence rows.
    - data.items: review-level evidence objects.
    - data_sources: table and column metadata for traceability.
    - errors: recoverable tool errors, empty on success.

    This tool does not generate recommendations or natural-language answers.
    """

    data_sources = [
        ToolDataSource(table="reviews", columns=REVIEW_EVIDENCE_COLUMNS),
        ToolDataSource(
            table="review_aspect_signals",
            columns=REVIEW_ASPECT_EVIDENCE_COLUMNS,
        ),
    ]
    statement = (
        select(Review, ReviewAspectSignal)
        .join(ReviewAspectSignal, Review.review_id == ReviewAspectSignal.review_id)
        .where(Review.business_id == tool_input.business_id)
        .order_by(desc(Review.review_date), Review.review_id)
        .limit(tool_input.limit)
    )

    if tool_input.sentiment is not None:
        statement = statement.where(
            ReviewAspectSignal.overall_sentiment_label == tool_input.sentiment
        )

    rows = session.execute(statement).all()
    items = [_build_evidence_item(review, signal, tool_input.aspects) for review, signal in rows]
    status: Literal["ok", "empty"] = "ok" if items else "empty"

    return ReviewAspectEvidenceToolOutput(
        status=status,
        data=ReviewAspectEvidenceData(
            business_id=tool_input.business_id,
            total=len(items),
            items=items,
        ),
        data_sources=data_sources,
    )


def _build_evidence_item(
    review: Review,
    signal: ReviewAspectSignal,
    selected_aspects: list[AspectName],
) -> ReviewAspectEvidenceItem:
    aspect_scores = {
        aspect: getattr(signal, score_field) for aspect, score_field in ASPECT_SCORE_FIELDS.items()
    }
    selected_aspect_scores = {
        aspect: aspect_scores[aspect] for aspect in selected_aspects if aspect in aspect_scores
    }

    return ReviewAspectEvidenceItem(
        review_id=review.review_id,
        business_id=review.business_id,
        stars=review.stars,
        text=review.text,
        review_date=review.review_date,
        overall_sentiment_score=signal.overall_sentiment_score,
        overall_sentiment_label=signal.overall_sentiment_label,
        aspect_scores=aspect_scores,
        selected_aspect_scores=selected_aspect_scores,
        aspect_sentiments=signal.aspect_sentiments,
        evidence_terms=signal.evidence_terms,
        pros=signal.pros,
        cons=signal.cons,
        risk_flags=signal.risk_flags,
        model_name=signal.model_name,
        model_version=signal.model_version,
        confidence=signal.confidence,
    )


@tool(
    "get_review_aspect_evidence",
    args_schema=ReviewAspectEvidenceToolInput,
    return_direct=False,
)
def get_review_aspect_evidence_tool(
    business_id: str,
    aspect: AspectName | None = None,
    aspects: list[AspectName] | None = None,
    sentiment: SentimentLabel | None = None,
    limit: int = 8,
) -> dict:
    """Fetch review-level aspect and sentiment evidence for a restaurant.

    Supported intents:
    - aspect: food, service, price, ambience
    - scenario: date, family, quick_meal
    - risk: complaints
    - summary: summary

    Use this tool when an answer needs evidence from individual reviews and
    review-level static model outputs. It connects raw review text from
    `reviews` with per-review aspect and sentiment predictions from
    `review_aspect_signals`.

    Do not use this tool for restaurant identity or high-level profile fields;
    use `get_restaurant_profile` for that. Do not use this tool for the
    restaurant-level aggregate summary; use `get_restaurant_aspect_summary` for
    that. Do not use this tool to generate the final answer directly.

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
    - review_aspect_signals.aspect_sentiments
    - review_aspect_signals.evidence_terms
    - review_aspect_signals.pros
    - review_aspect_signals.cons
    - review_aspect_signals.risk_flags
    - review_aspect_signals.model_name
    - review_aspect_signals.model_version
    - review_aspect_signals.confidence

    Input:
    - business_id: required selected restaurant ID.
    - aspect: optional single aspect focus.
    - aspects: optional list of aspect focuses.
    - sentiment: optional positive, negative, neutral, or mixed filter.
    - limit: maximum number of evidence rows.

    Flow:
    1. Validate arguments through the LangChain args schema.
    2. Open a SQLAlchemy session using the configured application database.
    3. Join `reviews` with `review_aspect_signals`.
    4. Apply the selected restaurant and optional sentiment filters.
    5. Return bounded review evidence sorted by recency and review ID.

    Output:
    - tool_name: get_review_aspect_evidence.
    - status: ok or empty.
    - data.total: number of returned evidence rows.
    - data.items: review evidence objects with review text, sentiment, aspect
      scores, selected aspect scores, evidence terms, pros, cons, risk flags,
      model metadata, and confidence.
    - data_sources: table and column metadata for traceability.
    - errors: recoverable tool errors, empty on success.

    This tool does not generate recommendations or natural-language answers.
    """

    with get_session_factory()() as session:
        result = get_review_aspect_evidence(
            session,
            ReviewAspectEvidenceToolInput(
                business_id=business_id,
                aspect=aspect,
                aspects=aspects or [],
                sentiment=sentiment,
                limit=limit,
            ),
        )
    return result.model_dump()
