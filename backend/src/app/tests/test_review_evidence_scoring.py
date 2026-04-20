from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.agents.tools.review_evidence_scoring import (
    ReviewEvidenceCandidate,
    ReviewEvidenceScoringConfig,
    build_candidate_from_review_signal,
    score_review_evidence,
)
from app.db.models import ReviewAspectSignal
from app.services.restaurant_service import get_restaurant_reviews, list_restaurants


def test_score_review_evidence_prioritizes_structured_keyword_hits() -> None:
    candidate = ReviewEvidenceCandidate(
        review_id="review-1",
        business_id="restaurant-1",
        text="The place was fine.",
        stars=4,
        review_date=datetime(2024, 1, 1),
        aspect_scores={},
        evidence_terms=["romantic"],
        pros=["quiet"],
    )

    scored = score_review_evidence(
        [candidate],
        ReviewEvidenceScoringConfig(
            positive_keywords=["romantic", "quiet"],
            limit=1,
        ),
    )

    assert scored[0].score > 0
    assert scored[0].breakdown.keyword_score == 1.0
    assert scored[0].matched_keywords == ["romantic", "quiet"]


def test_score_review_evidence_uses_negative_sentiment_and_low_aspect_scores() -> None:
    candidate = ReviewEvidenceCandidate(
        review_id="review-1",
        business_id="restaurant-1",
        text="Slow and crowded.",
        stars=2,
        review_date=datetime(2024, 1, 1),
        aspect_scores={"service": 1.0, "waiting_time": 1.5},
        overall_sentiment_label="negative",
        overall_sentiment_score=-0.8,
        risk_flags=["slow service"],
        confidence=0.9,
    )

    scored = score_review_evidence(
        [candidate],
        ReviewEvidenceScoringConfig(
            aspect_weights={"service": 0.5, "waiting_time": 0.5},
            aspect_direction="negative",
            negative_keywords=["slow"],
            sentiment_target="negative",
            star_preference="low",
            limit=1,
        ),
    )

    assert scored[0].breakdown.sentiment_score == 1.0
    assert scored[0].breakdown.aspect_score > 0.7
    assert scored[0].breakdown.star_score == 0.6
    assert scored[0].score > 0.7


def test_score_review_evidence_uses_positive_sentiment_and_high_aspect_scores() -> None:
    candidate = ReviewEvidenceCandidate(
        review_id="review-1",
        business_id="restaurant-1",
        text="Great food and friendly staff.",
        stars=5,
        review_date=datetime(2024, 1, 1),
        aspect_scores={"food": 4.5, "service": 4.0},
        overall_sentiment_label="positive",
        overall_sentiment_score=0.9,
        pros=["great food"],
        confidence=0.8,
    )

    scored = score_review_evidence(
        [candidate],
        ReviewEvidenceScoringConfig(
            aspect_weights={"food": 0.6, "service": 0.4},
            aspect_direction="positive",
            positive_keywords=["great food"],
            sentiment_target="positive",
            star_preference="high",
            limit=1,
        ),
    )

    assert scored[0].breakdown.sentiment_score == 1.0
    assert scored[0].breakdown.aspect_score == pytest.approx(0.86)
    assert scored[0].breakdown.star_score == 1.0
    assert scored[0].score > 0.8


def test_score_review_evidence_orders_by_score_then_recency() -> None:
    older = ReviewEvidenceCandidate(
        review_id="older",
        business_id="restaurant-1",
        text="Good.",
        stars=4,
        review_date=datetime(2023, 1, 1),
        aspect_scores={"food": 4.0},
        overall_sentiment_label="positive",
        confidence=0.8,
    )
    newer = ReviewEvidenceCandidate(
        review_id="newer",
        business_id="restaurant-1",
        text="Good.",
        stars=4,
        review_date=datetime(2023, 1, 1) + timedelta(days=30),
        aspect_scores={"food": 4.0},
        overall_sentiment_label="positive",
        confidence=0.8,
    )

    scored = score_review_evidence(
        [older, newer],
        ReviewEvidenceScoringConfig(
            sentiment_target="positive",
            prefer_recent=True,
            limit=2,
        ),
    )

    assert [item.candidate.review_id for item in scored] == ["newer", "older"]
    assert scored[0].breakdown.recency_score == 1.0
    assert scored[1].breakdown.recency_score < 1.0


def test_score_review_evidence_applies_limit() -> None:
    candidates = [
        ReviewEvidenceCandidate(
            review_id=f"review-{index}",
            business_id="restaurant-1",
            text="Good.",
            stars=5,
            review_date=datetime(2024, 1, index + 1),
            aspect_scores={},
            overall_sentiment_label="positive",
        )
        for index in range(4)
    ]

    scored = score_review_evidence(
        candidates,
        ReviewEvidenceScoringConfig(sentiment_target="positive", limit=2),
    )

    assert len(scored) == 2


def test_build_candidate_from_review_signal_maps_database_models(
    db_session: Session,
) -> None:
    restaurant = list_restaurants(db_session, limit=1)[0]
    review = get_restaurant_reviews(db_session, restaurant.business_id, limit=1)[0]
    signal = db_session.get(ReviewAspectSignal, review.review_id)
    assert signal is not None

    signal.food_score = 4.5
    signal.overall_sentiment_label = "positive"
    signal.evidence_terms = ["fresh"]
    signal.pros = ["great food"]
    signal.confidence = 0.9
    db_session.commit()

    candidate = build_candidate_from_review_signal(review, signal)

    assert candidate.review_id == review.review_id
    assert candidate.business_id == restaurant.business_id
    assert candidate.text == review.text
    assert candidate.aspect_scores["food"] == 4.5
    assert candidate.overall_sentiment_label == "positive"
    assert candidate.evidence_terms == ["fresh"]
    assert candidate.pros == ["great food"]
    assert candidate.confidence == 0.9
