"use client";

import { FormEvent, useEffect, useState } from "react";

type ChatRole = "user" | "assistant";

type ChatMessage = {
  role: ChatRole;
  content: string;
};

type ChatIntent = {
  category: "recommendation" | "aspect" | "scenario" | "risk" | "summary";
  label:
    | "worth_it"
    | "should_go"
    | "food"
    | "service"
    | "price"
    | "ambience"
    | "date"
    | "family"
    | "quick_meal"
    | "complaints"
    | "warnings"
    | "summary";
};

type RestaurantSummary = {
  business_id: string;
  name: string;
  city: string;
  state: string;
  stars: number | null;
  review_count: number;
  categories: string[];
};

type RestaurantSearchResponse = {
  total: number;
  items: RestaurantSummary[];
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

const idleAssistantMessage =
  "Choose a restaurant from the search panel first. After that, every message will be sent in the context of that restaurant only.";

function buildStarterMessages(restaurant: RestaurantSummary | null): ChatMessage[] {
  if (!restaurant) {
    return [{ role: "assistant", content: idleAssistantMessage }];
  }

  const categories = restaurant.categories.slice(0, 4).join(", ") || "Unknown";
  const rating = restaurant.stars !== null ? `${restaurant.stars.toFixed(1)}/5` : "N/A";

  return [
    {
      role: "assistant",
      content: `Selected restaurant: ${restaurant.name}. Categories: ${categories}. Rating: ${rating}. Ask about this restaurant only.`,
    },
  ];
}

function formatCategories(categories: string[]) {
  return categories.filter((category) => category !== "Restaurants").slice(0, 3);
}

function formatIntent(intent: ChatIntent | null) {
  if (!intent) {
    return "No intent classified yet";
  }

  return `${intent.category} / ${intent.label.replaceAll("_", " ")}`;
}

export function ChatShell() {
  const [restaurants, setRestaurants] = useState<RestaurantSummary[]>([]);
  const [search, setSearch] = useState("");
  const [selectedRestaurant, setSelectedRestaurant] = useState<RestaurantSummary | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>(buildStarterMessages(null));
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [searchStatus, setSearchStatus] = useState<"idle" | "loading" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [searchError, setSearchError] = useState("");
  const [latestIntent, setLatestIntent] = useState<ChatIntent | null>(null);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    async function loadRestaurants() {
      setSearchStatus("loading");
      setSearchError("");

      try {
        const params = new URLSearchParams({ limit: "12" });
        if (search.trim()) {
          params.set("query", search.trim());
        }

        const response = await fetch(`${API_BASE_URL}/restaurants?${params.toString()}`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Backend returned ${response.status}`);
        }

        const payload = (await response.json()) as RestaurantSearchResponse;
        if (!active) {
          return;
        }

        setRestaurants(payload.items);
        setSearchStatus("idle");
      } catch (error) {
        if (!active || controller.signal.aborted) {
          return;
        }
        setSearchStatus("error");
        setSearchError(error instanceof Error ? error.message : "Unable to load restaurants.");
      }
    }

    void loadRestaurants();

    return () => {
      active = false;
      controller.abort();
    };
  }, [search]);

  function handleRestaurantSelect(restaurant: RestaurantSummary) {
    setSelectedRestaurant(restaurant);
    setMessages(buildStarterMessages(restaurant));
    setInput("");
    setStatus("idle");
    setErrorMessage("");
    setLatestIntent(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedRestaurant) {
      setStatus("error");
      setErrorMessage("Select a restaurant before sending a question.");
      return;
    }

    const trimmed = input.trim();
    if (!trimmed || status === "loading") {
      return;
    }

    const nextMessages = [...messages, { role: "user" as const, content: trimmed }];
    setMessages(nextMessages);
    setInput("");
    setStatus("loading");
    setErrorMessage("");

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          restaurant_context: selectedRestaurant,
          messages: nextMessages.map((message) => ({
            role: message.role,
            content: message.content,
          })),
        }),
      });

      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`);
      }

      const payload = (await response.json()) as {
        message: {
          role: "assistant";
          content: string;
        };
        intent: ChatIntent;
      };

      setMessages([...nextMessages, payload.message]);
      setLatestIntent(payload.intent);
      setStatus("idle");
    } catch (error) {
      setStatus("error");
      setErrorMessage(
        error instanceof Error ? error.message : "Unable to reach the backend.",
      );
    }
  }

  return (
    <main className="chat-page">
      <section className="chat-panel chat-panel--intro">
        <p className="chat-eyebrow">Restaurant Search</p>
        <h1 className="chat-title">Pick One Restaurant, Then Ask</h1>
        <p className="chat-copy">
          Search by restaurant name, city, or category. Once selected, the chat box stays
          scoped to that single restaurant for decision support.
        </p>

        <div className="chat-meta-grid">
          <article className="chat-meta-card">
            <span className="chat-meta-label">Backend</span>
            <strong>{API_BASE_URL}</strong>
          </article>
          <article className="chat-meta-card">
            <span className="chat-meta-label">Flow</span>
            <strong>Search → Select → Chat</strong>
          </article>
          <article className="chat-meta-card">
            <span className="chat-meta-label">Intent Layer</span>
            <strong>{formatIntent(latestIntent)}</strong>
          </article>
        </div>
      </section>

      <section className="chat-panel chat-panel--search">
        <div className="restaurant-search-header">
          <div>
            <h2>Restaurants</h2>
            <p>Search before opening the chat context.</p>
          </div>
          <div className={`chat-status chat-status--${searchStatus}`}>
            {searchStatus === "idle" && "Loaded"}
            {searchStatus === "loading" && "Loading"}
            {searchStatus === "error" && "Error"}
          </div>
        </div>

        <label className="chat-label" htmlFor="restaurant-search">
          Search
        </label>
        <input
          id="restaurant-search"
          className="restaurant-search-input"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search restaurant name, city, or type..."
        />

        <span className="chat-error">{searchError}</span>

        <div className="restaurant-grid">
          {restaurants.map((restaurant) => {
            const categories = formatCategories(restaurant.categories);
            const isSelected = selectedRestaurant?.business_id === restaurant.business_id;

            return (
              <button
                key={restaurant.business_id}
                type="button"
                className={`restaurant-card ${isSelected ? "restaurant-card--selected" : ""}`}
                onClick={() => handleRestaurantSelect(restaurant)}
              >
                <div className="restaurant-card-top">
                  <div>
                    <h3>{restaurant.name}</h3>
                    <p>
                      {restaurant.city}, {restaurant.state}
                    </p>
                  </div>
                  <div className="restaurant-rating">
                    <strong>{restaurant.stars?.toFixed(1) ?? "N/A"}</strong>
                    <span>{restaurant.review_count} reviews</span>
                  </div>
                </div>

                <div className="restaurant-badges">
                  {categories.map((category) => (
                    <span key={category} className="restaurant-badge">
                      {category}
                    </span>
                  ))}
                </div>

                <div className="restaurant-rating-bar">
                  <span
                    style={{
                      width: `${Math.max(8, ((restaurant.stars ?? 0) / 5) * 100)}%`,
                    }}
                  />
                </div>
              </button>
            );
          })}
        </div>
      </section>

      <section className="chat-panel chat-panel--conversation">
        <div className="chat-status-row">
          <div className={`chat-status chat-status--${status}`}>
            {status === "idle" && "Ready"}
            {status === "loading" && "Thinking"}
            {status === "error" && "Error"}
          </div>
          <span className="chat-status-note">
            {selectedRestaurant
              ? `Current restaurant: ${selectedRestaurant.name}`
              : "No restaurant selected yet."}
          </span>
        </div>

        <div className="intent-banner">
          <span className="intent-banner-label">Recognized intent</span>
          <strong>{formatIntent(latestIntent)}</strong>
        </div>

        <div className="chat-thread">
          {messages.map((message, index) => (
            <article
              key={`${message.role}-${index}`}
              className={`chat-bubble chat-bubble--${message.role}`}
            >
              <span className="chat-bubble-role">{message.role}</span>
              <p>{message.content}</p>
            </article>
          ))}
        </div>

        <form className="chat-composer" onSubmit={handleSubmit}>
          <label className="chat-label" htmlFor="chat-input">
            Ask about the selected restaurant
          </label>
          <textarea
            id="chat-input"
            className="chat-input"
            rows={4}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder={
              selectedRestaurant
                ? `Ask about ${selectedRestaurant.name}...`
                : "Select a restaurant before chatting..."
            }
            disabled={!selectedRestaurant}
          />
          <div className="chat-actions">
            <span className="chat-error">{errorMessage}</span>
            <button className="chat-submit" type="submit" disabled={status === "loading"}>
              {status === "loading" ? "Sending..." : "Send"}
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}
