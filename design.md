# Design: LangChain Multi-Agent Meal Planning Pipeline

---

## 1. Introduction

A minimal end-to-end proof-of-concept pipeline using multi-agents concept:

1. **Planning Agent**: Generates meal outlines based on user constraints.
2. **Chef Agent**: Produces detailed recipe steps from the meal outline.
3. **Nutrition Agent**: Computes nutritional breakdown of the generated recipe.

This document covers high-level architecture, data flows, sequence diagrams, and implementation guidance.


## 2. Goals and Constraints

**Goals**

* Validate multi-agent orchestration in LangChain.
* Produce a working pipeline: Planner → Chef → Nutrition.
* Enable iterative development and prompt tuning.

**Constraints**

* User-selected cuisine (e.g., Italian, Indian, Mexican).

* Maximum prep time (e.g., ≤30 minutes).

*Additional dietary restrictions and preferences (vegetarian, dairy-free, likes/dislikes) will be integrated in future iterations.

## 3. Architecture Overview

```plaintext
+---------+     +---------+     +-------------+
|  User   | →─▶ | Planner | →─▶ |   Chef      |
|  Input  |     | Agent   |     |   Agent     |
+---------+     +---------+     +-------------+
                                     |
                                     ↓
                               +-------------+
                               | Nutrition   |
                               | Agent       |
                               +-------------+
                                     |
                                     ↓
                               +-------------+
                               |  Output:    |
                               | Recipe +    |
                               | Nutrition   |
                               +-------------+
```

*Agents communicate via JSON payloads validated by Pydantic models.*

---

## 4. Component Details

### 4.1 Planning Agent

* **Function:** Interpret user constraints and propose a single meal outline.
* **Prompt Structure:** Few-shot examples plus JSON schema.
* **Output Model:**

```python
from pydantic import BaseModel
from typing import List

class Ingredient(BaseModel):
    item: str
    qty: str  # e.g. "100g"

class Plan(BaseModel):
    meal: str
    ingredients: List[Ingredient]
```

### 4.2 Chef Agent

* **Function:** Expand meal name + ingredients into cooking steps.
* **Prompt Structure:** Input JSON `Plan`, request recipe fields.
* **Output:** Structured JSON or Markdown containing:

  * Title
  * Prep & cook times
  * Steps (numbered list)
  * Serving size

### 4.3 Nutrition Agent

* **Function:** Lookup macro & micro data per ingredient.
* **Implementation Steps:**

  1. Parse `qty` into grams or common units.
  2. Query USDA FoodData Central API (or Edamam).
  3. Aggregate calories, carbs, protein, fat, and key micros.
  4. Return JSON:

```json
{
  "calories": 450,
  "macros": {"carbs": 60, "protein": 20, "fat": 10},
  "micros": {"iron_mg": 4.5, "vitamin_c_mg": 20}
}
```





