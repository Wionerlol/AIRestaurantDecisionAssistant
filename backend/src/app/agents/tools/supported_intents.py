from __future__ import annotations

from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.agents.graph.nodes import INTENT_TOOL_PLANS


SUPPORTED_INTENT_LABELS = [
    "worth_it",
    "should_go",
    "food",
    "service",
    "price",
    "ambience",
    "date",
    "family",
    "quick_meal",
    "complaints",
    "warnings",
    "summary",
]


class SupportedIntentsToolInput(BaseModel):
    """Input for `get_supported_intents`."""


class SupportedIntentItem(BaseModel):
    category: Literal["recommendation", "aspect", "scenario", "risk", "summary"]
    label: str
    description: str
    example_questions: list[str]
    tool_plan: list[str]
    requires_restaurant_context: bool


class SupportedIntentsData(BaseModel):
    supported_categories: list[str]
    supported_labels: list[str]
    intents: list[SupportedIntentItem]
    unsupported_guidance: str


class ToolDataSource(BaseModel):
    table: str | None
    columns: list[str]


class SupportedIntentsToolOutput(BaseModel):
    tool_name: Literal["get_supported_intents"] = "get_supported_intents"
    status: Literal["ok"] = "ok"
    data: SupportedIntentsData
    data_sources: list[ToolDataSource]
    errors: list[str] = Field(default_factory=list)


INTENT_DEFINITIONS: list[SupportedIntentItem] = [
    SupportedIntentItem(
        category="recommendation",
        label="worth_it",
        description="Judge whether the selected restaurant is worth trying.",
        example_questions=[
            "Is this restaurant worth it?",
            "Is this place worth trying?",
        ],
        tool_plan=[tool_call["name"] for tool_call in INTENT_TOOL_PLANS["worth_it"]],
        requires_restaurant_context=True,
    ),
    SupportedIntentItem(
        category="recommendation",
        label="should_go",
        description="Judge whether the user should go or skip the selected restaurant.",
        example_questions=[
            "Should I go?",
            "Should I go or skip this place?",
        ],
        tool_plan=[tool_call["name"] for tool_call in INTENT_TOOL_PLANS["should_go"]],
        requires_restaurant_context=True,
    ),
    SupportedIntentItem(
        category="aspect",
        label="food",
        description="Explain food quality using restaurant and review-level aspect evidence.",
        example_questions=[
            "How is the food here?",
            "Are the dishes good?",
        ],
        tool_plan=[tool_call["name"] for tool_call in INTENT_TOOL_PLANS["food"]],
        requires_restaurant_context=True,
    ),
    SupportedIntentItem(
        category="aspect",
        label="service",
        description="Explain service quality and service-related complaints.",
        example_questions=[
            "How is the service?",
            "Are the staff friendly?",
        ],
        tool_plan=[tool_call["name"] for tool_call in INTENT_TOOL_PLANS["service"]],
        requires_restaurant_context=True,
    ),
    SupportedIntentItem(
        category="aspect",
        label="price",
        description="Explain price, value, and expensive-or-cheap signals.",
        example_questions=[
            "Is it expensive?",
            "Is the price worth it?",
        ],
        tool_plan=[tool_call["name"] for tool_call in INTENT_TOOL_PLANS["price"]],
        requires_restaurant_context=True,
    ),
    SupportedIntentItem(
        category="aspect",
        label="ambience",
        description="Explain ambience, vibe, atmosphere, and noise signals.",
        example_questions=[
            "How is the vibe?",
            "Is the atmosphere nice?",
        ],
        tool_plan=[tool_call["name"] for tool_call in INTENT_TOOL_PLANS["ambience"]],
        requires_restaurant_context=True,
    ),
    SupportedIntentItem(
        category="scenario",
        label="date",
        description="Judge whether the selected restaurant fits a date scenario.",
        example_questions=[
            "Is it good for a date?",
            "Is this place romantic?",
        ],
        tool_plan=[tool_call["name"] for tool_call in INTENT_TOOL_PLANS["date"]],
        requires_restaurant_context=True,
    ),
    SupportedIntentItem(
        category="scenario",
        label="family",
        description="Judge whether the selected restaurant fits a family meal.",
        example_questions=[
            "Is it family friendly?",
            "Is it good with kids?",
        ],
        tool_plan=[tool_call["name"] for tool_call in INTENT_TOOL_PLANS["family"]],
        requires_restaurant_context=True,
    ),
    SupportedIntentItem(
        category="scenario",
        label="quick_meal",
        description="Judge whether the selected restaurant is good for a quick meal.",
        example_questions=[
            "Is it good for a quick meal?",
            "Can I get a quick bite here?",
        ],
        tool_plan=[tool_call["name"] for tool_call in INTENT_TOOL_PLANS["quick_meal"]],
        requires_restaurant_context=True,
    ),
    SupportedIntentItem(
        category="risk",
        label="complaints",
        description="Summarize common complaints and negative patterns.",
        example_questions=[
            "Any common complaints?",
            "What are the negative reviews saying?",
        ],
        tool_plan=[tool_call["name"] for tool_call in INTENT_TOOL_PLANS["complaints"]],
        requires_restaurant_context=True,
    ),
    SupportedIntentItem(
        category="risk",
        label="warnings",
        description="Surface risk warnings and watch-outs before deciding.",
        example_questions=[
            "Anything I should watch out for?",
            "Any warnings before I go?",
        ],
        tool_plan=[tool_call["name"] for tool_call in INTENT_TOOL_PLANS["warnings"]],
        requires_restaurant_context=True,
    ),
    SupportedIntentItem(
        category="summary",
        label="summary",
        description="Give a broad evidence-backed summary of the selected restaurant.",
        example_questions=[
            "Give me a summary.",
            "Can you summarize this restaurant?",
        ],
        tool_plan=[tool_call["name"] for tool_call in INTENT_TOOL_PLANS["summary"]],
        requires_restaurant_context=True,
    ),
]


def get_supported_intents(
    _: SupportedIntentsToolInput | None = None,
) -> SupportedIntentsToolOutput:
    """Return the supported restaurant question types and tool plans.

    Supported intents:
    - unknown: unsupported

    Use this tool when the user asks an unsupported question, asks what the
    assistant can do, or when an orchestration node needs structured guidance
    about supported restaurant intents. This tool returns supported categories,
    intent labels, example questions, whether a selected restaurant is required,
    and the deterministic tool plan associated with each supported label.

    Do not use this tool for normal restaurant-specific answers when the intent
    is already classified as supported. Use the corresponding database-backed
    tools instead.

    Reads:
    - No database tables. The output is static capability metadata derived from
      the current intent-to-tool plan.

    Input:
    - No arguments.

    Flow:
    1. Build the supported intent list from static definitions.
    2. Include the tool plan names for each intent label.
    3. Return user-facing guidance for unsupported questions.

    Output:
    - status: ok.
    - data.supported_categories: supported intent categories.
    - data.supported_labels: supported intent labels.
    - data.intents: category, label, description, examples, tool plan, and
      restaurant-context requirement.
    - data.unsupported_guidance: short fallback guidance.
    - data_sources: explicit metadata showing that no database table was read.
    - errors: always empty unless future validation is added.

    This tool does not generate final natural-language answers.
    """

    categories = list(dict.fromkeys(intent.category for intent in INTENT_DEFINITIONS))
    return SupportedIntentsToolOutput(
        data=SupportedIntentsData(
            supported_categories=categories,
            supported_labels=SUPPORTED_INTENT_LABELS,
            intents=INTENT_DEFINITIONS,
            unsupported_guidance=(
                "Ask about a selected restaurant's worth, food, service, price, "
                "ambience, date fit, family fit, quick meal fit, complaints, "
                "warnings, or summary."
            ),
        ),
        data_sources=[ToolDataSource(table=None, columns=[])],
    )


@tool(
    "get_supported_intents",
    args_schema=SupportedIntentsToolInput,
    return_direct=False,
)
def get_supported_intents_tool() -> dict:
    """Return the supported restaurant question types and tool plans.

    Supported intents:
    - unknown: unsupported

    Use this tool when the user asks an unsupported question, asks what the
    assistant can do, or when an orchestration node needs structured guidance
    about supported restaurant intents.

    Do not use this tool for normal restaurant-specific answers when the intent
    is already classified as supported.

    Reads:
    - No database tables. The output is static capability metadata.

    Input:
    - No arguments.

    Flow:
    1. Return supported categories and labels.
    2. Return example user questions for each supported label.
    3. Return the deterministic tool plan names for each label.
    4. Return fallback guidance for unsupported questions.

    Output:
    - tool_name: get_supported_intents.
    - status: ok.
    - data.supported_categories.
    - data.supported_labels.
    - data.intents.
    - data.unsupported_guidance.
    - data_sources: one metadata entry with no table.
    - errors: empty on success.

    This tool does not generate final natural-language answers.
    """

    return get_supported_intents().model_dump()
