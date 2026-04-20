from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.db.models import Review, ReviewAspectSignal


AspectDirection = Literal["positive", "negative", "absolute"]
SentimentTarget = Literal["positive", "negative", "neutral", "mixed"]
StarPreference = Literal["high", "low", "extreme", "none"]

ASPECT_SCORE_FIELDS: dict[str, str] = {
    "food": "food_score",
    "service": "service_score",
    "price": "price_score",
    "ambience": "ambience_score",
    "waiting_time": "waiting_time_score",
}


class ReviewEvidenceCandidate(BaseModel):
    review_id: str
    business_id: str
    text: str
    stars: float
    review_date: datetime
    aspect_scores: dict[str, float | None]
    overall_sentiment_score: float | None = None
    overall_sentiment_label: str | None = None
    evidence_terms: list[str] = Field(default_factory=list)
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    confidence: float | None = None


class ReviewEvidenceScoringConfig(BaseModel):
    aspect_weights: dict[str, float] = Field(default_factory=dict)
    aspect_direction: AspectDirection = "positive"
    positive_keywords: list[str] = Field(default_factory=list)
    negative_keywords: list[str] = Field(default_factory=list)
    sentiment_target: SentimentTarget | None = None
    prefer_recent: bool = True
    prefer_high_confidence: bool = True
    star_preference: StarPreference = "none"
    limit: int = Field(default=8, ge=1, le=100)
    keyword_weight: float = 0.30
    sentiment_weight: float = 0.25
    aspect_weight: float = 0.25
    confidence_weight: float = 0.10
    recency_weight: float = 0.05
    star_weight: float = 0.05


class ReviewEvidenceScoreBreakdown(BaseModel):
    keyword_score: float
    sentiment_score: float
    aspect_score: float
    confidence_score: float
    recency_score: float
    star_score: float


class ScoredReviewEvidence(BaseModel):
    candidate: ReviewEvidenceCandidate
    score: float
    breakdown: ReviewEvidenceScoreBreakdown
    matched_keywords: list[str]


def build_candidate_from_review_signal(
    review: Review,
    signal: ReviewAspectSignal,
) -> ReviewEvidenceCandidate:
    return ReviewEvidenceCandidate(
        review_id=review.review_id,
        business_id=review.business_id,
        text=review.text,
        stars=review.stars,
        review_date=review.review_date,
        aspect_scores={
            aspect: getattr(signal, score_field)
            for aspect, score_field in ASPECT_SCORE_FIELDS.items()
        },
        overall_sentiment_score=signal.overall_sentiment_score,
        overall_sentiment_label=signal.overall_sentiment_label,
        evidence_terms=signal.evidence_terms,
        pros=signal.pros,
        cons=signal.cons,
        risk_flags=signal.risk_flags,
        confidence=signal.confidence,
    )


def score_review_evidence(
    candidates: list[ReviewEvidenceCandidate],
    config: ReviewEvidenceScoringConfig,
) -> list[ScoredReviewEvidence]:
    latest_review_date = max((candidate.review_date for candidate in candidates), default=None)
    scored = [_score_candidate(candidate, config, latest_review_date) for candidate in candidates]
    scored.sort(
        key=lambda item: (
            item.score,
            item.candidate.confidence or 0,
            item.candidate.review_date,
            item.candidate.review_id,
        ),
        reverse=True,
    )
    return scored[: config.limit]


def _score_candidate(
    candidate: ReviewEvidenceCandidate,
    config: ReviewEvidenceScoringConfig,
    latest_review_date: datetime | None,
) -> ScoredReviewEvidence:
    keyword_score, matched_keywords = _keyword_score(candidate, config)
    breakdown = ReviewEvidenceScoreBreakdown(
        keyword_score=keyword_score,
        sentiment_score=_sentiment_score(candidate, config.sentiment_target),
        aspect_score=_aspect_score(candidate, config),
        confidence_score=_confidence_score(candidate, config.prefer_high_confidence),
        recency_score=_recency_score(candidate, latest_review_date, config.prefer_recent),
        star_score=_star_score(candidate.stars, config.star_preference),
    )
    score = round(
        breakdown.keyword_score * config.keyword_weight
        + breakdown.sentiment_score * config.sentiment_weight
        + breakdown.aspect_score * config.aspect_weight
        + breakdown.confidence_score * config.confidence_weight
        + breakdown.recency_score * config.recency_weight
        + breakdown.star_score * config.star_weight,
        6,
    )
    return ScoredReviewEvidence(
        candidate=candidate,
        score=score,
        breakdown=breakdown,
        matched_keywords=matched_keywords,
    )


def _keyword_score(
    candidate: ReviewEvidenceCandidate,
    config: ReviewEvidenceScoringConfig,
) -> tuple[float, list[str]]:
    keywords = _normalize_keywords(config.positive_keywords + config.negative_keywords)
    if not keywords:
        return 0.0, []

    structured_text = " ".join(
        candidate.risk_flags + candidate.pros + candidate.cons + candidate.evidence_terms
    ).lower()
    review_text = candidate.text.lower()
    matched = []
    weighted_hits = 0.0

    for keyword in keywords:
        structured_match = keyword in structured_text
        text_match = keyword in review_text
        if structured_match or text_match:
            matched.append(keyword)
            if structured_match:
                weighted_hits += 1.0
            if text_match:
                weighted_hits += 0.5

    return min(1.0, weighted_hits / max(len(keywords), 1)), matched


def _normalize_keywords(keywords: list[str]) -> list[str]:
    return [keyword.strip().lower() for keyword in keywords if keyword.strip()]


def _sentiment_score(
    candidate: ReviewEvidenceCandidate,
    sentiment_target: SentimentTarget | None,
) -> float:
    score = candidate.overall_sentiment_score
    label = candidate.overall_sentiment_label

    if sentiment_target == "positive":
        if label == "positive":
            return 1.0
        return _clamp01(((score or 0) + 1) / 2)

    if sentiment_target == "negative":
        if label == "negative":
            return 1.0
        return _clamp01((1 - (score or 0)) / 2)

    if sentiment_target is not None:
        return 1.0 if label == sentiment_target else 0.0

    return _clamp01(abs(score or 0))


def _aspect_score(
    candidate: ReviewEvidenceCandidate,
    config: ReviewEvidenceScoringConfig,
) -> float:
    weighted_scores = []
    total_weight = 0.0

    for aspect, weight in config.aspect_weights.items():
        raw_score = candidate.aspect_scores.get(aspect)
        if raw_score is None or weight <= 0:
            continue

        total_weight += weight
        weighted_scores.append(_normalize_aspect(raw_score, config.aspect_direction) * weight)

    if total_weight <= 0:
        return 0.0
    return _clamp01(sum(weighted_scores) / total_weight)


def _normalize_aspect(raw_score: float, direction: AspectDirection) -> float:
    normalized = _clamp01(raw_score / 5)
    if direction == "negative":
        return 1 - normalized
    if direction == "absolute":
        return abs(normalized - 0.5) * 2
    return normalized


def _confidence_score(candidate: ReviewEvidenceCandidate, prefer_high_confidence: bool) -> float:
    if not prefer_high_confidence:
        return 0.0
    return _clamp01(candidate.confidence if candidate.confidence is not None else 0.5)


def _recency_score(
    candidate: ReviewEvidenceCandidate,
    latest_review_date: datetime | None,
    prefer_recent: bool,
) -> float:
    if not prefer_recent or latest_review_date is None:
        return 0.0
    age_days = max((latest_review_date - candidate.review_date).days, 0)
    return _clamp01(1 - (age_days / 365))


def _star_score(stars: float, star_preference: StarPreference) -> float:
    if star_preference == "high":
        return _clamp01(stars / 5)
    if star_preference == "low":
        return _clamp01((5 - stars) / 5)
    if star_preference == "extreme":
        return _clamp01(abs(stars - 3) / 2)
    return 0.0


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))
