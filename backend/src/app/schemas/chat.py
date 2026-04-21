from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str = Field(min_length=1)


class ChatRestaurantContext(BaseModel):
    business_id: str
    name: str
    city: str
    state: str
    stars: float | None = None
    review_count: int
    categories: list[str]


class ChatIntent(BaseModel):
    category: str = Field(
        pattern="^(recommendation|aspect|scenario|risk|summary|greeting|unknown)$"
    )
    label: str = Field(
        pattern="^(worth_it|should_go|food|service|price|ambience|date|family|quick_meal|complaints|warnings|summary|greeting|unsupported)$"
    )


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
    restaurant_context: ChatRestaurantContext | None = None


class ChatProcessTraceIntent(BaseModel):
    category: str
    label: str
    summary: str


class ChatProcessTraceTool(BaseModel):
    name: str
    purpose: str


class ChatProcessTraceToolPlan(BaseModel):
    reason: str | None = None
    tools: list[ChatProcessTraceTool] = Field(default_factory=list)


class ChatProcessTraceToolExecution(BaseModel):
    name: str
    status: str
    summary: str


class ChatProcessTraceEvidence(BaseModel):
    coverage: dict[str, bool] = Field(default_factory=dict)
    missing: list[str] = Field(default_factory=list)


class ChatProcessTrace(BaseModel):
    intent: ChatProcessTraceIntent
    tool_plan: ChatProcessTraceToolPlan
    tool_execution: list[ChatProcessTraceToolExecution] = Field(default_factory=list)
    evidence: ChatProcessTraceEvidence
    answer_basis: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str
    model: str
    message: ChatMessage
    intent: ChatIntent
    restaurant_context: ChatRestaurantContext | None = None
    process_trace: ChatProcessTrace
