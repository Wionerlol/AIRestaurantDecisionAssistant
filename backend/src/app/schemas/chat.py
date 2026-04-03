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
        pattern="^(recommendation|aspect|scenario|risk|summary)$"
    )
    label: str = Field(
        pattern="^(worth_it|should_go|food|service|price|ambience|date|family|quick_meal|complaints|warnings|summary)$"
    )


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
    restaurant_context: ChatRestaurantContext | None = None


class ChatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str
    model: str
    message: ChatMessage
    intent: ChatIntent
    restaurant_context: ChatRestaurantContext | None = None
