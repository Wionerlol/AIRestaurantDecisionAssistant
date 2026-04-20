from sqlalchemy.orm import Session

from app.agents.tools.negative_review_patterns import (
    NEGATIVE_RESTAURANT_ASPECT_COLUMNS,
    NEGATIVE_REVIEW_ASPECT_COLUMNS,
    NEGATIVE_REVIEW_COLUMNS,
    NegativeReviewPatternsToolInput,
    get_negative_review_patterns,
    get_negative_review_patterns_tool,
)
from app.agents.tools.positive_review_patterns import (
    POSITIVE_RESTAURANT_ASPECT_COLUMNS,
    POSITIVE_REVIEW_ASPECT_COLUMNS,
    POSITIVE_REVIEW_COLUMNS,
    PositiveReviewPatternsToolInput,
    get_positive_review_patterns,
    get_positive_review_patterns_tool,
)
from app.agents.tools.recent_review_trend import (
    RECENT_REVIEW_ASPECT_COLUMNS,
    RECENT_REVIEW_COLUMNS,
    RecentReviewTrendToolInput,
    get_recent_review_trend,
    get_recent_review_trend_tool,
)
from app.agents.tools.restaurant_aspect_summary import (
    RESTAURANT_ASPECT_SUMMARY_COLUMNS,
    RestaurantAspectSummaryToolInput,
    get_restaurant_aspect_summary,
    get_restaurant_aspect_summary_tool,
)
from app.agents.tools.restaurant_profile import (
    RESTAURANT_PROFILE_COLUMNS,
    RestaurantProfileToolInput,
    get_restaurant_profile,
    get_restaurant_profile_tool,
)
from app.agents.tools.review_aspect_evidence import (
    REVIEW_ASPECT_EVIDENCE_COLUMNS,
    REVIEW_EVIDENCE_COLUMNS,
    ReviewAspectEvidenceToolInput,
    get_review_aspect_evidence,
    get_review_aspect_evidence_tool,
)
from app.db.models import RestaurantAspectSignal, ReviewAspectSignal
from app.db.session import reset_db_caches
from app.services.restaurant_service import get_restaurant_reviews, list_restaurants


def test_get_restaurant_profile_returns_selected_restaurant(db_session: Session) -> None:
    restaurant = list_restaurants(db_session, limit=1)[0]

    result = get_restaurant_profile(
        db_session,
        RestaurantProfileToolInput(business_id=restaurant.business_id),
    )

    assert result.tool_name == "get_restaurant_profile"
    assert result.status == "ok"
    assert result.data is not None
    assert result.data.business_id == restaurant.business_id
    assert result.data.name == restaurant.name
    assert result.data.city == restaurant.city
    assert result.data.state == restaurant.state
    assert result.data.review_count == restaurant.review_count
    assert result.errors == []


def test_get_restaurant_profile_returns_source_metadata(db_session: Session) -> None:
    restaurant = list_restaurants(db_session, limit=1)[0]

    result = get_restaurant_profile(
        db_session,
        RestaurantProfileToolInput(business_id=restaurant.business_id),
    )

    assert len(result.data_sources) == 1
    assert result.data_sources[0].table == "restaurants"
    assert result.data_sources[0].columns == RESTAURANT_PROFILE_COLUMNS


def test_get_restaurant_profile_returns_not_found_for_missing_restaurant(
    db_session: Session,
) -> None:
    result = get_restaurant_profile(
        db_session,
        RestaurantProfileToolInput(business_id="missing-restaurant"),
    )

    assert result.status == "not_found"
    assert result.data is None
    assert result.errors == ["Restaurant not found: missing-restaurant"]


def test_get_restaurant_profile_langchain_tool_metadata() -> None:
    assert get_restaurant_profile_tool.name == "get_restaurant_profile"
    assert get_restaurant_profile_tool.args_schema is RestaurantProfileToolInput
    assert "Supported intents:" in get_restaurant_profile_tool.description
    assert "restaurants.business_id" in get_restaurant_profile_tool.description


def test_get_restaurant_profile_langchain_tool_invokes_database(
    db_session: Session,
) -> None:
    restaurant = list_restaurants(db_session, limit=1)[0]

    reset_db_caches()
    try:
        result = get_restaurant_profile_tool.invoke({"business_id": restaurant.business_id})
    finally:
        reset_db_caches()

    assert result["tool_name"] == "get_restaurant_profile"
    assert result["status"] == "ok"
    assert result["data"]["business_id"] == restaurant.business_id
    assert result["data_sources"][0]["table"] == "restaurants"
    assert result["errors"] == []


def test_get_restaurant_aspect_summary_returns_seeded_summary(
    db_session: Session,
) -> None:
    restaurant = list_restaurants(db_session, limit=1)[0]

    result = get_restaurant_aspect_summary(
        db_session,
        RestaurantAspectSummaryToolInput(business_id=restaurant.business_id),
    )

    assert result.tool_name == "get_restaurant_aspect_summary"
    assert result.status == "ok"
    assert result.data is not None
    assert result.data.business_id == restaurant.business_id
    assert result.data.overall_rating == restaurant.stars
    assert result.data.pros == []
    assert result.data.cons == []
    assert result.data.risk_flags == []
    assert result.errors == []


def test_get_restaurant_aspect_summary_returns_source_metadata(
    db_session: Session,
) -> None:
    restaurant = list_restaurants(db_session, limit=1)[0]

    result = get_restaurant_aspect_summary(
        db_session,
        RestaurantAspectSummaryToolInput(business_id=restaurant.business_id),
    )

    assert len(result.data_sources) == 1
    assert result.data_sources[0].table == "restaurant_aspect_signals"
    assert result.data_sources[0].columns == RESTAURANT_ASPECT_SUMMARY_COLUMNS


def test_get_restaurant_aspect_summary_returns_not_found_for_missing_restaurant(
    db_session: Session,
) -> None:
    result = get_restaurant_aspect_summary(
        db_session,
        RestaurantAspectSummaryToolInput(business_id="missing-restaurant"),
    )

    assert result.status == "not_found"
    assert result.data is None
    assert result.errors == ["Restaurant aspect summary not found: missing-restaurant"]


def test_get_restaurant_aspect_summary_langchain_tool_metadata() -> None:
    assert get_restaurant_aspect_summary_tool.name == "get_restaurant_aspect_summary"
    assert get_restaurant_aspect_summary_tool.args_schema is RestaurantAspectSummaryToolInput
    assert "Supported intents:" in get_restaurant_aspect_summary_tool.description
    assert (
        "restaurant_aspect_signals.overall_rating" in get_restaurant_aspect_summary_tool.description
    )


def test_get_restaurant_aspect_summary_langchain_tool_invokes_database(
    db_session: Session,
) -> None:
    restaurant = list_restaurants(db_session, limit=1)[0]

    reset_db_caches()
    try:
        result = get_restaurant_aspect_summary_tool.invoke({"business_id": restaurant.business_id})
    finally:
        reset_db_caches()

    assert result["tool_name"] == "get_restaurant_aspect_summary"
    assert result["status"] == "ok"
    assert result["data"]["business_id"] == restaurant.business_id
    assert result["data"]["overall_rating"] == restaurant.stars
    assert result["data_sources"][0]["table"] == "restaurant_aspect_signals"
    assert result["errors"] == []


def test_get_review_aspect_evidence_returns_bounded_review_rows(
    db_session: Session,
) -> None:
    restaurant = list_restaurants(db_session, limit=1)[0]

    result = get_review_aspect_evidence(
        db_session,
        ReviewAspectEvidenceToolInput(business_id=restaurant.business_id, limit=3),
    )

    assert result.tool_name == "get_review_aspect_evidence"
    assert result.status == "ok"
    assert result.data.business_id == restaurant.business_id
    assert result.data.total == 3
    assert len(result.data.items) == 3
    assert result.data.items[0].business_id == restaurant.business_id
    assert result.data.items[0].text
    assert set(result.data.items[0].aspect_scores) == {
        "food",
        "service",
        "price",
        "ambience",
        "waiting_time",
    }
    assert result.data.items[0].selected_aspect_scores == {}
    assert result.errors == []


def test_get_review_aspect_evidence_includes_selected_aspect_scores(
    db_session: Session,
) -> None:
    restaurant = list_restaurants(db_session, limit=1)[0]

    result = get_review_aspect_evidence(
        db_session,
        ReviewAspectEvidenceToolInput(
            business_id=restaurant.business_id,
            aspect="food",
            aspects=["service"],
            limit=1,
        ),
    )

    assert result.status == "ok"
    assert result.data.total == 1
    assert result.data.items[0].selected_aspect_scores == {
        "food": None,
        "service": None,
    }


def test_get_review_aspect_evidence_returns_empty_when_filter_has_no_matches(
    db_session: Session,
) -> None:
    restaurant = list_restaurants(db_session, limit=1)[0]

    result = get_review_aspect_evidence(
        db_session,
        ReviewAspectEvidenceToolInput(
            business_id=restaurant.business_id,
            sentiment="negative",
        ),
    )

    assert result.status == "empty"
    assert result.data.business_id == restaurant.business_id
    assert result.data.total == 0
    assert result.data.items == []
    assert result.errors == []


def test_get_review_aspect_evidence_returns_source_metadata(
    db_session: Session,
) -> None:
    restaurant = list_restaurants(db_session, limit=1)[0]

    result = get_review_aspect_evidence(
        db_session,
        ReviewAspectEvidenceToolInput(business_id=restaurant.business_id, limit=1),
    )

    assert len(result.data_sources) == 2
    assert result.data_sources[0].table == "reviews"
    assert result.data_sources[0].columns == REVIEW_EVIDENCE_COLUMNS
    assert result.data_sources[1].table == "review_aspect_signals"
    assert result.data_sources[1].columns == REVIEW_ASPECT_EVIDENCE_COLUMNS


def test_get_review_aspect_evidence_langchain_tool_metadata() -> None:
    assert get_review_aspect_evidence_tool.name == "get_review_aspect_evidence"
    assert get_review_aspect_evidence_tool.args_schema is ReviewAspectEvidenceToolInput
    assert "Supported intents:" in get_review_aspect_evidence_tool.description
    assert "review_aspect_signals.food_score" in get_review_aspect_evidence_tool.description


def test_get_review_aspect_evidence_langchain_tool_invokes_database(
    db_session: Session,
) -> None:
    restaurant = list_restaurants(db_session, limit=1)[0]

    reset_db_caches()
    try:
        result = get_review_aspect_evidence_tool.invoke(
            {
                "business_id": restaurant.business_id,
                "aspect": "food",
                "limit": 2,
            }
        )
    finally:
        reset_db_caches()

    assert result["tool_name"] == "get_review_aspect_evidence"
    assert result["status"] == "ok"
    assert result["data"]["business_id"] == restaurant.business_id
    assert result["data"]["total"] == 2
    assert result["data"]["items"][0]["selected_aspect_scores"] == {"food": None}
    assert result["data_sources"][0]["table"] == "reviews"
    assert result["data_sources"][1]["table"] == "review_aspect_signals"
    assert result["errors"] == []


def test_get_negative_review_patterns_returns_common_complaints(
    db_session: Session,
) -> None:
    restaurant = list_restaurants(db_session, limit=1)[0]
    reviews = get_restaurant_reviews(db_session, restaurant.business_id, limit=2)
    first_signal = db_session.get(ReviewAspectSignal, reviews[0].review_id)
    second_signal = db_session.get(ReviewAspectSignal, reviews[1].review_id)
    restaurant_signal = db_session.get(RestaurantAspectSignal, restaurant.business_id)
    assert first_signal is not None
    assert second_signal is not None
    assert restaurant_signal is not None

    first_signal.overall_sentiment_label = "negative"
    first_signal.overall_sentiment_score = -0.7
    first_signal.service_score = 1.2
    first_signal.evidence_terms = ["slow", "rude"]
    first_signal.cons = ["slow service"]
    first_signal.risk_flags = ["service inconsistency"]
    first_signal.confidence = 0.9
    second_signal.cons = ["slow service"]
    second_signal.risk_flags = ["long wait"]
    restaurant_signal.cons = ["inconsistent service"]
    restaurant_signal.risk_flags = ["busy at peak hours"]
    db_session.commit()

    result = get_negative_review_patterns(
        db_session,
        NegativeReviewPatternsToolInput(
            business_id=restaurant.business_id,
            aspect="service",
            limit=2,
        ),
    )

    assert result.tool_name == "get_negative_review_patterns"
    assert result.status == "ok"
    assert result.data.business_id == restaurant.business_id
    assert result.data.aspect == "service"
    assert result.data.total == 2
    assert "slow service" in result.data.top_cons
    assert "inconsistent service" in result.data.top_cons
    assert "service inconsistency" in result.data.top_risk_flags
    assert "busy at peak hours" in result.data.top_risk_flags
    assert "slow" in result.data.top_evidence_terms
    assert result.data.items[0].selected_aspect_score == 1.2
    assert "negative sentiment label" in result.data.items[0].negative_reasons
    assert "low selected aspect score" in result.data.items[0].negative_reasons
    assert result.errors == []


def test_get_negative_review_patterns_returns_empty_for_missing_restaurant(
    db_session: Session,
) -> None:
    result = get_negative_review_patterns(
        db_session,
        NegativeReviewPatternsToolInput(business_id="missing-restaurant"),
    )

    assert result.status == "empty"
    assert result.data.business_id == "missing-restaurant"
    assert result.data.total == 0
    assert result.data.top_cons == []
    assert result.data.top_risk_flags == []
    assert result.data.items == []
    assert result.errors == []


def test_get_negative_review_patterns_returns_source_metadata(
    db_session: Session,
) -> None:
    restaurant = list_restaurants(db_session, limit=1)[0]

    result = get_negative_review_patterns(
        db_session,
        NegativeReviewPatternsToolInput(business_id=restaurant.business_id, limit=1),
    )

    assert len(result.data_sources) == 3
    assert result.data_sources[0].table == "reviews"
    assert result.data_sources[0].columns == NEGATIVE_REVIEW_COLUMNS
    assert result.data_sources[1].table == "review_aspect_signals"
    assert result.data_sources[1].columns == NEGATIVE_REVIEW_ASPECT_COLUMNS
    assert result.data_sources[2].table == "restaurant_aspect_signals"
    assert result.data_sources[2].columns == NEGATIVE_RESTAURANT_ASPECT_COLUMNS


def test_get_negative_review_patterns_langchain_tool_metadata() -> None:
    assert get_negative_review_patterns_tool.name == "get_negative_review_patterns"
    assert get_negative_review_patterns_tool.args_schema is NegativeReviewPatternsToolInput
    assert "Supported intents:" in get_negative_review_patterns_tool.description
    assert "review_aspect_signals" in get_negative_review_patterns_tool.description


def test_get_negative_review_patterns_langchain_tool_invokes_database(
    db_session: Session,
) -> None:
    restaurant = list_restaurants(db_session, limit=1)[0]
    review = get_restaurant_reviews(db_session, restaurant.business_id, limit=1)[0]
    signal = db_session.get(ReviewAspectSignal, review.review_id)
    assert signal is not None

    signal.overall_sentiment_label = "negative"
    signal.cons = ["cold food"]
    signal.risk_flags = ["quality variance"]
    db_session.commit()

    reset_db_caches()
    try:
        result = get_negative_review_patterns_tool.invoke(
            {
                "business_id": restaurant.business_id,
                "limit": 1,
            }
        )
    finally:
        reset_db_caches()

    assert result["tool_name"] == "get_negative_review_patterns"
    assert result["status"] == "ok"
    assert result["data"]["business_id"] == restaurant.business_id
    assert result["data"]["total"] == 1
    assert "cold food" in result["data"]["top_cons"]
    assert result["data_sources"][0]["table"] == "reviews"
    assert result["data_sources"][1]["table"] == "review_aspect_signals"
    assert result["data_sources"][2]["table"] == "restaurant_aspect_signals"
    assert result["errors"] == []


def test_get_positive_review_patterns_returns_common_strengths(
    db_session: Session,
) -> None:
    restaurant = list_restaurants(db_session, limit=1)[0]
    reviews = get_restaurant_reviews(db_session, restaurant.business_id, limit=2)
    first_signal = db_session.get(ReviewAspectSignal, reviews[0].review_id)
    second_signal = db_session.get(ReviewAspectSignal, reviews[1].review_id)
    restaurant_signal = db_session.get(RestaurantAspectSignal, restaurant.business_id)
    assert first_signal is not None
    assert second_signal is not None
    assert restaurant_signal is not None

    first_signal.overall_sentiment_label = "positive"
    first_signal.overall_sentiment_score = 0.8
    first_signal.food_score = 4.6
    first_signal.evidence_terms = ["fresh", "flavorful"]
    first_signal.pros = ["great food"]
    first_signal.confidence = 0.95
    second_signal.pros = ["great food"]
    second_signal.evidence_terms = ["friendly"]
    restaurant_signal.pros = ["popular dishes"]
    db_session.commit()

    result = get_positive_review_patterns(
        db_session,
        PositiveReviewPatternsToolInput(
            business_id=restaurant.business_id,
            aspect="food",
            limit=2,
        ),
    )

    assert result.tool_name == "get_positive_review_patterns"
    assert result.status == "ok"
    assert result.data.business_id == restaurant.business_id
    assert result.data.aspect == "food"
    assert result.data.total == 2
    assert "great food" in result.data.top_pros
    assert "popular dishes" in result.data.top_pros
    assert "fresh" in result.data.top_evidence_terms
    assert result.data.items[0].selected_aspect_score == 4.6
    assert "positive sentiment label" in result.data.items[0].positive_reasons
    assert "high selected aspect score" in result.data.items[0].positive_reasons
    assert result.errors == []


def test_get_positive_review_patterns_returns_empty_for_missing_restaurant(
    db_session: Session,
) -> None:
    result = get_positive_review_patterns(
        db_session,
        PositiveReviewPatternsToolInput(business_id="missing-restaurant"),
    )

    assert result.status == "empty"
    assert result.data.business_id == "missing-restaurant"
    assert result.data.total == 0
    assert result.data.top_pros == []
    assert result.data.items == []
    assert result.errors == []


def test_get_positive_review_patterns_returns_source_metadata(
    db_session: Session,
) -> None:
    restaurant = list_restaurants(db_session, limit=1)[0]

    result = get_positive_review_patterns(
        db_session,
        PositiveReviewPatternsToolInput(business_id=restaurant.business_id, limit=1),
    )

    assert len(result.data_sources) == 3
    assert result.data_sources[0].table == "reviews"
    assert result.data_sources[0].columns == POSITIVE_REVIEW_COLUMNS
    assert result.data_sources[1].table == "review_aspect_signals"
    assert result.data_sources[1].columns == POSITIVE_REVIEW_ASPECT_COLUMNS
    assert result.data_sources[2].table == "restaurant_aspect_signals"
    assert result.data_sources[2].columns == POSITIVE_RESTAURANT_ASPECT_COLUMNS


def test_get_positive_review_patterns_langchain_tool_metadata() -> None:
    assert get_positive_review_patterns_tool.name == "get_positive_review_patterns"
    assert get_positive_review_patterns_tool.args_schema is PositiveReviewPatternsToolInput
    assert "Supported intents:" in get_positive_review_patterns_tool.description
    assert "review_aspect_signals" in get_positive_review_patterns_tool.description


def test_get_positive_review_patterns_langchain_tool_invokes_database(
    db_session: Session,
) -> None:
    restaurant = list_restaurants(db_session, limit=1)[0]
    review = get_restaurant_reviews(db_session, restaurant.business_id, limit=1)[0]
    signal = db_session.get(ReviewAspectSignal, review.review_id)
    assert signal is not None

    signal.overall_sentiment_label = "positive"
    signal.pros = ["excellent service"]
    db_session.commit()

    reset_db_caches()
    try:
        result = get_positive_review_patterns_tool.invoke(
            {
                "business_id": restaurant.business_id,
                "limit": 1,
            }
        )
    finally:
        reset_db_caches()

    assert result["tool_name"] == "get_positive_review_patterns"
    assert result["status"] == "ok"
    assert result["data"]["business_id"] == restaurant.business_id
    assert result["data"]["total"] == 1
    assert "excellent service" in result["data"]["top_pros"]
    assert result["data_sources"][0]["table"] == "reviews"
    assert result["data_sources"][1]["table"] == "review_aspect_signals"
    assert result["data_sources"][2]["table"] == "restaurant_aspect_signals"
    assert result["errors"] == []


def test_get_recent_review_trend_returns_recent_reviews_and_averages(
    db_session: Session,
) -> None:
    restaurant = list_restaurants(db_session, limit=1)[0]

    result = get_recent_review_trend(
        db_session,
        RecentReviewTrendToolInput(business_id=restaurant.business_id, limit=3),
    )

    assert result.tool_name == "get_recent_review_trend"
    assert result.status == "ok"
    assert result.data.business_id == restaurant.business_id
    assert result.data.total == 3
    assert len(result.data.items) == 3
    assert result.data.average_stars is not None
    assert result.data.date_range_start is not None
    assert result.data.date_range_end is not None
    assert result.data.star_trend in {"improving", "declining", "stable", "unknown"}
    assert set(result.data.aspect_average_scores) == {
        "food",
        "service",
        "price",
        "ambience",
        "waiting_time",
    }
    assert result.errors == []


def test_get_recent_review_trend_aggregates_model_outputs(
    db_session: Session,
) -> None:
    restaurant = list_restaurants(db_session, limit=1)[0]
    reviews = get_restaurant_reviews(db_session, restaurant.business_id, limit=2)
    first_signal = db_session.get(ReviewAspectSignal, reviews[0].review_id)
    second_signal = db_session.get(ReviewAspectSignal, reviews[1].review_id)
    assert first_signal is not None
    assert second_signal is not None

    first_signal.overall_sentiment_label = "positive"
    first_signal.overall_sentiment_score = 0.8
    first_signal.food_score = 4.0
    first_signal.risk_flags = ["recent crowding"]
    second_signal.overall_sentiment_label = "negative"
    second_signal.overall_sentiment_score = -0.4
    second_signal.food_score = 2.0
    db_session.commit()

    result = get_recent_review_trend(
        db_session,
        RecentReviewTrendToolInput(
            business_id=restaurant.business_id,
            months=120,
            limit=2,
        ),
    )

    assert result.status == "ok"
    assert result.data.total == 2
    assert result.data.months == 120
    assert result.data.average_sentiment_score == 0.2
    assert result.data.sentiment_label_counts == {"positive": 1, "negative": 1}
    assert result.data.aspect_average_scores["food"] == 3.0
    assert result.data.items[0].risk_flags == ["recent crowding"]


def test_get_recent_review_trend_returns_empty_for_missing_restaurant(
    db_session: Session,
) -> None:
    result = get_recent_review_trend(
        db_session,
        RecentReviewTrendToolInput(business_id="missing-restaurant"),
    )

    assert result.status == "empty"
    assert result.data.business_id == "missing-restaurant"
    assert result.data.total == 0
    assert result.data.average_stars is None
    assert result.data.sentiment_label_counts == {}
    assert result.data.items == []
    assert result.errors == []


def test_get_recent_review_trend_returns_source_metadata(
    db_session: Session,
) -> None:
    restaurant = list_restaurants(db_session, limit=1)[0]

    result = get_recent_review_trend(
        db_session,
        RecentReviewTrendToolInput(business_id=restaurant.business_id, limit=1),
    )

    assert len(result.data_sources) == 2
    assert result.data_sources[0].table == "reviews"
    assert result.data_sources[0].columns == RECENT_REVIEW_COLUMNS
    assert result.data_sources[1].table == "review_aspect_signals"
    assert result.data_sources[1].columns == RECENT_REVIEW_ASPECT_COLUMNS


def test_get_recent_review_trend_langchain_tool_metadata() -> None:
    assert get_recent_review_trend_tool.name == "get_recent_review_trend"
    assert get_recent_review_trend_tool.args_schema is RecentReviewTrendToolInput
    assert "Supported intents:" in get_recent_review_trend_tool.description
    assert "review_aspect_signals" in get_recent_review_trend_tool.description


def test_get_recent_review_trend_langchain_tool_invokes_database(
    db_session: Session,
) -> None:
    restaurant = list_restaurants(db_session, limit=1)[0]

    reset_db_caches()
    try:
        result = get_recent_review_trend_tool.invoke(
            {
                "business_id": restaurant.business_id,
                "limit": 2,
            }
        )
    finally:
        reset_db_caches()

    assert result["tool_name"] == "get_recent_review_trend"
    assert result["status"] == "ok"
    assert result["data"]["business_id"] == restaurant.business_id
    assert result["data"]["total"] == 2
    assert result["data_sources"][0]["table"] == "reviews"
    assert result["data_sources"][1]["table"] == "review_aspect_signals"
    assert result["errors"] == []
