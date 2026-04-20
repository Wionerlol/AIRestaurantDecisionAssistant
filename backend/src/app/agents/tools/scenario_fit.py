from __future__ import annotations

from collections import Counter
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.agents.tools.review_evidence_scoring import (
    ReviewEvidenceCandidate,
    ReviewEvidenceScoringConfig,
    ScoredReviewEvidence,
    build_candidate_from_review_signal,
    score_review_evidence,
)
from app.db.models import RestaurantAspectSignal, Review, ReviewAspectSignal
from app.db.session import get_session_factory


ScenarioName = Literal["date", "family", "quick_meal"]
FitLabel = Literal["good_fit", "mixed_fit", "poor_fit", "insufficient_data"]

ASPECT_SCORE_FIELDS: dict[str, str] = {
    "food": "food_score",
    "service": "service_score",
    "price": "price_score",
    "ambience": "ambience_score",
    "waiting_time": "waiting_time_score",
}

SCENARIO_FIT_RESTAURANT_COLUMNS = [
    "business_id",
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

SCENARIO_FIT_REVIEW_COLUMNS = [
    "review_id",
    "business_id",
    "stars",
    "text",
    "review_date",
]

SCENARIO_FIT_REVIEW_ASPECT_COLUMNS = [
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
    "confidence",
]


class ScenarioConfig(BaseModel):
    weights: dict[str, float]
    positive_keywords: list[str]
    negative_keywords: list[str]
    risk_keywords: list[str]


SCENARIO_CONFIGS: dict[ScenarioName, ScenarioConfig] = {
    "date": ScenarioConfig(
        weights={
            "ambience": 0.35,
            "service": 0.20,
            "waiting_time": 0.15,
            "price": 0.15,
            "food": 0.15,
        },
        positive_keywords=[
            "romantic",
            "cozy",
            "quiet",
            "ambience",
            "atmosphere",
            "vibe",
            "intimate",
            "date",
            "anniversary",
            "nice service",
        ],
        negative_keywords=[
            "noisy",
            "loud",
            "crowded",
            "long wait",
            "rude",
            "expensive",
            "rushed",
            "dirty",
        ],
        risk_keywords=["noisy", "crowded", "long wait", "rude", "expensive"],
    ),
    "family": ScenarioConfig(
        weights={
            "service": 0.25,
            "ambience": 0.25,
            "waiting_time": 0.20,
            "price": 0.15,
            "food": 0.15,
        },
        positive_keywords=[
            "family",
            "kids",
            "children",
            "friendly",
            "spacious",
            "comfortable",
            "quick service",
            "reasonable price",
        ],
        negative_keywords=[
            "not kid friendly",
            "small",
            "cramped",
            "long wait",
            "noisy",
            "expensive",
            "rude",
        ],
        risk_keywords=["not kid friendly", "cramped", "long wait", "noisy", "expensive"],
    ),
    "quick_meal": ScenarioConfig(
        weights={
            "waiting_time": 0.40,
            "service": 0.25,
            "price": 0.20,
            "food": 0.15,
        },
        positive_keywords=[
            "quick",
            "fast",
            "takeout",
            "take-out",
            "short wait",
            "efficient",
            "lunch",
            "grab",
            "casual",
        ],
        negative_keywords=[
            "slow",
            "long wait",
            "queue",
            "crowded",
            "late",
            "wrong order",
            "rude",
        ],
        risk_keywords=["slow", "long wait", "queue", "crowded", "wrong order"],
    ),
}


class ScenarioFitToolInput(BaseModel):
    """Input for `get_scenario_fit`."""

    business_id: str = Field(
        min_length=1,
        description="Selected Yelp restaurant business ID used to compute scenario fit.",
    )
    scenario: ScenarioName = Field(
        description="Scenario to evaluate: date, family, or quick_meal.",
    )
    evidence_limit: int = Field(
        default=4,
        ge=1,
        le=20,
        description="Maximum positive and negative evidence rows to return per side.",
    )


class ScenarioEvidenceItem(BaseModel):
    review_id: str
    text: str
    stars: float
    relevance_score: float
    matched_keywords: list[str]
    evidence_terms: list[str]
    pros: list[str]
    cons: list[str]
    risk_flags: list[str]


class ScenarioFitCoverage(BaseModel):
    used_restaurant_aspect_summary: bool
    used_review_aspect_fallback: bool
    review_evidence_count: int


class ScenarioFitData(BaseModel):
    business_id: str
    scenario: ScenarioName
    fit_score: float | None
    fit_label: FitLabel
    aspect_scores: dict[str, float | None]
    weights: dict[str, float]
    risk_penalty: float
    supporting_reasons: list[str]
    opposing_reasons: list[str]
    risk_flags: list[str]
    positive_evidence: list[ScenarioEvidenceItem]
    negative_evidence: list[ScenarioEvidenceItem]
    coverage: ScenarioFitCoverage


class ToolDataSource(BaseModel):
    table: str
    columns: list[str]


class ScenarioFitToolOutput(BaseModel):
    tool_name: Literal["get_scenario_fit"] = "get_scenario_fit"
    status: Literal["ok", "empty"]
    data: ScenarioFitData
    data_sources: list[ToolDataSource]
    errors: list[str] = Field(default_factory=list)


def get_scenario_fit(
    session: Session,
    tool_input: ScenarioFitToolInput,
) -> ScenarioFitToolOutput:
    """Compute deterministic scenario fit from aspect scores and review evidence.

    Supported intents:
    - scenario: date, family, quick_meal

    Use this tool when the user asks whether the selected restaurant is suitable
    for a concrete usage scenario. The tool maps a scenario to weighted aspect
    scores, finds positive and negative review evidence with the shared review
    evidence scorer, applies a simple risk penalty, and returns a structured fit
    result.

    Do not use this tool for generic restaurant profile data, open-ended review
    search, broad positive/negative pattern summaries, or recent trend analysis.
    Use `get_restaurant_profile`, `get_review_aspect_evidence`,
    `get_positive_review_patterns`, `get_negative_review_patterns`, or
    `get_recent_review_trend` for those needs.

    Reads:
    - restaurant_aspect_signals scenario-specific aspect scores, pros, cons,
      risk_flags, updated_at
    - reviews.review_id, business_id, stars, text, review_date
    - review_aspect_signals overall sentiment, aspect scores, aspect_sentiments,
      evidence_terms, pros, cons, risk_flags, confidence

    Input:
    - business_id: required selected restaurant ID.
    - scenario: date, family, or quick_meal.
    - evidence_limit: maximum positive and negative evidence rows per side.

    Flow:
    1. Select fixed scenario config: aspect weights, positive keywords,
       negative keywords, and risk keywords.
    2. Load restaurant-level aspect summary for the selected restaurant.
    3. Load joined review and review_aspect_signals candidates.
    4. Resolve each scenario aspect score from restaurant-level score first;
       fall back to review-level average when restaurant-level score is missing.
    5. Compute weighted scenario fit score on a 0-5 scale.
    6. Use shared scorer twice to select positive and negative scenario evidence.
    7. Apply capped risk penalty from relevant risk flags.
    8. Return fit label, reasons, risks, evidence, and coverage metadata.

    Output:
    - status: ok or empty.
    - data.fit_score: final 0-5 scenario score after risk penalty.
    - data.fit_label: good_fit, mixed_fit, poor_fit, or insufficient_data.
    - data.aspect_scores: resolved scenario aspect scores.
    - data.positive_evidence and data.negative_evidence: ranked review evidence.
    - data.coverage: whether restaurant summary and review fallback were used.
    - data_sources: table and column metadata for traceability.

    This tool does not generate recommendations or natural-language answers.
    """

    config = SCENARIO_CONFIGS[tool_input.scenario]
    data_sources = [
        ToolDataSource(
            table="restaurant_aspect_signals",
            columns=SCENARIO_FIT_RESTAURANT_COLUMNS,
        ),
        ToolDataSource(table="reviews", columns=SCENARIO_FIT_REVIEW_COLUMNS),
        ToolDataSource(
            table="review_aspect_signals",
            columns=SCENARIO_FIT_REVIEW_ASPECT_COLUMNS,
        ),
    ]
    restaurant_signal = session.get(RestaurantAspectSignal, tool_input.business_id)
    rows = session.execute(
        select(Review, ReviewAspectSignal)
        .join(ReviewAspectSignal, Review.review_id == ReviewAspectSignal.review_id)
        .where(Review.business_id == tool_input.business_id)
        .order_by(desc(Review.review_date), Review.review_id)
        .limit(max(tool_input.evidence_limit * 8, tool_input.evidence_limit))
    ).all()
    candidates = [build_candidate_from_review_signal(review, signal) for review, signal in rows]
    aspect_scores, used_review_fallback = _resolve_aspect_scores(
        restaurant_signal,
        candidates,
        config.weights,
    )
    base_score = _weighted_score(aspect_scores, config.weights)
    risk_flags = _relevant_risk_flags(restaurant_signal, candidates, config.risk_keywords)
    risk_penalty = min(0.6, len(risk_flags) * 0.15)
    fit_score = None if base_score is None else round(max(0.0, base_score - risk_penalty), 3)

    positive_evidence = _scenario_evidence(
        candidates,
        config,
        direction="positive",
        limit=tool_input.evidence_limit,
    )
    negative_evidence = _scenario_evidence(
        candidates,
        config,
        direction="negative",
        limit=tool_input.evidence_limit,
    )
    status: Literal["ok", "empty"] = "ok" if restaurant_signal or candidates else "empty"

    return ScenarioFitToolOutput(
        status=status,
        data=ScenarioFitData(
            business_id=tool_input.business_id,
            scenario=tool_input.scenario,
            fit_score=fit_score,
            fit_label=_fit_label(fit_score),
            aspect_scores=aspect_scores,
            weights=config.weights,
            risk_penalty=risk_penalty,
            supporting_reasons=_supporting_reasons(aspect_scores, positive_evidence),
            opposing_reasons=_opposing_reasons(aspect_scores, risk_flags, negative_evidence),
            risk_flags=risk_flags,
            positive_evidence=positive_evidence,
            negative_evidence=negative_evidence,
            coverage=ScenarioFitCoverage(
                used_restaurant_aspect_summary=restaurant_signal is not None,
                used_review_aspect_fallback=used_review_fallback,
                review_evidence_count=len(candidates),
            ),
        ),
        data_sources=data_sources,
    )


def _resolve_aspect_scores(
    restaurant_signal: RestaurantAspectSignal | None,
    candidates: list[ReviewEvidenceCandidate],
    weights: dict[str, float],
) -> tuple[dict[str, float | None], bool]:
    resolved_scores = {}
    used_review_fallback = False

    for aspect in weights:
        score = (
            getattr(restaurant_signal, ASPECT_SCORE_FIELDS[aspect])
            if restaurant_signal is not None
            else None
        )
        if score is None:
            score = _average(
                [
                    candidate.aspect_scores.get(aspect)
                    for candidate in candidates
                    if candidate.aspect_scores.get(aspect) is not None
                ]
            )
            used_review_fallback = used_review_fallback or score is not None
        resolved_scores[aspect] = score

    return resolved_scores, used_review_fallback


def _weighted_score(
    aspect_scores: dict[str, float | None],
    weights: dict[str, float],
) -> float | None:
    weighted_values = []
    total_weight = 0.0
    for aspect, weight in weights.items():
        score = aspect_scores.get(aspect)
        if score is None:
            continue
        weighted_values.append(score * weight)
        total_weight += weight
    if total_weight <= 0:
        return None
    return round(sum(weighted_values) / total_weight, 3)


def _scenario_evidence(
    candidates: list[ReviewEvidenceCandidate],
    config: ScenarioConfig,
    direction: Literal["positive", "negative"],
    limit: int,
) -> list[ScenarioEvidenceItem]:
    if direction == "positive":
        scoring_config = ReviewEvidenceScoringConfig(
            aspect_weights=config.weights,
            aspect_direction="positive",
            positive_keywords=config.positive_keywords,
            sentiment_target="positive",
            star_preference="high",
            limit=limit,
        )
    else:
        scoring_config = ReviewEvidenceScoringConfig(
            aspect_weights=config.weights,
            aspect_direction="negative",
            negative_keywords=config.negative_keywords,
            sentiment_target="negative",
            star_preference="low",
            limit=limit,
        )

    return [_to_evidence_item(item) for item in score_review_evidence(candidates, scoring_config)]


def _to_evidence_item(scored: ScoredReviewEvidence) -> ScenarioEvidenceItem:
    candidate = scored.candidate
    return ScenarioEvidenceItem(
        review_id=candidate.review_id,
        text=candidate.text,
        stars=candidate.stars,
        relevance_score=scored.score,
        matched_keywords=scored.matched_keywords,
        evidence_terms=candidate.evidence_terms,
        pros=candidate.pros,
        cons=candidate.cons,
        risk_flags=candidate.risk_flags,
    )


def _relevant_risk_flags(
    restaurant_signal: RestaurantAspectSignal | None,
    candidates: list[ReviewEvidenceCandidate],
    risk_keywords: list[str],
) -> list[str]:
    all_flags = []
    if restaurant_signal is not None:
        all_flags.extend(restaurant_signal.risk_flags)
    for candidate in candidates:
        all_flags.extend(candidate.risk_flags)

    normalized_keywords = [keyword.lower() for keyword in risk_keywords]
    relevant_flags = [
        flag
        for flag in all_flags
        if any(keyword in flag.lower() for keyword in normalized_keywords)
    ]
    return [flag for flag, _ in Counter(relevant_flags).most_common(8)]


def _supporting_reasons(
    aspect_scores: dict[str, float | None],
    positive_evidence: list[ScenarioEvidenceItem],
) -> list[str]:
    reasons = [
        f"{aspect.replace('_', ' ')} score is strong"
        for aspect, score in aspect_scores.items()
        if score is not None and score >= 4
    ]
    if positive_evidence:
        reasons.append("Positive review evidence matches this scenario")
    return reasons[:5]


def _opposing_reasons(
    aspect_scores: dict[str, float | None],
    risk_flags: list[str],
    negative_evidence: list[ScenarioEvidenceItem],
) -> list[str]:
    reasons = [
        f"{aspect.replace('_', ' ')} score is weak"
        for aspect, score in aspect_scores.items()
        if score is not None and score < 3
    ]
    if risk_flags:
        reasons.append("Relevant risk flags are present")
    if negative_evidence:
        reasons.append("Negative review evidence matches this scenario")
    return reasons[:5]


def _fit_label(fit_score: float | None) -> FitLabel:
    if fit_score is None:
        return "insufficient_data"
    if fit_score >= 4:
        return "good_fit"
    if fit_score >= 3:
        return "mixed_fit"
    return "poor_fit"


def _average(values: list[float | None]) -> float | None:
    clean_values = [value for value in values if value is not None]
    if not clean_values:
        return None
    return round(sum(clean_values) / len(clean_values), 3)


@tool(
    "get_scenario_fit",
    args_schema=ScenarioFitToolInput,
    return_direct=False,
)
def get_scenario_fit_tool(
    business_id: str,
    scenario: ScenarioName,
    evidence_limit: int = 4,
) -> dict:
    """Compute deterministic scenario fit from aspect scores and review evidence.

    Supported intents:
    - scenario: date, family, quick_meal

    Use this tool when the user asks whether the selected restaurant is suitable
    for a concrete usage scenario such as a date, family meal, or quick meal.

    Do not use this tool for generic restaurant profile data, open-ended review
    search, broad positive/negative pattern summaries, or recent trend analysis.

    Reads:
    - restaurant_aspect_signals scenario-specific aspect scores, pros, cons,
      risk_flags, updated_at
    - reviews.review_id, business_id, stars, text, review_date
    - review_aspect_signals overall sentiment, aspect scores, aspect_sentiments,
      evidence_terms, pros, cons, risk_flags, confidence

    Input:
    - business_id: required selected restaurant ID.
    - scenario: date, family, or quick_meal.
    - evidence_limit: maximum positive and negative evidence rows per side.

    Flow:
    1. Open a SQLAlchemy session using the configured application database.
    2. Resolve scenario-specific weighted aspect scores.
    3. Use the shared scorer to select positive and negative scenario evidence.
    4. Apply a capped risk penalty from relevant risk flags.
    5. Return fit score, fit label, reasons, risks, evidence, and coverage.

    Output:
    - tool_name: get_scenario_fit.
    - status: ok or empty.
    - data.fit_score and data.fit_label.
    - data.aspect_scores and data.weights.
    - data.supporting_reasons and data.opposing_reasons.
    - data.positive_evidence and data.negative_evidence.
    - data.coverage.
    - data_sources: table and column metadata for traceability.
    - errors: recoverable tool errors, empty on success.

    This tool does not generate recommendations or natural-language answers.
    """

    with get_session_factory()() as session:
        result = get_scenario_fit(
            session,
            ScenarioFitToolInput(
                business_id=business_id,
                scenario=scenario,
                evidence_limit=evidence_limit,
            ),
        )
    return result.model_dump()
