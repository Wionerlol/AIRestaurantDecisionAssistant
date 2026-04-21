export type ChatRole = "user" | "assistant";

export type ChatMessage = {
  role: ChatRole;
  content: string;
};

export type ChatIntent = {
  category:
    | "recommendation"
    | "aspect"
    | "scenario"
    | "risk"
    | "summary"
    | "greeting"
    | "unknown";
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
    | "summary"
    | "greeting"
    | "unsupported";
};

export type ChatProcessTrace = {
  intent: {
    category: string;
    label: string;
    summary: string;
  };
  tool_plan: {
    reason: string | null;
    tools: {
      name: string;
      purpose: string;
    }[];
  };
  tool_execution: {
    name: string;
    status: string;
    summary: string;
  }[];
  evidence: {
    coverage: Record<string, boolean>;
    missing: string[];
  };
  answer_basis: string[];
};

export type RestaurantSummary = {
  business_id: string;
  name: string;
  city: string;
  state: string;
  stars: number | null;
  review_count: number;
  categories: string[];
};

export type RestaurantReview = {
  review_id: string;
  user_id: string;
  business_id: string;
  stars: number;
  useful: number;
  funny: number;
  cool: number;
  text: string;
  date: string;
};

export type RestaurantSearchResponse = {
  total: number;
  items: RestaurantSummary[];
};

export type RestaurantReviewsResponse = {
  business_id: string;
  total: number;
  items: RestaurantReview[];
};

export type ChatStatus = "idle" | "loading" | "error";
