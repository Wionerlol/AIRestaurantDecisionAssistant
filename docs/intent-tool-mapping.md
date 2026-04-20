# Intent to Tool Mapping

This document records the proposed mapping between user intent, database-backed tools, and the database fields each tool should read.

Assumption: the database tables are fully populated:

- `restaurants`
- `reviews`
- `review_aspect_signals`
- `restaurant_aspect_signals`

Design principle:

- Intent decides which tools are needed.
- Tools retrieve and lightly aggregate structured database evidence.
- LangGraph nodes compose tool outputs into the final answer.
- Review-level static model outputs should be read from `review_aspect_signals`.
- Restaurant-level aggregate summaries should be read from `restaurant_aspect_signals`.

## Core Tools

| Tool | Purpose | Main tables | Key fields |
|---|---|---|---|
| `get_restaurant_profile` | Fetch base restaurant profile. | `restaurants` | `business_id`, `name`, `city`, `state`, `address`, `stars`, `review_count`, `categories`, `is_open` |
| `get_restaurant_aspect_summary` | Fetch restaurant-level precomputed aspect and sentiment summary. | `restaurant_aspect_signals` | `overall_rating`, `food_score`, `service_score`, `price_score`, `ambience_score`, `waiting_time_score`, `pros`, `cons`, `risk_flags`, `updated_at` |
| `get_review_aspect_evidence` | Fetch review-level model outputs and supporting review text. | `reviews`, `review_aspect_signals` | `reviews.text`, `reviews.stars`, `reviews.review_date`, `overall_sentiment_score`, `overall_sentiment_label`, aspect scores, `aspect_sentiments`, `evidence_terms`, `pros`, `cons`, `risk_flags`, `confidence` |
| `get_negative_review_patterns` | Aggregate common complaints and negative patterns. | `review_aspect_signals`, `reviews`, `restaurant_aspect_signals` | `overall_sentiment_label`, `overall_sentiment_score`, `cons`, `risk_flags`, `evidence_terms`, low aspect scores, `reviews.text`, `reviews.review_date` |
| `get_positive_review_patterns` | Aggregate common strengths and positive patterns. | `review_aspect_signals`, `reviews`, `restaurant_aspect_signals` | `pros`, `aspect_sentiments`, high aspect scores, `evidence_terms`, `reviews.text` |
| `get_scenario_fit` | Judge whether the restaurant fits a target scenario. | `restaurant_aspect_signals`, `review_aspect_signals`, `reviews` | Scenario-specific aspect scores, `pros`, `cons`, `risk_flags`, `evidence_terms`, `reviews.text` |
| `get_recent_review_trend` | Summarize recent sentiment and aspect trend. | `reviews`, `review_aspect_signals` | `review_date`, `stars`, `overall_sentiment_score`, `overall_sentiment_label`, aspect scores |
| `get_decision_inputs` | Collect normalized decision context for recommendation-style answers. | `restaurants`, `restaurant_aspect_signals`, `review_aspect_signals` | Profile fields, overall scores, aspect scores, top pros, top cons, risk flags, confidence |
| `get_supported_intents` | Return supported question types when intent is unsupported. | none | Static supported-intent list |

## Intent Mapping

| Intent category | Intent label | Example user question | Recommended tools | Database fields used |
|---|---|---|---|---|
| `recommendation` | `worth_it` | Is this restaurant worth it? | `get_restaurant_profile`, `get_restaurant_aspect_summary`, `get_positive_review_patterns`, `get_negative_review_patterns`, `get_decision_inputs` | `restaurants`: `name`, `stars`, `review_count`, `categories`; `restaurant_aspect_signals`: `overall_rating`, all aspect scores, `pros`, `cons`, `risk_flags`; `review_aspect_signals`: `overall_sentiment_score`, `overall_sentiment_label`, `pros`, `cons`, `risk_flags`, `confidence`; `reviews`: `text`, `stars`, `review_date` |
| `recommendation` | `should_go` | Should I go or skip? | `get_restaurant_profile`, `get_restaurant_aspect_summary`, `get_negative_review_patterns`, `get_decision_inputs` | `restaurants`: `stars`, `review_count`, `is_open`; `restaurant_aspect_signals`: `overall_rating`, all aspect scores, `risk_flags`, `pros`, `cons`; `review_aspect_signals`: `overall_sentiment_label`, `overall_sentiment_score`, `risk_flags`, `cons`; `reviews`: evidence `text` |
| `aspect` | `food` | How is the food? | `get_restaurant_profile`, `get_restaurant_aspect_summary`, `get_review_aspect_evidence` | `restaurant_aspect_signals`: `food_score`, `pros`, `cons`; `review_aspect_signals`: `food_score`, `aspect_sentiments`, `evidence_terms`, `pros`, `cons`, `confidence`; `reviews`: `text`, `stars`, `review_date` |
| `aspect` | `service` | How is the service? | `get_restaurant_profile`, `get_restaurant_aspect_summary`, `get_review_aspect_evidence`, `get_negative_review_patterns` | `restaurant_aspect_signals`: `service_score`, `risk_flags`, `cons`; `review_aspect_signals`: `service_score`, `aspect_sentiments`, `evidence_terms`, `cons`, `risk_flags`; `reviews`: service-related `text` |
| `aspect` | `price` | Is it expensive? | `get_restaurant_profile`, `get_restaurant_aspect_summary`, `get_review_aspect_evidence` | `restaurant_aspect_signals`: `price_score`, `pros`, `cons`; `review_aspect_signals`: `price_score`, `aspect_sentiments`, `evidence_terms`, `pros`, `cons`; `reviews`: price/value-related `text` |
| `aspect` | `ambience` | How is the vibe? | `get_restaurant_profile`, `get_restaurant_aspect_summary`, `get_review_aspect_evidence` | `restaurant_aspect_signals`: `ambience_score`; `review_aspect_signals`: `ambience_score`, `aspect_sentiments`, `evidence_terms`, `pros`, `cons`; `reviews`: ambience-related `text` |
| `scenario` | `date` | Is it good for a date? | `get_restaurant_profile`, `get_scenario_fit`, `get_review_aspect_evidence`, `get_negative_review_patterns` | `restaurants`: `categories`, `stars`, `review_count`, `address`; `restaurant_aspect_signals`: `ambience_score`, `service_score`, `waiting_time_score`, `price_score`, `risk_flags`; `review_aspect_signals`: `ambience_score`, `service_score`, `waiting_time_score`, `price_score`, `aspect_sentiments`, `evidence_terms`, `pros`, `cons`, `risk_flags`; `reviews`: date, romantic, noise, service, and wait-related `text` |
| `scenario` | `family` | Is it family friendly? | `get_restaurant_profile`, `get_scenario_fit`, `get_negative_review_patterns` | `restaurants`: `categories`, `is_open`, `address`; `restaurant_aspect_signals`: `service_score`, `ambience_score`, `waiting_time_score`, `price_score`, `risk_flags`; `review_aspect_signals`: family, kids, noise, waiting, and service-related `aspect_sentiments`, `evidence_terms`, `pros`, `cons`, `risk_flags`; `reviews`: relevant `text` |
| `scenario` | `quick_meal` | Is it good for a quick meal? | `get_restaurant_profile`, `get_scenario_fit`, `get_recent_review_trend` | `restaurant_aspect_signals`: `waiting_time_score`, `service_score`, `price_score`; `review_aspect_signals`: `waiting_time_score`, `service_score`, `evidence_terms`, `risk_flags`; `reviews`: `review_date`, quick, wait, and takeout-related `text` |
| `risk` | `complaints` | Any common complaints? | `get_negative_review_patterns`, `get_review_aspect_evidence`, `get_recent_review_trend` | `review_aspect_signals`: `cons`, `risk_flags`, `overall_sentiment_label`, `overall_sentiment_score`, all aspect scores, `evidence_terms`; `reviews`: low-star or negative `text`, `stars`, `review_date`; `restaurant_aspect_signals`: `cons`, `risk_flags` |
| `risk` | `warnings` | Anything I should watch out for? | `get_negative_review_patterns`, `get_restaurant_aspect_summary`, `get_recent_review_trend` | `restaurant_aspect_signals`: `risk_flags`, `cons`, low aspect scores; `review_aspect_signals`: `risk_flags`, `cons`, `confidence`, `overall_sentiment_label`; `reviews`: evidence `text`, `review_date` |
| `summary` | `summary` | Give me a summary. | `get_restaurant_profile`, `get_restaurant_aspect_summary`, `get_positive_review_patterns`, `get_negative_review_patterns`, `get_recent_review_trend` | `restaurants`: profile fields; `restaurant_aspect_signals`: all scores, `pros`, `cons`, `risk_flags`; `review_aspect_signals`: `overall_sentiment_score`, `aspect_sentiments`, `pros`, `cons`, `risk_flags`; `reviews`: representative positive, negative, and recent `text` |
| `unknown` | `unsupported` | Tell me something random. | `get_supported_intents` | No database read. Return supported question types. |

## Tool Execution Order

| Intent label | Suggested tool execution order |
|---|---|
| `worth_it` | `get_restaurant_profile` -> `get_restaurant_aspect_summary` -> `get_positive_review_patterns` -> `get_negative_review_patterns` -> `get_decision_inputs` |
| `should_go` | `get_restaurant_profile` -> `get_restaurant_aspect_summary` -> `get_negative_review_patterns` -> `get_decision_inputs` |
| `food` | `get_restaurant_profile` -> `get_restaurant_aspect_summary` -> `get_review_aspect_evidence(aspect="food")` |
| `service` | `get_restaurant_profile` -> `get_restaurant_aspect_summary` -> `get_review_aspect_evidence(aspect="service")` -> `get_negative_review_patterns(aspect="service")` |
| `price` | `get_restaurant_profile` -> `get_restaurant_aspect_summary` -> `get_review_aspect_evidence(aspect="price")` |
| `ambience` | `get_restaurant_profile` -> `get_restaurant_aspect_summary` -> `get_review_aspect_evidence(aspect="ambience")` |
| `date` | `get_restaurant_profile` -> `get_scenario_fit(scenario="date")` -> `get_review_aspect_evidence(aspects=["ambience", "service", "price", "waiting_time"])` -> `get_negative_review_patterns` |
| `family` | `get_restaurant_profile` -> `get_scenario_fit(scenario="family")` -> `get_negative_review_patterns` |
| `quick_meal` | `get_restaurant_profile` -> `get_scenario_fit(scenario="quick_meal")` -> `get_recent_review_trend` |
| `complaints` | `get_negative_review_patterns` -> `get_review_aspect_evidence(filter="negative")` -> `get_recent_review_trend` |
| `warnings` | `get_restaurant_aspect_summary` -> `get_negative_review_patterns` -> `get_recent_review_trend` |
| `summary` | `get_restaurant_profile` -> `get_restaurant_aspect_summary` -> `get_positive_review_patterns` -> `get_negative_review_patterns` -> `get_recent_review_trend` |
| `unsupported` | `get_supported_intents` |

## Tool Input and Output Contracts

| Tool | Input | Output |
|---|---|---|
| `get_restaurant_profile` | `business_id` | Restaurant profile object. |
| `get_restaurant_aspect_summary` | `business_id` | Restaurant-level aspect summary with scores, pros, cons, risk flags, and update time. |
| `get_review_aspect_evidence` | `business_id`, optional `aspect`, optional `aspects`, optional `sentiment`, optional `limit` | Review-level evidence list with review text, aspect score, sentiment, evidence terms, and confidence. |
| `get_negative_review_patterns` | `business_id`, optional `aspect`, optional `limit` | Common negative themes, risks, and representative review snippets. |
| `get_positive_review_patterns` | `business_id`, optional `aspect`, optional `limit` | Common positive themes, strengths, and representative review snippets. |
| `get_scenario_fit` | `business_id`, `scenario` | Scenario fit score, supporting reasons, opposing reasons, risks, and representative evidence. |
| `get_recent_review_trend` | `business_id`, optional `months`, optional `limit` | Recent sentiment trend, recent positive/negative shifts, and representative reviews. |
| `get_decision_inputs` | `business_id`, `intent_label` | Normalized decision context for final recommendation generation. |
| `get_supported_intents` | none | Supported intent categories, labels, and example questions. |

## Scenario Rules

| Scenario | Priority aspects | Positive signals | Negative signals |
|---|---|---|---|
| `date` | `ambience`, `service`, `price`, `waiting_time`, `food` | Quiet, good ambience, stable service, good food, reasonable price. | Noisy, long wait, poor service, crowded, poor value. |
| `family` | `service`, `ambience`, `price`, `waiting_time`, `food` | Kid-friendly, friendly service, comfortable seating, reasonable price, reliable food. | Too noisy, long wait, small space, impatient service, expensive. |
| `quick_meal` | `waiting_time`, `service`, `price`, `food` | Fast service, short queue, efficient ordering, reasonable price. | Long wait, slow service, crowded, wrong orders. |

## Suggested LangGraph Nodes

| Node | Responsibility |
|---|---|
| `classify_user_intent` | Classify user message into category and label. |
| `validate_restaurant_context` | Ensure a `business_id` exists; otherwise ask user to select a restaurant. |
| `select_tools_for_intent` | Convert intent label into a tool plan. |
| `run_restaurant_tools` | Execute database-backed tools. |
| `compose_decision_context` | Normalize tool outputs into answer-ready context. |
| `generate_answer` | Generate the user-facing answer. |
| `self_check_answer` | Check that the answer is evidence-grounded, scoped to the selected restaurant, and includes relevant risks. |

## Recommended First Implementation Batch

| Tool | Reason |
|---|---|
| `get_restaurant_profile` | Required by every supported restaurant-specific intent. |
| `get_restaurant_aspect_summary` | Directly uses restaurant-level aggregate outputs. |
| `get_review_aspect_evidence` | Connects review-level static model outputs to final answers. |
| `get_negative_review_patterns` | Supports complaints, warnings, and scenario risk checks. |
| `get_scenario_fit` | Supports date, family, and quick meal decisions. |

## Skill and Tool Docstring Recommendation

The intent-to-tool mapping can be turned into a skill, but the skill should be used as a development and orchestration reference, not as the only runtime mechanism.

Recommended structure:

```text
skills/restaurant-decision-tools/
├─ SKILL.md
└─ references/
   └─ intent-tool-mapping.md
```

`SKILL.md` should stay concise and only explain when to use the skill, how to select tools from an intent, and when to read `references/intent-tool-mapping.md`.

The detailed mapping table should live in `references/intent-tool-mapping.md` or in this project document. Avoid duplicating large mapping tables in both places unless there is an explicit sync process.

Tool docstrings should be detailed and structured because LLM tool selection is sensitive to names, descriptions, inputs, and output contracts. Each database-backed tool should document:

- Supported intents.
- When to use the tool.
- When not to use the tool.
- Required input fields.
- Optional input fields and defaults.
- Tables and columns read.
- Output schema.
- Sorting or ranking behavior.
- Evidence limits.
- Failure behavior.

Example docstring format:

```python
def get_review_aspect_evidence(...):
    """Fetch review-level aspect and sentiment evidence for a selected restaurant.

    Use for intents that need evidence from individual reviews, including food,
    service, price, ambience, date, family, quick_meal, complaints, warnings,
    and summary.

    Reads:
    - reviews: review_id, business_id, stars, text, review_date
    - review_aspect_signals: overall_sentiment_score, overall_sentiment_label,
      food_score, service_score, price_score, ambience_score,
      waiting_time_score, aspect_sentiments, evidence_terms, pros, cons,
      risk_flags, confidence

    Inputs:
    - business_id: required selected restaurant ID.
    - aspect: optional single aspect filter.
    - aspects: optional list of aspect filters.
    - sentiment: optional positive, negative, neutral, or mixed filter.
    - limit: maximum number of evidence rows.

    Returns representative review evidence sorted by relevance, confidence,
    and recency. Does not generate final recommendations.
    """
```

Recommended approach:

- Keep this document as the canonical design reference during planning.
- If the workflow becomes stable, create a `restaurant-decision-tools` skill that points to this mapping.
- Put compact intent routing rules in the LangGraph code.
- Put rich tool-selection hints in each tool docstring.
- Do not rely on skills alone for runtime tool selection unless the application explicitly injects the skill content into the model prompt.
