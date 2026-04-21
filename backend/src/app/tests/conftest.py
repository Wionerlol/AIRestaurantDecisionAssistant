from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.agents.graph.graph import reset_chat_graph
from app.core.config import settings
from app.core.llm import reset_chat_model
from app.db.bootstrap import init_database
from app.db.session import get_engine, reset_db_caches


@pytest.fixture()
def db_session(tmp_path: Path) -> Session:
    original_database_url = settings.database_url
    original_auto_seed = settings.database_auto_seed
    original_sample_businesses_path = settings.sample_businesses_path
    original_sample_reviews_path = settings.sample_reviews_path
    sample_businesses_path, sample_reviews_path = _write_test_sample_files(tmp_path)

    settings.database_url = f"sqlite:///{tmp_path / 'test.db'}"
    settings.database_auto_seed = True
    settings.sample_businesses_path = str(sample_businesses_path)
    settings.sample_reviews_path = str(sample_reviews_path)
    reset_db_caches()
    init_database()

    session = Session(get_engine())
    try:
        yield session
    finally:
        session.close()
        reset_chat_graph()
        reset_chat_model()
        reset_db_caches()
        settings.database_url = original_database_url
        settings.database_auto_seed = original_auto_seed
        settings.sample_businesses_path = original_sample_businesses_path
        settings.sample_reviews_path = original_sample_reviews_path


@pytest.fixture(autouse=True)
def force_stub_llm() -> None:
    original_llm_provider = settings.llm_provider
    original_llm_model_name = settings.llm_model_name
    original_stub_prefix = settings.stub_llm_response_prefix
    original_stub_default_reply = settings.stub_llm_default_reply

    settings.llm_provider = "stub"
    settings.llm_model_name = "stub-chat-model"
    settings.stub_llm_response_prefix = "Stub reply: "
    settings.stub_llm_default_reply = "Hello from the stub model."
    reset_chat_model()
    reset_chat_graph()

    try:
        yield
    finally:
        settings.llm_provider = original_llm_provider
        settings.llm_model_name = original_llm_model_name
        settings.stub_llm_response_prefix = original_stub_prefix
        settings.stub_llm_default_reply = original_stub_default_reply
        reset_chat_model()
        reset_chat_graph()


def _write_test_sample_files(tmp_path: Path) -> tuple[Path, Path]:
    business_output = tmp_path / "test_businesses.jsonl"
    review_output = tmp_path / "test_reviews.jsonl"
    selected_businesses = []

    with settings.sample_businesses_file.open("r", encoding="utf-8") as handle:
        for line in handle:
            selected_businesses.append(json.loads(line))
            if len(selected_businesses) >= 10:
                break

    selected_ids = {business["business_id"] for business in selected_businesses}
    review_counts = {business_id: 0 for business_id in selected_ids}
    selected_reviews = []

    with settings.sample_reviews_file.open("r", encoding="utf-8") as handle:
        for line in handle:
            payload = json.loads(line)
            business_id = payload["business_id"]
            if business_id not in selected_ids or review_counts[business_id] >= 20:
                continue
            selected_reviews.append(payload)
            review_counts[business_id] += 1
            if all(count >= 20 for count in review_counts.values()):
                break

    with business_output.open("w", encoding="utf-8") as handle:
        for business in selected_businesses:
            handle.write(json.dumps(business, ensure_ascii=False) + "\n")

    with review_output.open("w", encoding="utf-8") as handle:
        for review in selected_reviews:
            handle.write(json.dumps(review, ensure_ascii=False) + "\n")

    return business_output, review_output
