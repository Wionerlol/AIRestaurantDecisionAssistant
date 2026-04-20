from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class Restaurant(Base):
    __tablename__ = "restaurants"

    business_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str] = mapped_column(String(128), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    postal_code: Mapped[str | None] = mapped_column(String(16))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    stars: Mapped[float | None] = mapped_column(Float)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_open: Mapped[int | None] = mapped_column(Integer)
    categories: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    reviews: Mapped[list["Review"]] = relationship(
        back_populates="restaurant",
        cascade="all, delete-orphan",
    )
    aspect_signal: Mapped["RestaurantAspectSignal | None"] = relationship(
        back_populates="restaurant",
        cascade="all, delete-orphan",
        uselist=False,
    )
    review_aspect_signals: Mapped[list["ReviewAspectSignal"]] = relationship(
        back_populates="restaurant",
        cascade="all, delete-orphan",
    )


class Review(Base):
    __tablename__ = "reviews"

    review_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(32), nullable=False)
    business_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("restaurants.business_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stars: Mapped[float] = mapped_column(Float, nullable=False)
    useful: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    funny: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cool: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    review_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    restaurant: Mapped[Restaurant] = relationship(back_populates="reviews")
    aspect_signal: Mapped["ReviewAspectSignal | None"] = relationship(
        back_populates="review",
        cascade="all, delete-orphan",
        uselist=False,
    )


class ReviewAspectSignal(Base):
    __tablename__ = "review_aspect_signals"

    review_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("reviews.review_id", ondelete="CASCADE"),
        primary_key=True,
    )
    business_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("restaurants.business_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    overall_sentiment_score: Mapped[float | None] = mapped_column(Float)
    overall_sentiment_label: Mapped[str | None] = mapped_column(String(32))
    food_score: Mapped[float | None] = mapped_column(Float)
    service_score: Mapped[float | None] = mapped_column(Float)
    price_score: Mapped[float | None] = mapped_column(Float)
    ambience_score: Mapped[float | None] = mapped_column(Float)
    waiting_time_score: Mapped[float | None] = mapped_column(Float)
    aspect_sentiments: Mapped[dict[str, float | str | None]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    evidence_terms: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    pros: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    cons: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    risk_flags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(128))
    model_version: Mapped[str | None] = mapped_column(String(64))
    confidence: Mapped[float | None] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )

    review: Mapped[Review] = relationship(back_populates="aspect_signal")
    restaurant: Mapped[Restaurant] = relationship(back_populates="review_aspect_signals")


class RestaurantAspectSignal(Base):
    __tablename__ = "restaurant_aspect_signals"

    business_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("restaurants.business_id", ondelete="CASCADE"),
        primary_key=True,
    )
    overall_rating: Mapped[float | None] = mapped_column(Float)
    food_score: Mapped[float | None] = mapped_column(Float)
    service_score: Mapped[float | None] = mapped_column(Float)
    price_score: Mapped[float | None] = mapped_column(Float)
    ambience_score: Mapped[float | None] = mapped_column(Float)
    waiting_time_score: Mapped[float | None] = mapped_column(Float)
    pros: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    cons: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    risk_flags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )

    restaurant: Mapped[Restaurant] = relationship(back_populates="aspect_signal")
