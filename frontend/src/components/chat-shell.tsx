"use client";

import { FormEvent, useState } from "react";

type ChatRole = "user" | "assistant";

type ChatMessage = {
  role: ChatRole;
  content: string;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

const starterMessages: ChatMessage[] = [
  {
    role: "assistant",
    content:
      "Minimal LangGraph chat loop is online. Ask anything to verify the frontend-to-backend path.",
  },
];

export function ChatShell() {
  const [messages, setMessages] = useState<ChatMessage[]>(starterMessages);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

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
      };

      setMessages([...nextMessages, payload.message]);
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
        <p className="chat-eyebrow">LangChain + LangGraph</p>
        <h1 className="chat-title">Minimal Chat Console</h1>
        <p className="chat-copy">
          This page only validates the base chat loop. It does not touch restaurant
          analysis, retrieval, or recommendation workflows.
        </p>

        <div className="chat-meta-grid">
          <article className="chat-meta-card">
            <span className="chat-meta-label">Backend</span>
            <strong>{API_BASE_URL}</strong>
          </article>
          <article className="chat-meta-card">
            <span className="chat-meta-label">Endpoint</span>
            <strong>POST /chat</strong>
          </article>
          <article className="chat-meta-card">
            <span className="chat-meta-label">Default Model</span>
            <strong>stub-chat-model</strong>
          </article>
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
            {status === "loading"
              ? "Waiting for backend reply..."
              : "Messages are sent as a full conversation transcript."}
          </span>
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
            Message
          </label>
          <textarea
            id="chat-input"
            className="chat-input"
            rows={4}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Type a message to exercise the chat graph..."
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
