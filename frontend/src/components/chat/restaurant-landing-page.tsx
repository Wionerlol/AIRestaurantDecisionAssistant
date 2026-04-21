import { formatCategories } from "./chat-utils";
import { ChatStatus, RestaurantSummary } from "./types";

type RestaurantLandingPageProps = {
  restaurants: RestaurantSummary[];
  search: string;
  searchError: string;
  searchStatus: ChatStatus;
  onSearchChange: (value: string) => void;
  onRestaurantSelect: (restaurant: RestaurantSummary) => void;
};

export function RestaurantLandingPage({
  restaurants,
  search,
  searchError,
  searchStatus,
  onSearchChange,
  onRestaurantSelect,
}: RestaurantLandingPageProps) {
  return (
    <main className="landing-page">
      <section className="landing-hero">
        <p className="chat-eyebrow">Restaurant Decision Assistant</p>
        <h1 className="landing-title">Where should we eat?</h1>
        <p className="landing-copy">
          Search restaurants first. Then open one restaurant to inspect reviews and ask
          evidence-backed questions.
        </p>

        <div className="landing-search">
          <input
            className="landing-search-input"
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Search restaurant name, city, or category..."
          />
          <span className={`chat-status chat-status--${searchStatus}`}>
            {searchStatus === "idle" && "Loaded"}
            {searchStatus === "loading" && "Loading"}
            {searchStatus === "error" && "Error"}
          </span>
        </div>
        <span className="chat-error">{searchError}</span>
      </section>

      <section className="restaurant-catalog-shell">
        <div className="restaurant-catalog">
          {searchStatus === "loading" &&
            restaurants.length === 0 &&
            Array.from({ length: 12 }).map((_, index) => (
              <div className="restaurant-intro-card restaurant-intro-card--loading" key={index} />
            ))}

          {restaurants.map((restaurant) => (
            <RestaurantIntroCard
              key={restaurant.business_id}
              restaurant={restaurant}
              onSelect={onRestaurantSelect}
            />
          ))}
        </div>

        {searchStatus === "idle" && restaurants.length === 0 && (
          <div className="restaurant-empty-state">
            No restaurants found. Try a different name, city, or category.
          </div>
        )}
      </section>
    </main>
  );
}

type RestaurantIntroCardProps = {
  restaurant: RestaurantSummary;
  onSelect: (restaurant: RestaurantSummary) => void;
};

function RestaurantIntroCard({ restaurant, onSelect }: RestaurantIntroCardProps) {
  const categories = formatCategories(restaurant.categories);

  return (
    <button
      type="button"
      className="restaurant-intro-card"
      onClick={() => onSelect(restaurant)}
    >
      <div>
        <span className="restaurant-intro-location">
          {restaurant.city}, {restaurant.state}
        </span>
        <h2>{restaurant.name}</h2>
      </div>

      <div className="restaurant-intro-footer">
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
    </button>
  );
}
