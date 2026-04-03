from __future__ import annotations

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

    settings.database_url = f"sqlite:///{tmp_path / 'test.db'}"
    settings.database_auto_seed = True
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
