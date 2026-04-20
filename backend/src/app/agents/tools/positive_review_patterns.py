from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.agents.tools.review_evidence_scoring import (
    ReviewEvidenceScoringConfig,
    build_candidate_from_review_signal,
    score_review_evidence,
)
from app.db.models import RestaurantAspectSignal, Review, ReviewAspectSignal
from app.db.session import get_session_factory


AspectName = Literal["food", "service", "price", "ambience", "waiting_time"]

ASPECT_SCORE_FIELDS: dict[str, str] = {
    "food": "food_score",
    "service": "service_score",
    "price": "price_score",
    "ambience": "ambience_score",
    "waiting_time": "waiting_time_score",
}

POSITIVE_REVIEW_COLUMNS = [
    "review_id",
    "business_id",
    "stars",
    "text",
    "review_date",
]

POSITIVE_REVIEW_ASPECT_COLUMNS = [
    "review_id",
    "business_id",
    "overall_sentiment_score",
    "overall_sentiment_label",
    "food_score",
    "service_score",
    "price_score",
    "ambience_score",
    "waiting_time_score",
    "evidence_terms",
    "pros",
    "confidence",
]

POSITIVE_RESTAURANT_ASPECT_COLUMNS = [
    "business_id",
    "pros",
    "food_score",
    "service_score",
    "price_score",
    "ambience_score",
    "waiting_time_score",
    "updated_at",
]

POSITIVE_KEYWORDS = [
    "great",
    "good",
    "excellent",
    "friendly",
    "fresh",
    "flavorful",
    "quick",
    "cozy",
    "quiet",
    "reasonable",
]


class PositiveReviewPatternsToolInput(BaseModel):
    """Input for `get_positive_review_patterns`."""

    business_id: str = Field(
        min_length=1,
        description="Selected Yelp restaurant business ID used to fetch positive patterns.",
    )
    aspect: AspectName | None = Field(
        default=None,
        description="Optional aspect focus for positive evidence.",
    )
    limit: int = Field(
        default=8,
        ge=1,
        le=50,
        description="Maximum number of representative positive review rows to return.",
    )


class PositiveReviewEvidenceItem(BaseModel):
    review_id: str
    business_id: str
    stars: float
    text: str
    review_date: datetime
    overall_sentiment_score: float | None = None
    overall_sentiment_label: str | None = None
    selected_aspect_score: float | None = None
    evidence_terms: list[str]
    pros: list[str]
    relevance_score: float | None = None
    matched_keywords: list[str] = Field(default_factory=list)
    confidence: float | None = None
    positive_reasons: list[str]


class PositiveReviewPatternsData(BaseModel):
    business_id: str
    aspect: AspectName | None = None
    total: int
    top_pros: list[str]
    top_evidence_terms: list[str]
    restaurant_level_pros: list[str]
    items: list[PositiveReviewEvidenceItem]


class ToolDataSource(BaseModel):
    table: str
    columns: list[str]


class PositiveReviewPatternsToolOutput(BaseModel):
    tool_name: Literal["get_positive_review_patterns"] = "get_positive_review_patterns"
    status: Literal["ok", "empty"]
    data: PositiveReviewPatternsData
    data_sources: list[ToolDataSource]
    errors: list[str] = Field(default_factory=list)


def get_positive_review_patterns(
    session: Session,
    tool_input: PositiveReviewPatternsToolInput,
) -> PositiveReviewPatternsToolOutput:
    """Aggregate common strengths and positive review evidence.

    Supported intents:
    - recommendation: worth_it
    - aspect: food, service, price, ambience
    - summary: summary

    Use this tool when an answer needs common strengths, positive themes, or
    representative positive reviews for the selected restaurant. This tool
    helps final answers explain what diners consistently liked before making a
    balanced recommendation.

    Do not use this tool to fetch the restaurant profile, common complaints,
    risk warnings, generic review evidence, or recent trend summaries. Use
    `get_restaurant_profile`, `get_negative_review_patterns`,
    `get_review_aspect_evidence`, or `get_recent_review_trend` for those needs.

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
    - review_aspect_signals.evidence_terms
    - review_aspect_signals.pros
    - review_aspect_signals.confidence
    - restaurant_aspect_signals.pros

    Input:
    - business_id: required selected restaurant ID.
    - aspect: optional aspect focus.
    - limit: maximum number of representative positive evidence rows.

    Flow:
    1. Validate input through `PositiveReviewPatternsToolInput`.
    2. Load restaurant-level pros from `restaurant_aspect_signals`.
    3. Join `reviews` to `review_aspect_signals` by `review_id`.
    4. Restrict rows to the selected `business_id`.
    5. Identify positive evidence in Python using any of these signals:
       positive sentiment label, high overall sentiment score, high selected
       aspect score, high Yelp stars, or non-empty pros.
    6. Rank representative reviews with the shared review evidence scorer using
       positive keywords, positive sentiment, high aspect scores, confidence,
       recency, and high stars.
    7. Aggregate top pros and evidence terms from review-level and
       restaurant-level signals.

    Output:
    - status: `ok` when positive patterns or evidence exist, otherwise `empty`.
    - data.top_pros: most common positive themes.
    - data.top_evidence_terms: common positive evidence terms.
    - data.items: representative positive review evidence with relevance score
      and matched keywords.
    - data_sources: table and column metadata for traceability.
    - errors: recoverable tool errors, empty on success.

    This tool does not generate recommendations or natural-language answers.
    """

    data_sources = [
        ToolDataSource(table="reviews", columns=POSITIVE_REVIEW_COLUMNS),
        ToolDataSource(
            table="review_aspect_signals",
            columns=POSITIVE_REVIEW_ASPECT_COLUMNS,
        ),
        ToolDataSource(
            table="restaurant_aspect_signals",
            columns=POSITIVE_RESTAURANT_ASPECT_COLUMNS,
        ),
    ]
    restaurant_signal = session.get(RestaurantAspectSignal, tool_input.business_id)
    rows = session.execute(
        select(Review, ReviewAspectSignal)
        .join(ReviewAspectSignal, Review.review_id == ReviewAspectSignal.review_id)
        .where(Review.business_id == tool_input.business_id)
        .order_by(desc(Review.review_date), Review.review_id)
        .limit(max(tool_input.limit * 5, tool_input.limit))
    ).all()

    positive_items_by_review_id = {
        item.review_id: item
        for item in [
            _build_positive_item(review, signal, tool_input.aspect) for review, signal in rows
        ]
        if item.positive_reasons
    }
    candidates = [
        build_candidate_from_review_signal(review, signal)
        for review, signal in rows
        if review.review_id in positive_items_by_review_id
    ]
    scored_items = score_review_evidence(
        candidates,
        _scoring_config(tool_input),
    )
    positive_items = [
        _with_score_metadata(
            positive_items_by_review_id[scored.candidate.review_id],
            scored.score,
            scored.matched_keywords,
        )
        for scored in scored_items
    ]

    restaurant_level_pros = restaurant_signal.pros if restaurant_signal else []
    top_pros = _most_common(
        [value for item in positive_items for value in item.pros] + restaurant_level_pros
    )
    top_evidence_terms = _most_common(
        [value for item in positive_items for value in item.evidence_terms]
    )
    status: Literal["ok", "empty"] = (
        "ok" if positive_items or top_pros or top_evidence_terms else "empty"
    )

    return PositiveReviewPatternsToolOutput(
        status=status,
        data=PositiveReviewPatternsData(
            business_id=tool_input.business_id,
            aspect=tool_input.aspect,
            total=len(positive_items),
            top_pros=top_pros,
            top_evidence_terms=top_evidence_terms,
            restaurant_level_pros=restaurant_level_pros,
            items=positive_items,
        ),
        data_sources=data_sources,
    )


def _build_positive_item(
    review: Review,
    signal: ReviewAspectSignal,
    aspect: AspectName | None,
) -> PositiveReviewEvidenceItem:
    selected_aspect_score = _selected_aspect_score(signal, aspect)
    positive_reasons = _positive_reasons(review, signal, selected_aspect_score)

    return PositiveReviewEvidenceItem(
        review_id=review.review_id,
        business_id=review.business_id,
        stars=review.stars,
        text=review.text,
        review_date=review.review_date,
        overall_sentiment_score=signal.overall_sentiment_score,
        overall_sentiment_label=signal.overall_sentiment_label,
        selected_aspect_score=selected_aspect_score,
        evidence_terms=signal.evidence_terms,
        pros=signal.pros,
        confidence=signal.confidence,
        positive_reasons=positive_reasons,
    )


def _selected_aspect_score(
    signal: ReviewAspectSignal,
    aspect: AspectName | None,
) -> float | None:
    if aspect is None:
        return None
    return getattr(signal, ASPECT_SCORE_FIELDS[aspect])


def _positive_reasons(
    review: Review,
    signal: ReviewAspectSignal,
    selected_aspect_score: float | None,
) -> list[str]:
    reasons = []
    if signal.overall_sentiment_label == "positive":
        reasons.append("positive sentiment label")
    if signal.overall_sentiment_score is not None and signal.overall_sentiment_score > 0.2:
        reasons.append("high sentiment score")
    if selected_aspect_score is not None and selected_aspect_score >= 4:
        reasons.append("high selected aspect score")
    if review.stars >= 4:
        reasons.append("high review stars")
    if signal.pros:
        reasons.append("contains pros")
    return reasons


def _most_common(values: list[str], limit: int = 8) -> list[str]:
    return [value for value, _ in Counter(values).most_common(limit)]


def _scoring_config(
    tool_input: PositiveReviewPatternsToolInput,
) -> ReviewEvidenceScoringConfig:
    aspect_weights = (
        {tool_input.aspect: 1.0}
        if tool_input.aspect is not None
        else {aspect: 1.0 for aspect in ASPECT_SCORE_FIELDS}
    )
    return ReviewEvidenceScoringConfig(
        aspect_weights=aspect_weights,
        aspect_direction="positive",
        positive_keywords=POSITIVE_KEYWORDS,
        sentiment_target="positive",
        star_preference="high",
        limit=tool_input.limit,
    )


def _with_score_metadata(
    item: PositiveReviewEvidenceItem,
    relevance_score: float,
    matched_keywords: list[str],
) -> PositiveReviewEvidenceItem:
    return item.model_copy(
        update={
            "relevance_score": relevance_score,
            "matched_keywords": matched_keywords,
        }
    )


@tool(
    "get_positive_review_patterns",
    args_schema=PositiveReviewPatternsToolInput,
    return_direct=False,
)
def get_positive_review_patterns_tool(
    business_id: str,
    aspect: AspectName | None = None,
    limit: int = 8,
) -> dict:
    """Aggregate common strengths and positive review evidence.

    Supported intents:
    - recommendation: worth_it
    - aspect: food, service, price, ambience
    - summary: summary

    Use this tool when an answer needs common strengths, positive themes, or
    representative positive reviews for the selected restaurant.

    Do not use this tool to fetch the restaurant profile, common complaints,
    risk warnings, generic review evidence, or recent trend summaries. Use
    `get_restaurant_profile`, `get_negative_review_patterns`,
    `get_review_aspect_evidence`, or `get_recent_review_trend` for those needs.

    Reads:
    - reviews.review_id, business_id, stars, text, review_date
    - review_aspect_signals overall sentiment fields, aspect scores,
      evidence_terms, pros, confidence
    - restaurant_aspect_signals pros

    Input:
    - business_id: required selected restaurant ID.
    - aspect: optional aspect focus.
    - limit: maximum number of representative positive evidence rows.

    Flow:
    1. Validate arguments through the LangChain args schema.
    2. Open a SQLAlchemy session using the configured application database.
    3. Load restaurant-level pros.
    4. Join `reviews` with `review_aspect_signals`.
    5. Identify positive review evidence from sentiment, high scores, high
       stars, and pros.
    6. Rank candidates with the shared review evidence scorer.
    7. Return top positive themes, evidence terms, and bounded representative
       positive reviews.

    Output:
    - tool_name: get_positive_review_patterns.
    - status: ok or empty.
    - data.top_pros: common positive themes.
    - data.top_evidence_terms: common positive evidence terms.
    - data.items: representative positive review evidence with relevance score
      and matched keywords.
    - data_sources: table and column metadata for traceability.
    - errors: recoverable tool errors, empty on success.

    This tool does not generate recommendations or natural-language answers.
    """

    with get_session_factory()() as session:
        result = get_positive_review_patterns(
            session,
            PositiveReviewPatternsToolInput(
                business_id=business_id,
                aspect=aspect,
                limit=limit,
            ),
        )
    return result.model_dump()
