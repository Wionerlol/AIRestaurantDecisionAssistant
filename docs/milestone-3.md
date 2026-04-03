# Milestone 3

## Goal

- Do not implement restaurant analysis or recommendation logic yet.
- Establish the smallest extensible LangChain / LangGraph chat runtime.

## Delivered

### Minimal agent runtime

The backend now includes a minimal LangGraph chat flow:

1. accept chat messages
2. convert them into LangChain message objects
3. invoke a provider-backed chat model
4. return the assistant reply

Key files:

- [graph.py](/home/louis/projects/AIRestaurantDecisionAssistant/backend/src/app/agents/graph/graph.py)
- [nodes.py](/home/louis/projects/AIRestaurantDecisionAssistant/backend/src/app/agents/graph/nodes.py)
- [state.py](/home/louis/projects/AIRestaurantDecisionAssistant/backend/src/app/agents/graph/state.py)

### LLM integration layer

The LLM factory is provider-pluggable.

Current providers:

- `stub`
- `openai`

Key file:

- [llm.py](/home/louis/projects/AIRestaurantDecisionAssistant/backend/src/app/core/llm.py)

The `stub` provider is the default so the graph and tests can run without external credentials. Switching to OpenAI only requires environment variables.

### Chat API

Implemented endpoint:

- `POST /chat`

Files:

- [routes_chat.py](/home/louis/projects/AIRestaurantDecisionAssistant/backend/src/app/api/routes_chat.py)
- [chat.py](/home/louis/projects/AIRestaurantDecisionAssistant/backend/src/app/schemas/chat.py)
- [chat_service.py](/home/louis/projects/AIRestaurantDecisionAssistant/backend/src/app/services/chat_service.py)

Example request:

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Hello graph"
    }
  ]
}
```

Example response with the default stub provider:

```json
{
  "provider": "stub",
  "model": "stub-chat-model",
  "message": {
    "role": "assistant",
    "content": "Stub reply: Hello graph"
  }
}
```

## Configuration Externalization

Runtime configuration is now pulled from environment variables instead of being scattered through code and scripts.

Key configurable values include:

- app name, version, host, and port
- database URL and seed toggle
- PostgreSQL container credentials
- LLM provider, model, temperature, and max token budget
- OpenAI credentials and base URL
- system prompt
- stub model reply prefix

Reference file:

- [.env.example](/home/louis/projects/AIRestaurantDecisionAssistant/.env.example)

Affected runtime files:

- [config.py](/home/louis/projects/AIRestaurantDecisionAssistant/backend/src/app/core/config.py)
- [docker-compose.yml](/home/louis/projects/AIRestaurantDecisionAssistant/docker/docker-compose.yml)
- [backend.Dockerfile](/home/louis/projects/AIRestaurantDecisionAssistant/docker/backend.Dockerfile)
- [frontend.Dockerfile](/home/louis/projects/AIRestaurantDecisionAssistant/docker/frontend.Dockerfile)
- [Makefile](/home/louis/projects/AIRestaurantDecisionAssistant/Makefile)
- [dev-backend.sh](/home/louis/projects/AIRestaurantDecisionAssistant/scripts/dev-backend.sh)
- [dev-frontend.sh](/home/louis/projects/AIRestaurantDecisionAssistant/scripts/dev-frontend.sh)

## Done Condition Check

Done condition:

- the backend can accept chat messages and return an LLM-backed assistant response

Status:

- satisfied

Automated verification:

- [test_chat.py](/home/louis/projects/AIRestaurantDecisionAssistant/backend/src/app/tests/test_chat.py)

Current verification uses the `stub` provider, which still exercises the LangChain + LangGraph execution path without depending on an external API.
