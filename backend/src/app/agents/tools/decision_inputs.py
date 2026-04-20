from __future__ import annotations

from collections import Counter
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Restaurant, RestaurantAspectSignal, ReviewAspectSignal
from app.db.session import get_session_factory


DecisionIntentLabel = Literal["worth_it", "should_go"]
DecisionLabel = Literal[
    "worth_it",
    "worth_considering",
    "not_worth_it",
    "should_go",
    "consider_with_caution",
    "skip",
    "insufficient_data",
]

ASPECT_SCORE_FIELDS: dict[str, str] = {
    "food": "food_score",
    "service": "service_score",
    "price": "price_score",
    "ambience": "ambience_score",
    "waiting_time": "waiting_time_score",
}

DECISION_INPUT_RESTAURANT_COLUMNS = [
    "business_id",
    "name",
    "city",
    "state",
    "stars",
    "review_count",
    "is_open",
    "categories",
]

DECISION_INPUT_RESTAURANT_ASPECT_COLUMNS = [
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

DECISION_INPUT_REVIEW_ASPECT_COLUMNS = [
    "review_id",
    "business_id",
    "overall_sentiment_score",
    "overall_sentiment_label",
    "food_score",
    "service_score",
    "price_score",
    "ambience_score",
    "waiting_time_score",
    "pros",
    "cons",
    "risk_flags",
    "confidence",
]


class DecisionInputsToolInput(BaseModel):
    """Input for `get_decision_inputs`."""

    business_id: str = Field(
        min_length=1,
        description="Selected Yelp restaurant business ID used to build decision context.",
    )
    intent_label: DecisionIntentLabel = Field(
        description="Recommendation intent to normalize for: worth_it or should_go.",
    )


class DecisionRestaurantSnapshot(BaseModel):
    business_id: str
    name: str
    city: str
    state: str
    stars: float | None
    review_count: int
    is_open: int | None
    categories: list[str]


class DecisionEvidenceCoverage(BaseModel):
    has_profile: bool
    has_restaurant_aspect_summary: bool
    review_signal_count: int
    has_review_sentiment: bool
    has_review_strengths: bool
    has_review_weaknesses: bool
    has_risk_flags: bool


class DecisionInputsData(BaseModel):
    business_id: str
    intent_label: DecisionIntentLabel
    restaurant: DecisionRestaurantSnapshot
    decision_score: float | None
    decision_label: DecisionLabel
    base_rating: float | None
    overall_rating: float | None
    aspect_scores: dict[str, float | None]
    average_aspect_score: float | None
    average_sentiment_score: float | None
    sentiment_label_counts: dict[str, int]
    average_confidence: float | None
    strengths: list[str]
    weaknesses: list[str]
    risk_flags: list[str]
    penalties: dict[str, float]
    coverage: DecisionEvidenceCoverage


class ToolDataSource(BaseModel):
    table: str
    columns: list[str]


class DecisionInputsToolOutput(BaseModel):
    tool_name: Literal["get_decision_inputs"] = "get_decision_inputs"
    status: Literal["ok", "not_found"]
    data: DecisionInputsData | None
    data_sources: list[ToolDataSource]
    errors: list[str] = Field(default_factory=list)


def get_decision_inputs(
    session: Session,
    tool_input: DecisionInputsToolInput,
) -> DecisionInputsToolOutput:
    """Build normalized decision context for recommendation-style answers.

    Supported intents:
    - recommendation: worth_it, should_go

    Use this tool after profile, aspect summary, and positive/negative evidence
    tools have been selected for a final recommendation workflow. This tool
    reads the same canonical tables directly and produces a compact,
    answer-ready decision input object: score, label, strengths, weaknesses,
    risks, and coverage. It is intended to help the final LLM answer make a
    grounded yes/no or worth-it judgment without re-parsing raw database rows.

    Do not use this tool for aspect-only questions, scenario fit checks, generic
    review evidence retrieval, complaint-only answers, recent trend summaries,
    or unsupported questions. Use the more specific evidence tools for those
    needs.

    Reads:
    - restaurants profile fields for identity, rating, review volume, open flag,
      and categories.
    - restaurant_aspect_signals overall rating, aspect scores, pros, cons, and
      risk flags.
    - review_aspect_signals sentiment labels/scores, aspect scores, pros, cons,
      risk flags, and confidence.

    Input:
    - business_id: required selected restaurant ID.
    - intent_label: worth_it or should_go.

    Flow:
    1. Validate `business_id` and `intent_label`.
    2. Load the selected restaurant profile. Missing profile returns
       `status="not_found"` because final recommendation context cannot be
       grounded.
    3. Load the restaurant-level aspect summary when available.
    4. Load all review-level aspect signals for the restaurant.
    5. Resolve each aspect score from restaurant-level score first, with
       review-level average fallback.
    6. Aggregate top strengths, weaknesses, risk flags, sentiment counts, and
       average confidence.
    7. Compute a deterministic 0-5 decision score from base rating, aspect
       average, normalized sentiment, and bounded penalties for risks,
       weaknesses, and closed restaurants.
    8. Convert the score into an intent-specific label for final answer
       generation.

    Output:
    - status: ok or not_found.
    - data.decision_score: deterministic 0-5 recommendation score.
    - data.decision_label: intent-specific recommendation label.
    - data.strengths, weaknesses, risk_flags: compact evidence themes.
    - data.coverage: which evidence types were available.
    - data_sources: table and column metadata for traceability.
    - errors: recoverable tool errors, empty on success.

    This tool does not generate recommendations or natural-language answers.
    """

    data_sources = [
        ToolDataSource(table="restaurants", columns=DECISION_INPUT_RESTAURANT_COLUMNS),
        ToolDataSource(
            table="restaurant_aspect_signals",
            columns=DECISION_INPUT_RESTAURANT_ASPECT_COLUMNS,
        ),
        ToolDataSource(
            table="review_aspect_signals",
            columns=DECISION_INPUT_REVIEW_ASPECT_COLUMNS,
        ),
    ]
    restaurant = session.get(Restaurant, tool_input.business_id)
    if restaurant is None:
        return DecisionInputsToolOutput(
            status="not_found",
            data=None,
            data_sources=data_sources,
            errors=[f"Restaurant not found: {tool_input.business_id}"],
        )

    restaurant_signal = session.get(RestaurantAspectSignal, tool_input.business_id)
    review_signals = session.scalars(
        select(ReviewAspectSignal).where(ReviewAspectSignal.business_id == tool_input.business_id)
    ).all()

    aspect_scores = _resolve_aspect_scores(restaurant_signal, review_signals)
    average_aspect_score = _average(list(aspect_scores.values()))
    average_sentiment_score = _average(
        [signal.overall_sentiment_score for signal in review_signals]
    )
    average_confidence = _average([signal.confidence for signal in review_signals])
    sentiment_label_counts = dict(
        Counter(
            signal.overall_sentiment_label
            for signal in review_signals
            if signal.overall_sentiment_label
        )
    )
    strengths = _top_values(
        (restaurant_signal.pros if restaurant_signal else [])
        + [value for signal in review_signals for value in signal.pros]
    )
    weaknesses = _top_values(
        (restaurant_signal.cons if restaurant_signal else [])
        + [value for signal in review_signals for value in signal.cons]
    )
    risk_flags = _top_values(
        (restaurant_signal.risk_flags if restaurant_signal else [])
        + [value for signal in review_signals for value in signal.risk_flags]
    )
    base_rating = restaurant.stars
    overall_rating = restaurant_signal.overall_rating if restaurant_signal else None
    decision_score, penalties = _decision_score(
        base_rating=base_rating,
        overall_rating=overall_rating,
        average_aspect_score=average_aspect_score,
        average_sentiment_score=average_sentiment_score,
        risk_flags=risk_flags,
        weaknesses=weaknesses,
        is_open=restaurant.is_open,
        intent_label=tool_input.intent_label,
    )

    return DecisionInputsToolOutput(
        status="ok",
        data=DecisionInputsData(
            business_id=restaurant.business_id,
            intent_label=tool_input.intent_label,
            restaurant=DecisionRestaurantSnapshot(
                business_id=restaurant.business_id,
                name=restaurant.name,
                city=restaurant.city,
                state=restaurant.state,
                stars=restaurant.stars,
                review_count=restaurant.review_count,
                is_open=restaurant.is_open,
                categories=restaurant.categories,
            ),
            decision_score=decision_score,
            decision_label=_decision_label(tool_input.intent_label, decision_score),
            base_rating=base_rating,
            overall_rating=overall_rating,
            aspect_scores=aspect_scores,
            average_aspect_score=average_aspect_score,
            average_sentiment_score=average_sentiment_score,
            sentiment_label_counts=sentiment_label_counts,
            average_confidence=average_confidence,
            strengths=strengths,
            weaknesses=weaknesses,
            risk_flags=risk_flags,
            penalties=penalties,
            coverage=DecisionEvidenceCoverage(
                has_profile=True,
                has_restaurant_aspect_summary=restaurant_signal is not None,
                review_signal_count=len(review_signals),
                has_review_sentiment=average_sentiment_score is not None
                or bool(sentiment_label_counts),
                has_review_strengths=bool(strengths),
                has_review_weaknesses=bool(weaknesses),
                has_risk_flags=bool(risk_flags),
            ),
        ),
        data_sources=data_sources,
    )


def _resolve_aspect_scores(
    restaurant_signal: RestaurantAspectSignal | None,
    review_signals: list[ReviewAspectSignal],
) -> dict[str, float | None]:
    resolved_scores = {}
    for aspect, field_name in ASPECT_SCORE_FIELDS.items():
        score = getattr(restaurant_signal, field_name) if restaurant_signal else None
        if score is None:
            score = _average(
                [
                    getattr(signal, field_name)
                    for signal in review_signals
                    if getattr(signal, field_name) is not None
                ]
            )
        resolved_scores[aspect] = score
    return resolved_scores


def _decision_score(
    *,
    base_rating: float | None,
    overall_rating: float | None,
    average_aspect_score: float | None,
    average_sentiment_score: float | None,
    risk_flags: list[str],
    weaknesses: list[str],
    is_open: int | None,
    intent_label: DecisionIntentLabel,
) -> tuple[float | None, dict[str, float]]:
    score_inputs = [
        (overall_rating if overall_rating is not None else base_rating, 0.35),
        (average_aspect_score, 0.40),
        (_sentiment_to_rating(average_sentiment_score), 0.25),
    ]
    weighted_values = [
        (value * weight, weight) for value, weight in score_inputs if value is not None
    ]
    if not weighted_values:
        return None, {}

    base_score = sum(value for value, _ in weighted_values) / sum(
        weight for _, weight in weighted_values
    )
    risk_penalty = min(0.75, len(risk_flags) * 0.15)
    weakness_penalty = min(0.4, len(weaknesses) * 0.08)
    closed_penalty = 1.0 if is_open == 0 else 0.0
    intent_risk_multiplier = 1.15 if intent_label == "should_go" else 1.0
    penalties = {
        "risk_flags": round(risk_penalty * intent_risk_multiplier, 3),
        "weaknesses": round(weakness_penalty * intent_risk_multiplier, 3),
        "closed": closed_penalty,
    }
    final_score = max(0.0, base_score - sum(penalties.values()))
    return round(final_score, 3), penalties


def _decision_label(
    intent_label: DecisionIntentLabel,
    decision_score: float | None,
) -> DecisionLabel:
    if decision_score is None:
        return "insufficient_data"
    if intent_label == "worth_it":
        if decision_score >= 4:
            return "worth_it"
        if decision_score >= 3:
            return "worth_considering"
        return "not_worth_it"
    if decision_score >= 4:
        return "should_go"
    if decision_score >= 3:
        return "consider_with_caution"
    return "skip"


def _sentiment_to_rating(sentiment_score: float | None) -> float | None:
    if sentiment_score is None:
        return None
    return round((max(-1.0, min(1.0, sentiment_score)) + 1.0) * 2.5, 3)


def _average(values: list[float | None]) -> float | None:
    clean_values = [value for value in values if value is not None]
    if not clean_values:
        return None
    return round(sum(clean_values) / len(clean_values), 3)


def _top_values(values: list[str], limit: int = 8) -> list[str]:
    return [value for value, _ in Counter(values).most_common(limit)]


@tool(
    "get_decision_inputs",
    args_schema=DecisionInputsToolInput,
    return_direct=False,
)
def get_decision_inputs_tool(
    business_id: str,
    intent_label: DecisionIntentLabel,
) -> dict:
    """Build normalized decision context for recommendation-style answers.

    Supported intents:
    - recommendation: worth_it, should_go

    Use this tool when the final answer needs a compact recommendation input
    package for "is it worth it" or "should I go" questions. It combines profile
    facts, restaurant-level aspect summary, review-level sentiment, strengths,
    weaknesses, and risks into a deterministic score and label.

    Do not use this tool for aspect-only questions, scenario fit checks, generic
    review evidence retrieval, complaint-only answers, recent trend summaries,
    or unsupported questions.

    Reads:
    - restaurants profile fields.
    - restaurant_aspect_signals overall rating, aspect scores, pros, cons, and
      risk flags.
    - review_aspect_signals sentiment, aspect scores, pros, cons, risk flags,
      and confidence.

    Input:
    - business_id: required selected restaurant ID.
    - intent_label: worth_it or should_go.

    Flow:
    1. Open a SQLAlchemy session using the configured application database.
    2. Load profile, restaurant-level aspect summary, and review-level signals.
    3. Resolve aspect scores with restaurant-level priority and review fallback.
    4. Aggregate strengths, weaknesses, risks, sentiment, and confidence.
    5. Compute an intent-specific deterministic decision score and label.
    6. Return normalized context and source metadata.

    Output:
    - tool_name: get_decision_inputs.
    - status: ok or not_found.
    - data.decision_score and data.decision_label.
    - data.strengths, weaknesses, risk_flags.
    - data.aspect_scores and sentiment summaries.
    - data.coverage.
    - data_sources: table and column metadata for traceability.
    - errors: recoverable tool errors, empty on success.

    This tool does not generate recommendations or natural-language answers.
    """

    with get_session_factory()() as session:
        result = get_decision_inputs(
            session,
            DecisionInputsToolInput(
                business_id=business_id,
                intent_label=intent_label,
            ),
        )
    return result.model_dump()
