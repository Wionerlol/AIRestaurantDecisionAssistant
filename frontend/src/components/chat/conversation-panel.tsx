import { FormEvent } from "react";

import { formatIntent } from "./chat-utils";
import { ProcessTracePanel } from "./process-trace-panel";
import {
  ChatIntent,
  ChatMessage,
  ChatProcessTrace,
  ChatStatus,
  RestaurantSummary,
} from "./types";

type ConversationPanelProps = {
  errorMessage: string;
  input: string;
  intent: ChatIntent | null;
  messages: ChatMessage[];
  processTrace: ChatProcessTrace | null;
  selectedRestaurant: RestaurantSummary | null;
  status: ChatStatus;
  onInputChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

export function ConversationPanel({
  errorMessage,
  input,
  intent,
  messages,
  processTrace,
  selectedRestaurant,
  status,
  onInputChange,
  onSubmit,
}: ConversationPanelProps) {
  return (
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

      <div className="conversation-inspector">
        <div className="intent-banner">
          <span className="intent-banner-label">Recognized intent</span>
          <strong>{formatIntent(intent)}</strong>
        </div>
        <ProcessTracePanel trace={processTrace} />
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

      <form className="chat-composer" onSubmit={onSubmit}>
        <label className="chat-label" htmlFor="chat-input">
          Ask about the selected restaurant
        </label>
        <textarea
          id="chat-input"
          className="chat-input"
          rows={4}
          value={input}
          onChange={(event) => onInputChange(event.target.value)}
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
  );
}
