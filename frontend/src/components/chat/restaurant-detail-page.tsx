import { FormEvent } from "react";

import { ConversationPanel } from "./conversation-panel";
import {
  ChatIntent,
  ChatMessage,
  ChatProcessTrace,
  ChatStatus,
  RestaurantReview,
  RestaurantSummary,
} from "./types";

type RestaurantDetailPageProps = {
  chatErrorMessage: string;
  chatInput: string;
  chatIntent: ChatIntent | null;
  chatMessages: ChatMessage[];
  chatProcessTrace: ChatProcessTrace | null;
  chatStatus: ChatStatus;
  restaurant: RestaurantSummary;
  reviews: RestaurantReview[];
  reviewsError: string;
  reviewsStatus: ChatStatus;
  onBack: () => void;
  onChatInputChange: (value: string) => void;
  onChatSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

export function RestaurantDetailPage({
  chatErrorMessage,
  chatInput,
  chatIntent,
  chatMessages,
  chatProcessTrace,
  chatStatus,
  restaurant,
  reviews,
  reviewsError,
  reviewsStatus,
  onBack,
  onChatInputChange,
  onChatSubmit,
}: RestaurantDetailPageProps) {
  return (
    <main className="restaurant-detail-page">
      <button className="back-button" type="button" onClick={onBack}>
        ← Back
      </button>

      <aside className="restaurant-detail-sidebar">
        <RestaurantSnapshot restaurant={restaurant} />
        <ReviewList
          reviews={reviews}
          reviewsError={reviewsError}
          reviewsStatus={reviewsStatus}
        />
      </aside>

      <ConversationPanel
        errorMessage={chatErrorMessage}
        input={chatInput}
        intent={chatIntent}
        messages={chatMessages}
        processTrace={chatProcessTrace}
        selectedRestaurant={restaurant}
        status={chatStatus}
        onInputChange={onChatInputChange}
        onSubmit={onChatSubmit}
      />
    </main>
  );
}

type RestaurantSnapshotProps = {
  restaurant: RestaurantSummary;
};

function RestaurantSnapshot({ restaurant }: RestaurantSnapshotProps) {
  const categories = restaurant.categories
    .filter((category) => category !== "Restaurants")
    .slice(0, 5);

  return (
    <section className="chat-panel restaurant-snapshot">
      <span className="chat-eyebrow">Selected Restaurant</span>
      <h1>{restaurant.name}</h1>
      <p>
        {restaurant.city}, {restaurant.state}
      </p>
      <div className="restaurant-snapshot-metrics">
        <strong>{restaurant.stars?.toFixed(1) ?? "N/A"}</strong>
        <span>{restaurant.review_count} reviews</span>
      </div>
      <div className="restaurant-badges">
        {categories.map((category) => (
          <span key={category} className="restaurant-badge">
            {category}
          </span>
        ))}
      </div>
    </section>
  );
}

type ReviewListProps = {
  reviews: RestaurantReview[];
  reviewsError: string;
  reviewsStatus: ChatStatus;
};

function ReviewList({ reviews, reviewsError, reviewsStatus }: ReviewListProps) {
  return (
    <section className="chat-panel review-panel">
      <div className="review-panel-header">
        <div>
          <span className="chat-eyebrow">Recent Reviews</span>
          <h2>Review feed</h2>
        </div>
        <span className={`chat-status chat-status--${reviewsStatus}`}>
          {reviewsStatus === "idle" && "Loaded"}
          {reviewsStatus === "loading" && "Loading"}
          {reviewsStatus === "error" && "Error"}
        </span>
      </div>

      <span className="chat-error">{reviewsError}</span>

      <div className="review-list">
        {reviewsStatus === "loading" &&
          reviews.length === 0 &&
          Array.from({ length: 8 }).map((_, index) => (
            <div className="review-card review-card--loading" key={index} />
          ))}

        {reviews.map((review) => (
          <article className="review-card" key={review.review_id}>
            <div className="review-card-top">
              <strong>{review.stars.toFixed(1)}</strong>
              <span>{review.date.slice(0, 10)}</span>
            </div>
            <p>{review.text}</p>
            <small>
              Useful {review.useful} · Funny {review.funny} · Cool {review.cool}
            </small>
          </article>
        ))}
      </div>

      {reviewsStatus === "idle" && reviews.length === 0 && (
        <p className="review-empty-state">No reviews are available for this restaurant.</p>
      )}
    </section>
  );
}
