const features = [
  "Single-restaurant analysis workflow",
  "Aspect score cards for food, service, price, ambience",
  "Pros, cons, and complaint risk summary",
  "Scenario suitability for quick decisions",
];

export default function HomePage() {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: "32px",
      }}
    >
      <section
        style={{
          width: "min(900px, 100%)",
          border: "1px solid var(--border)",
          borderRadius: "24px",
          background: "rgba(255, 250, 242, 0.88)",
          padding: "40px",
          boxShadow: "0 20px 60px rgba(73, 46, 27, 0.08)",
        }}
      >
        <p
          style={{
            margin: 0,
            color: "var(--accent-strong)",
            textTransform: "uppercase",
            letterSpacing: "0.12em",
            fontSize: "12px",
          }}
        >
          Monorepo Skeleton
        </p>
        <h1 style={{ fontSize: "clamp(40px, 7vw, 72px)", margin: "12px 0 16px" }}>
          AI Restaurant Decision Assistant
        </h1>
        <p style={{ maxWidth: "680px", color: "var(--muted)", fontSize: "18px" }}>
          The frontend shell is ready. Business workflows, LangGraph orchestration, and
          restaurant analysis screens will be added in later milestones.
        </p>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "16px",
            marginTop: "32px",
          }}
        >
          {features.map((feature) => (
            <article
              key={feature}
              style={{
                padding: "18px",
                borderRadius: "18px",
                border: "1px solid var(--border)",
                background: "#fffdf8",
              }}
            >
              {feature}
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

