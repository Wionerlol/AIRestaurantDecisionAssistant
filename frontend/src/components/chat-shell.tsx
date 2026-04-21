"use client";

import { FormEvent, useEffect, useState } from "react";

import { API_BASE_URL, buildStarterMessages } from "./chat/chat-utils";
import { RestaurantDetailPage } from "./chat/restaurant-detail-page";
import { RestaurantLandingPage } from "./chat/restaurant-landing-page";
import {
  ChatIntent,
  ChatMessage,
  ChatProcessTrace,
  ChatStatus,
  RestaurantReview,
  RestaurantReviewsResponse,
  RestaurantSearchResponse,
  RestaurantSummary,
} from "./chat/types";

export function ChatShell() {
  const [restaurants, setRestaurants] = useState<RestaurantSummary[]>([]);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [selectedRestaurant, setSelectedRestaurant] = useState<RestaurantSummary | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>(buildStarterMessages(null));
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<ChatStatus>("idle");
  const [searchStatus, setSearchStatus] = useState<ChatStatus>("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [searchError, setSearchError] = useState("");
  const [latestIntent, setLatestIntent] = useState<ChatIntent | null>(null);
  const [latestProcessTrace, setLatestProcessTrace] = useState<ChatProcessTrace | null>(
    null,
  );
  const [reviews, setReviews] = useState<RestaurantReview[]>([]);
  const [reviewsStatus, setReviewsStatus] = useState<ChatStatus>("idle");
  const [reviewsError, setReviewsError] = useState("");

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setDebouncedSearch(search);
    }, 250);

    return () => window.clearTimeout(timeoutId);
  }, [search]);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    async function loadRestaurants() {
      setSearchStatus("loading");
      setSearchError("");

      try {
        const params = new URLSearchParams({ limit: "24" });
        if (debouncedSearch.trim()) {
          params.set("query", debouncedSearch.trim());
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
  }, [debouncedSearch]);

  useEffect(() => {
    if (!selectedRestaurant) {
      setReviews([]);
      setReviewsStatus("idle");
      setReviewsError("");
      return;
    }

    let active = true;
    const controller = new AbortController();

    async function loadReviews() {
      setReviewsStatus("loading");
      setReviewsError("");

      try {
        const response = await fetch(
          `${API_BASE_URL}/restaurants/${selectedRestaurant.business_id}/reviews?limit=30`,
          { signal: controller.signal },
        );

        if (!response.ok) {
          throw new Error(`Backend returned ${response.status}`);
        }

        const payload = (await response.json()) as RestaurantReviewsResponse;
        if (!active) {
          return;
        }

        setReviews(payload.items);
        setReviewsStatus("idle");
      } catch (error) {
        if (!active || controller.signal.aborted) {
          return;
        }
        setReviewsStatus("error");
        setReviewsError(error instanceof Error ? error.message : "Unable to load reviews.");
      }
    }

    void loadReviews();

    return () => {
      active = false;
      controller.abort();
    };
  }, [selectedRestaurant]);

  function handleRestaurantSelect(restaurant: RestaurantSummary) {
    setSelectedRestaurant(restaurant);
    setMessages(buildStarterMessages(restaurant));
    setInput("");
    setStatus("idle");
    setErrorMessage("");
    setLatestIntent(null);
    setLatestProcessTrace(null);
  }

  function handleBackToSearch() {
    setSelectedRestaurant(null);
    setMessages(buildStarterMessages(null));
    setInput("");
    setStatus("idle");
    setErrorMessage("");
    setLatestIntent(null);
    setLatestProcessTrace(null);
    setReviews([]);
    setReviewsStatus("idle");
    setReviewsError("");
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
        process_trace: ChatProcessTrace;
      };

      setMessages([...nextMessages, payload.message]);
      setLatestIntent(payload.intent);
      setLatestProcessTrace(payload.process_trace);
      setStatus("idle");
    } catch (error) {
      setStatus("error");
      setErrorMessage(
        error instanceof Error ? error.message : "Unable to reach the backend.",
      );
    }
  }

  if (!selectedRestaurant) {
    return (
      <RestaurantLandingPage
        restaurants={restaurants}
        search={search}
        searchError={searchError}
        searchStatus={searchStatus}
        onSearchChange={setSearch}
        onRestaurantSelect={handleRestaurantSelect}
      />
    );
  }

  return (
    <RestaurantDetailPage
      chatErrorMessage={errorMessage}
      chatInput={input}
      chatIntent={latestIntent}
      chatMessages={messages}
      chatProcessTrace={latestProcessTrace}
      chatStatus={status}
      restaurant={selectedRestaurant}
      reviews={reviews}
      reviewsError={reviewsError}
      reviewsStatus={reviewsStatus}
      onBack={handleBackToSearch}
      onChatInputChange={setInput}
      onChatSubmit={handleSubmit}
    />
  );
}
