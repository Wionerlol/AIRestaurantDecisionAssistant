# Session Recovery Notes

This document records the interrupted design discussion so the project can continue from the same baseline.

## Positioning

The target is not to build a full "restaurant AI platform" in one pass. The immediate goal is a course-project-grade MVP that is deliverable, demoable, and still leaves room for later evolution into tools, memory, subagents, and sandboxed workflows.

The first version should behave like a controlled analysis orchestrator rather than an autonomous agent.

## MVP Scope

The MVP solves one narrow problem: based on Yelp reviews for a single restaurant, answer whether it is worth visiting and highlight the main strengths, weaknesses, and risks.

Recommended MVP capabilities:

1. Accept a restaurant name or `restaurant_id`, then load base restaurant info and reviews.
2. Analyze reviews into aspect-level signals:
   - `food`
   - `service`
   - `price/value`
   - `ambience`
   - `waiting time`
3. Support four fixed user questions:
   - `Is this restaurant worth trying?`
   - `Is it good for a date?`
   - `Any common complaints?`
   - `Should I go or skip?`
4. Return a unified decision card with:
   - overall recommendation
   - aspect scores
   - pros / cons
   - risk flags
   - scenario suitability
   - short explanation

Design principles:

- Start with single-restaurant analysis and Q&A.
- Focus first on read data + reasoning + presentation.
- Prefer explainable output over open-ended chat.
- Keep the agent as a workflow wrapper around deterministic analysis stages.

Data source constraints for the first version:

- Use preprocessed Yelp dataset files.
- Prioritize a Singapore restaurant subset.
- Do not implement live Yelp scraping.

## Recommended Stack

### Backend

- Python 3.12
- FastAPI for HTTP APIs
- Pydantic v2 for request and response schemas
- LangGraph as the agent runtime
- LangChain for model, prompt, retriever, and tool integration
- SQLAlchemy 2.0 as the ORM / query layer
- PostgreSQL as the primary database
- `pgvector` for review embeddings
- Redis as optional cache / future session state store
- Celery or RQ only if offline ingestion or batch analysis becomes necessary later

### LLM / NLP

- Keep the LLM provider pluggable:
  - OpenAI
  - Azure OpenAI
  - Claude
- Use embeddings aligned with the selected provider ecosystem.
- Prefer a rules + LLM hybrid:
  - aspect extraction and common complaint mining can start with rules plus lightweight statistics
  - final answers and scenario judgments can be delegated to the LLM
- Do not start with fine-tuning.

### Frontend

- Next.js 15 with App Router
- TypeScript
- Tailwind CSS
- `shadcn/ui` or lightweight custom components
- Recharts if aspect scores or risk ratios need visualization

### Infra / Dev

- Docker + Docker Compose
- `uv` or Poetry for Python dependency management
- `pnpm` for frontend dependencies
- `pytest`
- `ruff` + `mypy`
- `eslint` + `prettier`

### Why this stack

- FastAPI + Next.js gives the minimum complete engineering loop.
- LangGraph allows later evolution into tools, memory, subgraphs, and subagents.
- PostgreSQL + `pgvector` is enough for a course project and small-scale validation.
- A rules + LLM hybrid is more stable and easier to defend than an all-agent design.

## Suggested Monorepo Layout

```text
AI-Restaurant-Decision-Assistant/
├─ backend/
│ ├─ pyproject.toml
│ ├─ README.md
│ ├─ src/
│ │ └─ app/
│ │   ├─ main.py
│ │   ├─ api/
│ │   │ ├─ routes_health.py
│ │   │ ├─ routes_restaurants.py
│ │   │ ├─ routes_analysis.py
│ │   │ └─ routes_chat.py
│ │   ├─ core/
│ │   │ ├─ config.py
│ │   │ ├─ logging.py
│ │   │ └─ llm.py
│ │   ├─ db/
│ │   │ ├─ base.py
│ │   │ ├─ models/
│ │   │ ├─ repositories/
│ │   │ └─ migrations/
│ │   ├─ schemas/
│ │   ├─ services/
│ │   │ ├─ restaurant_service.py
│ │   │ ├─ review_service.py
│ │   │ ├─ analysis_service.py
│ │   │ └─ recommendation_service.py
│ │   ├─ agents/
│ │   │ ├─ graph/
│ │   │ │ ├─ state.py
│ │   │ │ ├─ nodes.py
│ │   │ │ └─ graph.py
│ │   │ ├─ prompts/
│ │   │ ├─ tools/
│ │   │ └─ evaluators/
│ │   ├─ pipelines/
│ │   │ ├─ ingest_reviews.py
│ │   │ ├─ embed_reviews.py
│ │   │ └─ aggregate_aspects.py
│ │   └─ tests/
│ │    ├─ unit/
│ │    ├─ integration/
│ │    └─ evals/
│ └─ data/
│   ├─ raw/
│   ├─ processed/
│   └─ samples/
├─ frontend/
│ ├─ package.json
│ ├─ next.config.ts
│ ├─ src/
│ │ ├─ app/
│ │ │ ├─ page.tsx
│ │ │ ├─ restaurants/[id]/page.tsx
│ │ │ └─ api/
│ │ ├─ components/
│ │ │ ├─ restaurant/
│ │ │ ├─ analysis/
│ │ │ └─ chat/
│ │ ├─ lib/
│ │ │ ├─ api.ts
│ │ │ └─ types.ts
│ │ └─ styles/
├─ docker/
│ ├─ backend.Dockerfile
│ ├─ frontend.Dockerfile
│ ├─ worker.Dockerfile
│ └─ docker-compose.yml
├─ scripts/
│ ├─ bootstrap.sh
│ ├─ ingest_yelp.py
│ ├─ build_sample_dataset.py
│ ├─ run_local_eval.py
│ └─ seed_demo_data.py
├─ skills/
│ ├─ restaurant-analyst/
│ │ ├─ SKILL.md
│ │ ├─ prompts/
│ │ └─ rubrics/
│ └─ review-risk-detector/
│   ├─ SKILL.md
│   └─ prompts/
├─ docs/
│ ├─ architecture.md
│ ├─ api-contracts.md
│ ├─ data-model.md
│ └─ milestone-plan.md
├─ .env.example
├─ Makefile
└─ README.md
```

Directory rationale:

- `backend/agents` hosts the LangGraph runtime.
- `backend/services` holds business logic so the graph does not absorb everything.
- `backend/pipelines` handles ingestion, embedding, and aggregation.
- `skills/` is reserved for prompt and workflow assets, separate from core code.
- `scripts/` is for operational or one-off tasks.

## Milestones

### Milestone 1: Data and problem-boundary convergence

Goal:

- Commit to a single-restaurant analysis assistant.
- Prepare a usable dataset subset.

Expected outputs:

- Yelp field inventory
- Singapore restaurant filtering rules
- Demo subset of roughly 50 to 200 restaurants
- Review cleaning and storage plan
- Draft API input/output contracts

Done condition:

- The system can reliably fetch one restaurant and its reviews from the dataset.

### Milestone 2: Base backend and database

Goal:

- Bring up the data service.

Expected outputs:

- FastAPI project skeleton
- PostgreSQL schema
- Tables for restaurants, reviews, and precomputed aspect signals
- Basic endpoints:
  - `/restaurants/{id}`
  - `/restaurants/{id}/reviews`
- Local startup via Docker Compose

Done condition:

- Frontend or `curl` can retrieve restaurant details and review lists.

### Milestone 3: LangChain / LangGraph minimal chat loop

Goal:

- Establish the smallest extensible agent runtime before adding business workflows.

Expected outputs:

- provider-pluggable LLM client
- minimal LangGraph state and node flow
- basic multi-message chat request / response contract
- one chat endpoint wired through LangChain and LangGraph
- all runtime config externalized into environment variables

Done condition:

- The backend can accept chat messages and return an LLM-backed assistant response.

### Milestone 4: LangGraph agent loop

Goal:

- Add restaurant-specific business workflows on top of the chat runtime.

Expected outputs:

- LangGraph state definition
- Nodes for:
  - loading restaurant data
  - retrieving evidence
  - aggregating signals
  - generating the answer
  - self-checking output
- Support for the four fixed use cases
- Output that includes evidence snippets or a reasoning summary

Done condition:

- `Is it worth trying?` returns a stable answer.
- `Any common complaints?` returns recurrent negative points.

### Milestone 5: Next.js decision page

Goal:

- Build a demoable UI.

Expected outputs:

- Restaurant search or selection page
- Restaurant analysis dashboard
- Chat / Ask panel
- Decision card with:
  - overall verdict
  - aspect scores
  - pros / cons
  - risks
  - scenario suitability

Done condition:

- A user can pick a restaurant in the frontend, view the analysis, and ask a supported question.

### Milestone 6: Evaluation, stabilization, and deployment prep

Goal:

- Make the project behave more like a product than a one-off demo.

Expected outputs:

- Hardened prompts and response schemas
- Basic evaluation dataset
- Consistency and hallucination checks
- Error handling, logging, timeouts, and caching
- Dockerized deployment instructions

Done condition:

- A stable demo environment exists.
- Core question quality is reproducible.

## Explicitly Out of Scope for Phase 1

The first phase should not include:

- Multi-restaurant comparison
- Open-domain travel or food assistant behavior
- Live Yelp scraping
- True long-term memory across users
- Personalized multi-turn recommendation systems
- Complex tool-use orchestration
- Subagent architectures such as food-agent or service-agent decomposition
- Sandbox execution environments
- Admin panels or annotation back offices
- Full account systems such as login, registration, or multi-tenancy
- Production-grade multilingual support

## Suggested MVP Product Definition

One-sentence version:

> An AI assistant for single-restaurant review analysis aimed at Singapore users. After the user selects a restaurant, the system uses Yelp review data to generate structured analysis and answer whether the restaurant is worth visiting.

## Agent Role in Version 1

LangGraph should not be used as a "showcase autonomous agent" in the first release. It should be a controlled workflow that:

1. loads restaurant data
2. gathers or retrieves relevant review evidence
3. combines structured analysis outputs
4. generates the final answer
5. runs one output validation step

This framing is more stable, easier to debug, and easier to defend in a course report or demo.

## Interrupted Follow-up Topics

The interrupted session was about to continue with:

1. MVP API design draft
2. Data table design
