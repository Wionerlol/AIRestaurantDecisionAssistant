import { formatCoverageKey } from "./chat-utils";
import { ChatProcessTrace } from "./types";

type ProcessTracePanelProps = {
  trace: ChatProcessTrace | null;
};

export function ProcessTracePanel({ trace }: ProcessTracePanelProps) {
  return (
    <details className="process-trace">
      <summary>
        <span>View process</span>
        <strong>
          {trace
            ? `${trace.tool_execution.length} tool step${
                trace.tool_execution.length === 1 ? "" : "s"
              }`
            : "No run yet"}
        </strong>
      </summary>

      {trace ? (
        <div className="process-trace-body">
          <section className="process-trace-section">
            <span className="process-trace-label">Intent</span>
            <p>{trace.intent.summary}</p>
          </section>

          <section className="process-trace-section">
            <span className="process-trace-label">Tool plan</span>
            <p>{trace.tool_plan.reason ?? "No tool plan was needed."}</p>
            {trace.tool_plan.tools.length > 0 && (
              <ol className="process-trace-list">
                {trace.tool_plan.tools.map((tool) => (
                  <li key={tool.name}>
                    <strong>{tool.name}</strong>
                    <span>{tool.purpose}</span>
                  </li>
                ))}
              </ol>
            )}
          </section>

          <section className="process-trace-section">
            <span className="process-trace-label">Execution</span>
            {trace.tool_execution.length > 0 ? (
              <ol className="process-trace-list">
                {trace.tool_execution.map((tool) => (
                  <li key={tool.name}>
                    <strong>
                      {tool.name} · {tool.status}
                    </strong>
                    <span>{tool.summary}</span>
                  </li>
                ))}
              </ol>
            ) : (
              <p>No database tools were called for this message.</p>
            )}
          </section>

          <section className="process-trace-section">
            <span className="process-trace-label">Evidence</span>
            <div className="process-trace-chips">
              {Object.entries(trace.evidence.coverage).map(([key, value]) => (
                <span
                  key={key}
                  className={`process-trace-chip ${
                    value ? "process-trace-chip--ok" : "process-trace-chip--missing"
                  }`}
                >
                  {formatCoverageKey(key)}
                </span>
              ))}
              {Object.keys(trace.evidence.coverage).length === 0 && (
                <span className="process-trace-chip process-trace-chip--neutral">
                  no evidence checks
                </span>
              )}
            </div>
            {trace.evidence.missing.length > 0 && (
              <p>Missing: {trace.evidence.missing.join(", ")}</p>
            )}
          </section>

          <section className="process-trace-section">
            <span className="process-trace-label">Answer basis</span>
            <ul className="process-trace-basis">
              {trace.answer_basis.map((basis) => (
                <li key={basis}>{basis}</li>
              ))}
            </ul>
          </section>
        </div>
      ) : (
        <p className="process-trace-empty">
          Send a question to see the intent, selected tools, execution status, and
          evidence coverage.
        </p>
      )}
    </details>
  );
}
