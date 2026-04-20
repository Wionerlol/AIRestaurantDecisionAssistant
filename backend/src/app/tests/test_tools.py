from sqlalchemy.orm import Session

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
from app.db.session import reset_db_caches
from app.services.restaurant_service import list_restaurants


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
