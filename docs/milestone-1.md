# Milestone 1

## Goal

- Commit to a single-restaurant analysis assistant.
- Prepare a usable dataset subset.

## Decision Summary

The project is now explicitly scoped to a single-restaurant review analysis assistant. Milestone 1 does not attempt ranking, comparison, or open-domain chat. It focuses on deterministic retrieval of one restaurant and its reviews from a curated Yelp subset.

## Deliverables

### 1. Yelp field inventory

Documented in [data-model.md](/home/louis/projects/AIRestaurantDecisionAssistant/docs/data-model.md).

### 2. Singapore restaurant filtering rules

Target product rule:

1. A business must include the `Restaurants` category.
2. Geographic preference is:
   - `city == "Singapore"`, or
   - `state in {"SG", "Singapore"}`
3. A business should have enough review density for analysis:
   - recommended `review_count >= 20`
4. Reviews must exist and contain non-empty `text`.

Current dataset constraint:

- The current Yelp academic dataset in this repository has `0` businesses with Singapore geography.
- This was verified against `city`, `state`, and `address` fields.

Milestone 1 fallback:

- Use a deterministic restaurant subset from the Yelp dataset with the same business and review structure.
- Keep the product rule documented so a Singapore-source dataset can replace the demo subset later without changing the service contract.

### 3. Demo subset

Generated output:

- [demo_businesses.jsonl](/home/louis/projects/AIRestaurantDecisionAssistant/backend/data/samples/demo_businesses.jsonl)
- [demo_reviews.jsonl](/home/louis/projects/AIRestaurantDecisionAssistant/backend/data/samples/demo_reviews.jsonl)
- [demo_metadata.json](/home/louis/projects/AIRestaurantDecisionAssistant/backend/data/samples/demo_metadata.json)

Build script:

- [build_sample_dataset.py](/home/louis/projects/AIRestaurantDecisionAssistant/scripts/build_sample_dataset.py)

Current subset summary:

- `60` restaurants
- `4800` reviews
- Selection rule:
  - top `10` restaurants by `review_count` from each of 6 large Yelp cities
  - business must include `Restaurants`
  - business must have at least `50` reviews
  - retain up to `80` most recent reviews per selected restaurant

### 4. Review cleaning and storage plan

Documented in [data-model.md](/home/louis/projects/AIRestaurantDecisionAssistant/docs/data-model.md).

Short version:

- Store raw review text unchanged in JSON Lines.
- Keep review metadata intact.
- Defer heavy NLP transformations to Milestone 3.

### 5. Draft API input/output contracts

Documented in [api-contracts.md](/home/louis/projects/AIRestaurantDecisionAssistant/docs/api-contracts.md).

Implemented endpoints:

- `GET /health`
- `GET /restaurants`
- `GET /restaurants/{business_id}`
- `GET /restaurants/{business_id}/reviews`

## Done Condition Check

Milestone 1 done condition:

- The system can reliably fetch one restaurant and its reviews from the dataset.

Status:

- Satisfied.

Implementation:

- Restaurant retrieval route: [routes_restaurants.py](/home/louis/projects/AIRestaurantDecisionAssistant/backend/src/app/api/routes_restaurants.py)
- Dataset service: [yelp_data_service.py](/home/louis/projects/AIRestaurantDecisionAssistant/backend/src/app/services/yelp_data_service.py)
- Endpoint tests: [test_restaurants.py](/home/louis/projects/AIRestaurantDecisionAssistant/backend/src/app/tests/test_restaurants.py)

## Next Milestone Interface

Milestone 2 can now replace the in-memory JSON serving layer with a database-backed implementation without changing the basic restaurant and review retrieval contracts.
