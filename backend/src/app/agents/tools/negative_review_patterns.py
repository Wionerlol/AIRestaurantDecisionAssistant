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

NEGATIVE_REVIEW_COLUMNS = [
    "review_id",
    "business_id",
    "stars",
    "text",
    "review_date",
]

NEGATIVE_REVIEW_ASPECT_COLUMNS = [
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
    "cons",
    "risk_flags",
    "confidence",
]

NEGATIVE_RESTAURANT_ASPECT_COLUMNS = [
    "business_id",
    "cons",
    "risk_flags",
    "food_score",
    "service_score",
    "price_score",
    "ambience_score",
    "waiting_time_score",
    "updated_at",
]

NEGATIVE_KEYWORDS = [
    "bad",
    "slow",
    "rude",
    "expensive",
    "dirty",
    "crowded",
    "noisy",
    "long wait",
    "cold",
    "wrong order",
]


class NegativeReviewPatternsToolInput(BaseModel):
    """Input for `get_negative_review_patterns`."""

    business_id: str = Field(
        min_length=1,
        description="Selected Yelp restaurant business ID used to fetch negative patterns.",
    )
    aspect: AspectName | None = Field(
        default=None,
        description="Optional aspect focus for negative evidence.",
    )
    limit: int = Field(
        default=8,
        ge=1,
        le=50,
        description="Maximum number of representative negative review rows to return.",
    )


class NegativeReviewEvidenceItem(BaseModel):
    review_id: str
    business_id: str
    stars: float
    text: str
    review_date: datetime
    overall_sentiment_score: float | None = None
    overall_sentiment_label: str | None = None
    selected_aspect_score: float | None = None
    evidence_terms: list[str]
    cons: list[str]
    risk_flags: list[str]
    relevance_score: float | None = None
    matched_keywords: list[str] = Field(default_factory=list)
    confidence: float | None = None
    negative_reasons: list[str]


class NegativeReviewPatternsData(BaseModel):
    business_id: str
    aspect: AspectName | None = None
    total: int
    top_cons: list[str]
    top_risk_flags: list[str]
    top_evidence_terms: list[str]
    restaurant_level_cons: list[str]
    restaurant_level_risk_flags: list[str]
    items: list[NegativeReviewEvidenceItem]


class ToolDataSource(BaseModel):
    table: str
    columns: list[str]


class NegativeReviewPatternsToolOutput(BaseModel):
    tool_name: Literal["get_negative_review_patterns"] = "get_negative_review_patterns"
    status: Literal["ok", "empty"]
    data: NegativeReviewPatternsData
    data_sources: list[ToolDataSource]
    errors: list[str] = Field(default_factory=list)


def get_negative_review_patterns(
    session: Session,
    tool_input: NegativeReviewPatternsToolInput,
) -> NegativeReviewPatternsToolOutput:
    """Aggregate common complaints, risks, and negative review evidence.

    Supported intents:
    - recommendation: worth_it, should_go
    - aspect: service
    - scenario: date, family
    - risk: complaints, warnings
    - summary: summary

    Use this tool when an answer needs common complaints, watch-outs, risk
    flags, or representative negative reviews for the selected restaurant. This
    tool is especially important for yes/no decision answers because it exposes
    downside evidence before the final answer is generated.

    Do not use this tool to fetch the restaurant profile, positive strengths,
    generic review evidence, or recent trend summaries. Use
    `get_restaurant_profile`, `get_positive_review_patterns`,
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
    - review_aspect_signals.cons
    - review_aspect_signals.risk_flags
    - review_aspect_signals.confidence
    - restaurant_aspect_signals.cons
    - restaurant_aspect_signals.risk_flags

    Input:
    - business_id: required selected restaurant ID.
    - aspect: optional aspect focus.
    - limit: maximum number of representative negative evidence rows.

    Flow:
    1. Validate input through `NegativeReviewPatternsToolInput`.
    2. Load restaurant-level cons and risk flags from
       `restaurant_aspect_signals`.
    3. Join `reviews` to `review_aspect_signals` by `review_id`.
    4. Restrict rows to the selected `business_id`.
    5. Identify negative evidence in Python using any of these signals:
       negative sentiment label, low overall sentiment score, low selected
       aspect score, low Yelp stars, non-empty cons, or non-empty risk flags.
    6. Rank representative reviews with the shared review evidence scorer using
       negative keywords, negative sentiment, low aspect scores, confidence,
       recency, and low stars.
    7. Aggregate top cons, risk flags, and evidence terms from review-level and
       restaurant-level signals.

    Output:
    - status: `ok` when negative patterns or evidence exist, otherwise `empty`.
    - data.top_cons: most common negative themes.
    - data.top_risk_flags: most common risk flags.
    - data.top_evidence_terms: common negative evidence terms.
    - data.items: representative negative review evidence with relevance score
      and matched keywords.
    - data_sources: table and column metadata for traceability.
    - errors: recoverable tool errors, empty on success.

    This tool does not generate recommendations or natural-language answers.
    """

    data_sources = [
        ToolDataSource(table="reviews", columns=NEGATIVE_REVIEW_COLUMNS),
        ToolDataSource(
            table="review_aspect_signals",
            columns=NEGATIVE_REVIEW_ASPECT_COLUMNS,
        ),
        ToolDataSource(
            table="restaurant_aspect_signals",
            columns=NEGATIVE_RESTAURANT_ASPECT_COLUMNS,
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

    negative_items_by_review_id = {
        item.review_id: item
        for item in [
            _build_negative_item(review, signal, tool_input.aspect) for review, signal in rows
        ]
        if item.negative_reasons
    }
    candidates = [
        build_candidate_from_review_signal(review, signal)
        for review, signal in rows
        if review.review_id in negative_items_by_review_id
    ]
    scored_items = score_review_evidence(
        candidates,
        _scoring_config(tool_input),
    )
    negative_items = [
        _with_score_metadata(
            negative_items_by_review_id[scored.candidate.review_id],
            scored.score,
            scored.matched_keywords,
        )
        for scored in scored_items
    ]

    restaurant_level_cons = restaurant_signal.cons if restaurant_signal else []
    restaurant_level_risk_flags = restaurant_signal.risk_flags if restaurant_signal else []
    top_cons = _most_common(
        [value for item in negative_items for value in item.cons] + restaurant_level_cons
    )
    top_risk_flags = _most_common(
        [value for item in negative_items for value in item.risk_flags]
        + restaurant_level_risk_flags
    )
    top_evidence_terms = _most_common(
        [value for item in negative_items for value in item.evidence_terms]
    )
    status: Literal["ok", "empty"] = (
        "ok" if negative_items or top_cons or top_risk_flags or top_evidence_terms else "empty"
    )

    return NegativeReviewPatternsToolOutput(
        status=status,
        data=NegativeReviewPatternsData(
            business_id=tool_input.business_id,
            aspect=tool_input.aspect,
            total=len(negative_items),
            top_cons=top_cons,
            top_risk_flags=top_risk_flags,
            top_evidence_terms=top_evidence_terms,
            restaurant_level_cons=restaurant_level_cons,
            restaurant_level_risk_flags=restaurant_level_risk_flags,
            items=negative_items,
        ),
        data_sources=data_sources,
    )


def _build_negative_item(
    review: Review,
    signal: ReviewAspectSignal,
    aspect: AspectName | None,
) -> NegativeReviewEvidenceItem:
    selected_aspect_score = _selected_aspect_score(signal, aspect)
    negative_reasons = _negative_reasons(review, signal, selected_aspect_score)

    return NegativeReviewEvidenceItem(
        review_id=review.review_id,
        business_id=review.business_id,
        stars=review.stars,
        text=review.text,
        review_date=review.review_date,
        overall_sentiment_score=signal.overall_sentiment_score,
        overall_sentiment_label=signal.overall_sentiment_label,
        selected_aspect_score=selected_aspect_score,
        evidence_terms=signal.evidence_terms,
        cons=signal.cons,
        risk_flags=signal.risk_flags,
        confidence=signal.confidence,
        negative_reasons=negative_reasons,
    )


def _selected_aspect_score(
    signal: ReviewAspectSignal,
    aspect: AspectName | None,
) -> float | None:
    if aspect is None:
        return None
    return getattr(signal, ASPECT_SCORE_FIELDS[aspect])


def _negative_reasons(
    review: Review,
    signal: ReviewAspectSignal,
    selected_aspect_score: float | None,
) -> list[str]:
    reasons = []
    if signal.overall_sentiment_label == "negative":
        reasons.append("negative sentiment label")
    if signal.overall_sentiment_score is not None and signal.overall_sentiment_score < -0.2:
        reasons.append("low sentiment score")
    if selected_aspect_score is not None and selected_aspect_score < 2.5:
        reasons.append("low selected aspect score")
    if review.stars <= 2:
        reasons.append("low review stars")
    if signal.cons:
        reasons.append("contains cons")
    if signal.risk_flags:
        reasons.append("contains risk flags")
    return reasons


def _most_common(values: list[str], limit: int = 8) -> list[str]:
    return [value for value, _ in Counter(values).most_common(limit)]


def _scoring_config(
    tool_input: NegativeReviewPatternsToolInput,
) -> ReviewEvidenceScoringConfig:
    aspect_weights = (
        {tool_input.aspect: 1.0}
        if tool_input.aspect is not None
        else {aspect: 1.0 for aspect in ASPECT_SCORE_FIELDS}
    )
    return ReviewEvidenceScoringConfig(
        aspect_weights=aspect_weights,
        aspect_direction="negative",
        negative_keywords=NEGATIVE_KEYWORDS,
        sentiment_target="negative",
        star_preference="low",
        limit=tool_input.limit,
    )


def _with_score_metadata(
    item: NegativeReviewEvidenceItem,
    relevance_score: float,
    matched_keywords: list[str],
) -> NegativeReviewEvidenceItem:
    return item.model_copy(
        update={
            "relevance_score": relevance_score,
            "matched_keywords": matched_keywords,
        }
    )


@tool(
    "get_negative_review_patterns",
    args_schema=NegativeReviewPatternsToolInput,
    return_direct=False,
)
def get_negative_review_patterns_tool(
    business_id: str,
    aspect: AspectName | None = None,
    limit: int = 8,
) -> dict:
    """Aggregate common complaints, risks, and negative review evidence.

    Supported intents:
    - recommendation: worth_it, should_go
    - aspect: service
    - scenario: date, family
    - risk: complaints, warnings
    - summary: summary

    Use this tool when an answer needs common complaints, watch-outs, risk
    flags, or representative negative reviews for the selected restaurant.

    Do not use this tool to fetch the restaurant profile, positive strengths,
    generic review evidence, or recent trend summaries. Use
    `get_restaurant_profile`, `get_positive_review_patterns`,
    `get_review_aspect_evidence`, or `get_recent_review_trend` for those needs.

    Reads:
    - reviews.review_id, business_id, stars, text, review_date
    - review_aspect_signals overall sentiment fields, aspect scores,
      evidence_terms, cons, risk_flags, confidence
    - restaurant_aspect_signals cons and risk_flags

    Input:
    - business_id: required selected restaurant ID.
    - aspect: optional aspect focus.
    - limit: maximum number of representative negative evidence rows.

    Flow:
    1. Validate arguments through the LangChain args schema.
    2. Open a SQLAlchemy session using the configured application database.
    3. Load restaurant-level cons and risk flags.
    4. Join `reviews` with `review_aspect_signals`.
    5. Identify negative review evidence from sentiment, low scores, low stars,
       cons, and risk flags.
    6. Rank candidates with the shared review evidence scorer.
    7. Return top complaint themes, risk flags, evidence terms, and bounded
       representative negative reviews.

    Output:
    - tool_name: get_negative_review_patterns.
    - status: ok or empty.
    - data.top_cons: common negative themes.
    - data.top_risk_flags: common risk flags.
    - data.top_evidence_terms: common negative evidence terms.
    - data.items: representative negative review evidence with relevance score
      and matched keywords.
    - data_sources: table and column metadata for traceability.
    - errors: recoverable tool errors, empty on success.

    This tool does not generate recommendations or natural-language answers.
    """

    with get_session_factory()() as session:
        result = get_negative_review_patterns(
            session,
            NegativeReviewPatternsToolInput(
                business_id=business_id,
                aspect=aspect,
                limit=limit,
            ),
        )
    return result.model_dump()
