# Model Design and Training Plan

This document records the proposed model design, training pipeline, inference flow, and aggregation strategy for populating the review-level and restaurant-level signal tables.

## Core Direction

Training and inference should be centered on `review_aspect_signals`.

`restaurant_aspect_signals` should not be the direct output of a restaurant-level model in the first version. It should be derived by aggregating review-level model outputs grouped by `business_id`.

```text
reviews.text
  -> review-level model inference
  -> review_aspect_signals
  -> aggregation by business_id
  -> restaurant_aspect_signals
  -> tools / LangGraph / final answer
```

## Existing Signal Tables

### `review_aspect_signals`

This table stores model output for each individual review.

| Field | Meaning | Producer |
|---|---|---|
| `review_id` | Primary key and link to `reviews.review_id`. | Database |
| `business_id` | Denormalized restaurant ID for efficient aggregation. | Database |
| `overall_sentiment_score` | Overall review sentiment score. Recommended range: `-1.0` to `1.0`. | Model |
| `overall_sentiment_label` | Overall sentiment label: `positive`, `neutral`, `negative`, or `mixed`. | Model |
| `food_score` | Food aspect score. Recommended range: `0.0` to `5.0`; `null` if not mentioned. | Model |
| `service_score` | Service aspect score. | Model |
| `price_score` | Price/value aspect score. | Model |
| `ambience_score` | Ambience/vibe/noise aspect score. | Model |
| `waiting_time_score` | Wait time / queue / speed aspect score. | Model |
| `aspect_sentiments` | JSON mapping for aspect-level sentiment labels or scores. | Model or rule layer |
| `evidence_terms` | Short terms that support the prediction, such as `slow`, `friendly`, `fresh`. | Model or rule layer |
| `pros` | Short positive evidence phrases extracted from the review. | Model or rule layer |
| `cons` | Short negative evidence phrases extracted from the review. | Model or rule layer |
| `risk_flags` | Decision-relevant risk labels, such as `long wait` or `rude service`. | Model or rule layer |
| `model_name` | Name of the model or signal generator. | Inference pipeline |
| `model_version` | Version of the model or signal generator. | Inference pipeline |
| `confidence` | Prediction confidence in the range `0.0` to `1.0`. | Model or calibration logic |
| `updated_at` | Last update timestamp. | Database |

### `restaurant_aspect_signals`

This table stores restaurant-level aggregate signals derived from review-level signals.

| Field | Meaning | Producer |
|---|---|---|
| `business_id` | Primary key and link to `restaurants.business_id`. | Database |
| `overall_rating` | Aggregated overall restaurant score. | Aggregation pipeline |
| `food_score` | Aggregated food score. | Aggregation pipeline |
| `service_score` | Aggregated service score. | Aggregation pipeline |
| `price_score` | Aggregated price/value score. | Aggregation pipeline |
| `ambience_score` | Aggregated ambience score. | Aggregation pipeline |
| `waiting_time_score` | Aggregated wait time score. | Aggregation pipeline |
| `pros` | Common strengths across reviews. | Aggregation pipeline |
| `cons` | Common weaknesses across reviews. | Aggregation pipeline |
| `risk_flags` | Common decision risks across reviews. | Aggregation pipeline |
| `updated_at` | Last update timestamp. | Database |

## Model Task Design

The review-level signal model should be treated as a multi-output pipeline rather than one monolithic task.

| Task | Input | Output | Target fields |
|---|---|---|---|
| Overall sentiment | `reviews.text` | Sentiment label and sentiment score | `overall_sentiment_label`, `overall_sentiment_score` |
| Aspect presence / relevance | `reviews.text` | Which aspects are mentioned | `aspect_sentiments`, aspect score nullability |
| Aspect scoring | `reviews.text` plus aspect | Aspect scores from `0.0` to `5.0` | `food_score`, `service_score`, `price_score`, `ambience_score`, `waiting_time_score` |
| Evidence extraction | `reviews.text` | Pros, cons, evidence terms, risks | `pros`, `cons`, `evidence_terms`, `risk_flags` |

Recommended first implementation:

```text
Model A: overall sentiment model
Model B: aspect presence / aspect score model
Rule or LLM-assisted extractor: evidence_terms, pros, cons, risk_flags
Aggregator: review_aspect_signals -> restaurant_aspect_signals
```

## MVP Pipeline

The first milestone should prioritize filling the signal tables reliably, not training the most complex possible model.

Recommended MVP sequence:

```text
1. Generate weak labels from review text, stars, and keywords.
2. Build a baseline review signal generator.
3. Write outputs into review_aspect_signals.
4. Aggregate review signals into restaurant_aspect_signals.
5. Run existing tools and LangGraph answers against populated signals.
6. Evaluate and iterate.
7. Train a sklearn or transformer model after the pipeline is stable.
```

## Weak Labeling Strategy

The Yelp review data does not provide native aspect-level labels. The first training dataset should therefore use weak labels.

### Overall sentiment labels

Use `reviews.stars` as a weak supervision source.

| Stars | Weak label | Suggested score range |
|---|---|---|
| `1` to `2` | `negative` | `-1.0` to `-0.4` |
| `3` | `neutral` or `mixed` | `-0.2` to `0.2` |
| `4` to `5` | `positive` | `0.4` to `1.0` |

Important: stars should be treated as weak labels only. A 5-star review can still contain a negative service or waiting-time signal, and a 2-star review can still praise the food.

### Aspect weak labels

Use keyword rules to detect aspect mentions.

| Aspect | Keyword examples |
|---|---|
| `food` | `food`, `dish`, `meal`, `taste`, `flavor`, `menu`, `fresh`, `cold`, `delicious` |
| `service` | `service`, `staff`, `waiter`, `waitress`, `server`, `rude`, `friendly` |
| `price` | `price`, `expensive`, `cheap`, `value`, `worth`, `cost`, `overpriced` |
| `ambience` | `ambience`, `atmosphere`, `vibe`, `noisy`, `quiet`, `crowded`, `romantic` |
| `waiting_time` | `wait`, `waiting`, `line`, `queue`, `slow`, `fast`, `quick`, `takeout` |

### Aspect score weak labels

If an aspect is mentioned, derive its score from local sentiment, aspect-specific keywords, and review stars.

If an aspect is not mentioned, write `null` for that aspect score.

Example:

```text
"The food was amazing but service was slow."
```

Suggested output:

```json
{
  "overall_sentiment_label": "mixed",
  "food_score": 4.5,
  "service_score": 2.0,
  "waiting_time_score": 2.0,
  "pros": ["amazing food"],
  "cons": ["slow service"],
  "risk_flags": ["slow service"]
}
```

## Candidate Model Approaches

### Option A: Embeddings plus sklearn baseline

Recommended first trainable model.

```text
review.text
  -> sentence embedding
  -> classifier / regressor heads
```

Suggested heads:

| Output | Model type |
|---|---|
| Overall sentiment label | `LogisticRegression`, `LinearSVC`, or calibrated classifier |
| Overall sentiment score | `Ridge`, `SVR`, or calibrated mapping |
| Aspect presence | One-vs-rest multi-label classifier |
| Aspect scores | Multi-output regressor such as `Ridge`, `RandomForest`, or `XGBoost` |
| Confidence | Class probability or heuristic calibration |

Advantages:

- Fast.
- Works without GPU.
- Easy to debug.
- Fits course-project constraints.
- Can be trained from weak labels.

Limitations:

- Limited fine-grained language understanding.
- Aspect sentiment may be weaker than transformer fine-tuning.

### Option B: Transformer multi-task fine-tuning

Possible second version.

```text
DistilBERT / MiniLM encoder
  -> sentiment classification head
  -> aspect multi-label head
  -> aspect score regression head
```

Advantages:

- Stronger semantic understanding.
- More realistic ML modeling.

Limitations:

- More training complexity.
- Requires better labels.
- More tuning and compute.

Recommendation: use Option A first. Upgrade to Option B only after the review signal pipeline and evaluation process are stable.

## Review-Level Inference Output Contract

Each review-level inference should produce a record like:

```json
{
  "review_id": "...",
  "business_id": "...",
  "overall_sentiment_score": 0.72,
  "overall_sentiment_label": "positive",
  "food_score": 4.5,
  "service_score": 3.8,
  "price_score": null,
  "ambience_score": 4.0,
  "waiting_time_score": 2.5,
  "aspect_sentiments": {
    "food": "positive",
    "service": "positive",
    "ambience": "positive",
    "waiting_time": "negative"
  },
  "evidence_terms": ["fresh", "friendly", "slow wait"],
  "pros": ["fresh food", "friendly service"],
  "cons": ["slow wait"],
  "risk_flags": ["long wait"],
  "model_name": "review-signal-baseline",
  "model_version": "v1",
  "confidence": 0.78
}
```

Field conventions:

| Field | Convention |
|---|---|
| `overall_sentiment_score` | Float from `-1.0` to `1.0`. |
| `overall_sentiment_label` | One of `positive`, `neutral`, `negative`, `mixed`. |
| Aspect scores | Float from `0.0` to `5.0`, or `null` if the aspect is not mentioned. |
| `confidence` | Float from `0.0` to `1.0`. |
| `pros`, `cons`, `risk_flags`, `evidence_terms` | Short normalized strings, not long full sentences. |
| `model_version` | Update whenever model rules, labels, or training data change. |

## Restaurant-Level Aggregation

Aggregate `review_aspect_signals` by `business_id` into `restaurant_aspect_signals`.

Basic score aggregation:

```python
restaurant.food_score = weighted_average(review.food_score)
```

Recommended first weight:

```python
weight = confidence or 0.5
```

Possible later weight:

```python
recency_weight = exp(-days_old / 365)
useful_weight = log1p(review.useful)
weight = confidence * recency_weight * (1 + 0.1 * useful_weight)
```

Possible `overall_rating` formula:

```text
0.4 * restaurant.stars
+ 0.3 * normalized_overall_sentiment
+ 0.3 * average_aspect_score
```

For the first version, it is acceptable to use:

```text
overall_rating = average of available restaurant aspect scores
```

Aggregate textual signals:

```python
pros = top_n_most_common(review_signal.pros)
cons = top_n_most_common(review_signal.cons)
risk_flags = top_n_most_common(review_signal.risk_flags)
```

## Training Dataset Shape

The initial training file can be generated as JSONL:

```text
backend/data/ml/review_signal_train.jsonl
```

Each line:

```json
{
  "review_id": "...",
  "business_id": "...",
  "text": "...",
  "stars": 4,
  "overall_sentiment_label": "positive",
  "overall_sentiment_score": 0.75,
  "aspect_presence": {
    "food": true,
    "service": true,
    "price": false,
    "ambience": false,
    "waiting_time": true
  },
  "aspect_scores": {
    "food": 4.5,
    "service": 4.0,
    "price": null,
    "ambience": null,
    "waiting_time": 2.5
  },
  "pros": ["good food", "friendly service"],
  "cons": ["long wait"],
  "risk_flags": ["long wait"]
}
```

## Suggested Project Structure

Add an ML module:

```text
backend/src/app/ml/
├─ datasets.py
├─ weak_labels.py
├─ train_review_signal_model.py
├─ predict_review_signals.py
├─ aggregate_restaurant_signals.py
├─ schemas.py
└─ artifacts/
   └─ review_signal_baseline_v1.joblib
```

Responsibilities:

| File | Responsibility |
|---|---|
| `weak_labels.py` | Generate weak labels from review text, stars, and keyword rules. |
| `datasets.py` | Load training data from database or JSONL. |
| `train_review_signal_model.py` | Train and save the baseline model. |
| `predict_review_signals.py` | Batch infer review signals and write `review_aspect_signals`. |
| `aggregate_restaurant_signals.py` | Aggregate review signals into `restaurant_aspect_signals`. |
| `schemas.py` | Define model input/output schemas. |

Candidate commands:

```bash
python -m app.ml.train_review_signal_model --database-url sqlite:///...
python -m app.ml.predict_review_signals --model-version v1
python -m app.ml.aggregate_restaurant_signals --model-version v1
```

Optional Makefile targets:

```bash
make train-review-signals
make infer-review-signals
make aggregate-restaurant-signals
```

## Evaluation Plan

Because the first labels are weak labels, evaluation should combine automatic checks and human review.

### Automatic evaluation

| Target | Metric |
|---|---|
| Overall sentiment label | Accuracy, macro F1 against holdout weak labels |
| Overall sentiment score | Pearson or Spearman correlation with normalized stars |
| Aspect detection | F1 against keyword weak labels |
| Aspect score | MAE against weak aspect scores |
| Confidence | Error rate should be lower for high-confidence samples |

### Human evaluation

Sample 100 reviews and check:

| Item | Question |
|---|---|
| Sentiment label | Does it match the review's overall tone? |
| Aspect scores | Are scores only assigned to aspects actually mentioned? |
| Pros and cons | Are phrases short, accurate, and non-duplicative? |
| Risk flags | Are risks decision-relevant? |
| Evidence terms | Do terms support ranking and retrieval? |

Sample 20 restaurants and check:

| Item | Question |
|---|---|
| Aspect aggregate scores | Do they match the overall review impression? |
| Pros and cons | Are they high-frequency themes? |
| Risk flags | Are they useful for warnings, date, family, and quick meal intents? |
| Final answer | Does LangGraph produce evidence-grounded answers? |

## Alignment With Current Tools

The existing tools already expect populated signal fields.

| Tool | Required signal fields |
|---|---|
| `get_review_aspect_evidence` | Aspect scores, sentiment, evidence terms, pros, cons, confidence. |
| `get_positive_review_patterns` | Positive sentiment, high aspect scores, pros, evidence terms. |
| `get_negative_review_patterns` | Negative sentiment, low aspect scores, cons, risk flags. |
| `get_recent_review_trend` | Review dates, sentiment labels/scores, aspect scores, risk flags. |
| `get_scenario_fit` | Aspect scores, risk flags, evidence terms. |
| `get_decision_inputs` | Aspect scores, sentiment, pros, cons, risk flags. |
| `get_restaurant_aspect_summary` | Restaurant aggregate scores, pros, cons, risk flags. |

Once `review_aspect_signals` and `restaurant_aspect_signals` are filled, the LangGraph tool chain can use the signals without changing its interface.

## Recommended Landing Order

1. Finalize signal semantics:
   - score ranges
   - label sets
   - meaning of `null`
   - risk/pros/cons phrase conventions
2. Implement weak labeling:
   - text keyword rules
   - stars-to-sentiment mapping
   - evidence term extraction
3. Implement baseline review signal inference:
   - initially rule-based
   - write `review_aspect_signals`
4. Implement restaurant aggregation:
   - read review signals
   - write `restaurant_aspect_signals`
5. Run the existing tools and graph:
   - verify answers improve with populated signals
6. Export weak labels as training data:
   - `review_signal_train.jsonl`
7. Train sklearn baseline:
   - sentiment classifier
   - aspect detector
   - aspect score regressor
8. Replace or augment rule-based inference with trained model inference.
9. Evaluate with automatic metrics and human samples.
10. Consider transformer fine-tuning only after the baseline is stable.

## First Implementation Recommendation

Start with a baseline signal pipeline before training a complex model:

```text
reviews.text + reviews.stars
  -> weak/rule-based ReviewAspectSignal
  -> aggregate RestaurantAspectSignal
```

This immediately makes the existing tools useful because the signal tables stop being empty.

After that, export the weak-labeled records and train a baseline model to replace parts of the rule system.

