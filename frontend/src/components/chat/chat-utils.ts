import { ChatIntent, ChatMessage, RestaurantSummary } from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export const idleAssistantMessage =
  "Choose a restaurant from the search panel first. After that, every message will be sent in the context of that restaurant only.";

export function buildStarterMessages(restaurant: RestaurantSummary | null): ChatMessage[] {
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

export function formatCategories(categories: string[]) {
  return categories.filter((category) => category !== "Restaurants").slice(0, 3);
}

export function formatIntent(intent: ChatIntent | null) {
  if (!intent) {
    return "No intent classified yet";
  }

  return `${intent.category} / ${intent.label.replaceAll("_", " ")}`;
}

export function formatCoverageKey(key: string) {
  return key.replace(/^has_/, "").replaceAll("_", " ");
}
