# API Contracts

This document defines the Milestone 1 API surface for deterministic restaurant and review retrieval.

## `GET /health`

Purpose:

- Verify backend availability.

Response:

```json
{
  "status": "ok"
}
```

## `GET /restaurants`

Purpose:

- List demo restaurants.
- Support simple search by restaurant name, city, or category.

Query parameters:

- `query`: optional string
- `limit`: optional integer, default `20`, max `50`

Response shape:

```json
{
  "total": 2,
  "items": [
    {
      "business_id": "ytynqOUb3hjKeJfRj5Tshw",
      "name": "Reading Terminal Market",
      "city": "Philadelphia",
      "state": "PA",
      "stars": 4.5,
      "review_count": 5721,
      "categories": ["Food Court", "Shopping", "Restaurants"]
    }
  ]
}
```

Notes:

- Results are sorted by `review_count` descending in the current implementation.
- This is a retrieval endpoint, not the final recommendation endpoint.

## `GET /restaurants/{business_id}`

Purpose:

- Fetch one restaurant by ID.

Path parameters:

- `business_id`: Yelp business identifier

Response shape:

```json
{
  "business_id": "ytynqOUb3hjKeJfRj5Tshw",
  "name": "Reading Terminal Market",
  "city": "Philadelphia",
  "state": "PA",
  "stars": 4.5,
  "review_count": 5721,
  "categories": ["Food Court", "Shopping", "Restaurants"],
  "address": "1136 Arch St",
  "postal_code": "19107",
  "is_open": 1
}
```

Error response:

```json
{
  "detail": "Restaurant not found"
}
```

## `GET /restaurants/{business_id}/reviews`

Purpose:

- Fetch reviews for one restaurant.

Path parameters:

- `business_id`: Yelp business identifier

Query parameters:

- `limit`: optional integer, default `20`, max `100`

Response shape:

```json
{
  "business_id": "ytynqOUb3hjKeJfRj5Tshw",
  "total": 3,
  "items": [
    {
      "review_id": "example-review-id",
      "user_id": "example-user-id",
      "business_id": "ytynqOUb3hjKeJfRj5Tshw",
      "stars": 4.0,
      "useful": 2,
      "funny": 0,
      "cool": 1,
      "text": "Example review text",
      "date": "2021-11-13 18:45:00"
    }
  ]
}
```

## Deferred Milestone 2+ Endpoints

These are intentionally not implemented in Milestone 1:

- `GET /restaurants/{business_id}/analysis`
- `POST /chat`
- `POST /analysis/recommendation`

Those endpoints depend on later analysis and agent work.
