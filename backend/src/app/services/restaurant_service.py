from __future__ import annotations

from sqlalchemy import Select, desc, select
from sqlalchemy.orm import Session

from app.db.models import Restaurant, Review


def list_restaurants(session: Session, query: str | None = None, limit: int = 20) -> list[Restaurant]:
    statement: Select[tuple[Restaurant]] = select(Restaurant)

    if query:
        pattern = f"%{query.strip().lower()}%"
        statement = statement.where(
            Restaurant.name.ilike(pattern)
            | Restaurant.city.ilike(pattern)
        )

    statement = statement.order_by(desc(Restaurant.review_count), Restaurant.business_id).limit(limit)
    return list(session.scalars(statement))


def get_restaurant(session: Session, business_id: str) -> Restaurant | None:
    return session.get(Restaurant, business_id)


def get_restaurant_reviews(session: Session, business_id: str, limit: int = 20) -> list[Review]:
    statement = (
        select(Review)
        .where(Review.business_id == business_id)
        .order_by(desc(Review.review_date), Review.review_id)
        .limit(limit)
    )
    return list(session.scalars(statement))
