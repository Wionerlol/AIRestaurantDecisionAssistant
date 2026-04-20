# LangGraph Tool Node Notes

This document is a placeholder design note for the tool-oriented LangGraph nodes that will sit between intent classification and final answer generation.

The current goal is not to finalize implementation details. The goal is to reserve the structure and vocabulary so later code, tools, prompts, and tests can converge around the same node responsibilities.

## Target Flow

```text
classify_user_intent
  -> validate_restaurant_context
  -> select_tools_for_intent
  -> run_restaurant_tools
  -> compose_decision_context
  -> generate_answer
  -> self_check_answer
```

This note focuses on three middle nodes:

| Node | Responsibility |
|---|---|
| `select_tools_for_intent` | Choose a tool plan from the classified intent label. |
| `run_restaurant_tools` | Execute the selected tools and read database-backed evidence. |
| `compose_decision_context` | Normalize tool outputs into LLM-ready context. |

## `select_tools_for_intent`

Purpose:

- Convert `intent_category` and `intent_label` into a deterministic tool plan.
- Keep tool selection predictable instead of relying entirely on free-form LLM choice.
- Provide a single place to tune which evidence each supported user question needs.

Inputs:

- `restaurant_business_id`
- `intent_category`
- `intent_label`
- latest user message

Outputs:

- `tool_plan`: ordered list of tool calls.
- `tool_plan_reason`: short explanation of why these tools were selected.
- `unsupported_reason`: optional reason when no tool plan should run.

Initial behavior:

| Intent label | Initial tool plan |
|---|---|
| `worth_it` | `get_restaurant_profile`, `get_restaurant_aspect_summary`, `get_positive_review_patterns`, `get_negative_review_patterns`, `get_decision_inputs` |
| `should_go` | `get_restaurant_profile`, `get_restaurant_aspect_summary`, `get_negative_review_patterns`, `get_decision_inputs` |
| `food` | `get_restaurant_profile`, `get_restaurant_aspect_summary`, `get_review_aspect_evidence(aspect="food")` |
| `service` | `get_restaurant_profile`, `get_restaurant_aspect_summary`, `get_review_aspect_evidence(aspect="service")`, `get_negative_review_patterns(aspect="service")` |
| `price` | `get_restaurant_profile`, `get_restaurant_aspect_summary`, `get_review_aspect_evidence(aspect="price")` |
| `ambience` | `get_restaurant_profile`, `get_restaurant_aspect_summary`, `get_review_aspect_evidence(aspect="ambience")` |
| `date` | `get_restaurant_profile`, `get_scenario_fit(scenario="date")`, `get_review_aspect_evidence(aspects=["ambience", "service", "price", "waiting_time"])`, `get_negative_review_patterns` |
| `family` | `get_restaurant_profile`, `get_scenario_fit(scenario="family")`, `get_negative_review_patterns` |
| `quick_meal` | `get_restaurant_profile`, `get_scenario_fit(scenario="quick_meal")`, `get_recent_review_trend` |
| `complaints` | `get_negative_review_patterns`, `get_review_aspect_evidence(sentiment="negative")`, `get_recent_review_trend` |
| `warnings` | `get_restaurant_aspect_summary`, `get_negative_review_patterns`, `get_recent_review_trend` |
| `summary` | `get_restaurant_profile`, `get_restaurant_aspect_summary`, `get_positive_review_patterns`, `get_negative_review_patterns`, `get_recent_review_trend` |
| `unsupported` | `get_supported_intents` |

Open decisions:

- Whether the tool plan should be pure Python routing or an LLM-assisted planner with validation.
- Whether all supported intents should require `restaurant_business_id`.
- Whether `get_decision_inputs` should be a real tool or only an internal composition helper.

## `run_restaurant_tools`

Purpose:

- Execute each tool call in `tool_plan`.
- Read the database through service-layer functions, not raw SQL inside the graph node.
- Return structured evidence without generating the final natural-language answer.

Inputs:

- `restaurant_business_id`
- `tool_plan`

Outputs:

- `tool_results`: dictionary keyed by tool name or call ID.
- `tool_errors`: recoverable errors, such as missing data or empty evidence.
- `evidence_coverage`: lightweight metadata about whether enough evidence was found.

Expected tool result categories:

- Restaurant profile.
- Restaurant-level aspect summary.
- Review-level aspect evidence.
- Positive review patterns.
- Negative review patterns.
- Scenario fit result.
- Recent review trend.
- Supported intents.

Implementation notes:

- Tools should read from `restaurants`, `reviews`, `review_aspect_signals`, and `restaurant_aspect_signals`.
- Tools should have explicit input schemas and detailed docstrings.
- Tools should return bounded evidence lists to avoid overloading the LLM context.
- The node should tolerate partial tool failures where possible and let `compose_decision_context` mark missing evidence.
- Sorting rules should be deterministic, typically by relevance, confidence, and recency.

Open decisions:

- Whether tools should be LangChain `@tool` objects immediately or plain service functions first.
- How much aggregation belongs inside tools versus inside database/service-layer queries.
- Whether this node should run independent tools sequentially or in parallel.

## `compose_decision_context`

Purpose:

- Convert raw `tool_results` into a compact, consistent context object for `generate_answer`.
- Separate data retrieval from answer composition.
- Make the final prompt stable across different intents.

Inputs:

- `intent_category`
- `intent_label`
- latest user message
- `tool_results`
- `tool_errors`

Outputs:

- `decision_context`: LLM-ready structured context.
- `answer_requirements`: constraints for the final answer.
- `missing_evidence_notes`: warnings about missing or weak evidence.

Suggested `decision_context` shape:

```json
{
  "restaurant": {},
  "intent": {
    "category": "scenario",
    "label": "date"
  },
  "summary": {
    "overall": null,
    "aspect_scores": {},
    "top_pros": [],
    "top_cons": [],
    "risk_flags": []
  },
  "evidence": {
    "positive_reviews": [],
    "negative_reviews": [],
    "scenario_reviews": [],
    "recent_reviews": []
  },
  "coverage": {
    "has_restaurant_profile": false,
    "has_restaurant_summary": false,
    "has_review_evidence": false,
    "has_scenario_fit": false
  }
}
```

Answer requirements should describe:

- Whether to give a go/skip recommendation.
- Whether to include aspect scores.
- Whether to include pros and cons.
- Whether to include risk warnings.
- Whether to mention evidence limitations.
- Whether to stay scoped to one selected restaurant.

Open decisions:

- Final shape of `decision_context`.
- Whether evidence snippets should include raw review text or compressed excerpts.
- Whether this node should perform deterministic scoring, or only organize already-computed scores.

## Relationship to Tool Mapping

The detailed intent-to-tool mapping lives in:

- [intent-tool-mapping.md](/home/louis/projects/AIRestaurantDecisionAssistant/docs/intent-tool-mapping.md)

This node note should stay higher level. If the mapping changes, update the mapping document first, then update this file only where node responsibilities change.
