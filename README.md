# RecipeAI

An AI-powered recipe generator that finds recipes based on cuisine preferences, dietary restrictions, and time constraints.

## What it does

- Generates meal plans based on cuisine type and prep time
- Creates detailed recipes with ingredients and cooking steps
- Calculates comprehensive nutritional profiles
- Respects dietary restrictions (vegan, vegetarian, etc.)

## How to run

1. Install dependencies:
```bash
uv sync
```

2. Set up your OpenAI API key:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

3. Generate a recipe:
```bash
uv run main.py --cuisine thai --max-prep-time 30 --dietary-needs vegan
```

## MCP Server

The nutrition system uses an MCP (Model Context Protocol) server for nutrition calculations:

- **Automatic startup**: MCP server starts automatically when generating recipes
- **Automatic shutdown**: Server stops automatically after each recipe generation
- **No manual management**: No need to manually start/stop the server
- **Local operation**: Runs locally using TinyDB (348 nutrition foods database)

## Arguments

- `--cuisine`: Cuisine type (e.g., thai, indian, italian, mexican)
- `--max-prep-time`: Maximum preparation time in minutes
- `--dietary-needs`: Optional. Dietary restrictions (e.g., vegan, vegetarian, gluten-free)

## Sample run

```bash
$ uv run main.py --cuisine indian --max-prep-time 25 --dietary-needs vegan
```
output:

```json
{
  "plan": {
    "meal": "Chickpea Salad",
    "ingredients": [
      {
        "item": "canned chickpeas",
        "qty": "200g"
      },
      {
        "item": "tomato",
        "qty": "1"
      },
      {
        "item": "cucumber",
        "qty": "1"
      },
      {
        "item": "red onion",
        "qty": "1"
      },
      {
        "item": "lemon juice",
        "qty": "2 tbsp"
      },
      {
        "item": "olive oil",
        "qty": "1 tbsp"
      },
      {
        "item": "coriander",
        "qty": "a handful"
      },
      {
        "item": "salt",
        "qty": "to taste"
      },
      {
        "item": "pepper",
        "qty": "to taste"
      }
    ],
    "dietary_needs": "vegan"
  },
  "recipe": {
    "title": "Chickpea Salad",
    "prep_time": 10,
    "cook_time": 0,
    "ingredients": [
      {
        "item": "canned chickpeas",
        "qty": "200g"
      },
      {
        "item": "tomato",
        "qty": "1"
      },
      {
        "item": "cucumber",
        "qty": "1"
      },
      {
        "item": "red onion",
        "qty": "1"
      },
      {
        "item": "lemon juice",
        "qty": "2 tbsp"
      },
      {
        "item": "olive oil",
        "qty": "1 tbsp"
      },
      {
        "item": "coriander",
        "qty": "a handful"
      },
      {
        "item": "salt",
        "qty": "to taste"
      },
      {
        "item": "pepper",
        "qty": "to taste"
      }
    ],
    "steps": [
      "Rinse and drain the canned chickpeas.",
      "Chop the tomato, cucumber, and red onion into small pieces.",
      "In a large bowl, combine the chickpeas, chopped tomato, cucumber, and red onion.",
      "Add lemon juice, olive oil, salt, and pepper to the bowl.",
      "Mix everything together until well combined.",
      "Garnish with a handful of chopped coriander before serving."
    ],
    "servings": 2
  },
  "nutrition": {
    "calories": "210.0 kcal",
    "macros": {
      "carbs": "30.0 g",
      "protein": "10.0 g",
      "fat": "8.0 g"
    },
    "micros": {
      "iron_mg": "2.5 mg",
      "vitamin_c_mg": "20.0 mg",
      "calcium_mg": "40.0 mg",
      "vitamin_a_mcg": "500.0 mg",
      "vitamin_d_mcg": "0.0 mg",
      "vitamin_e_mg": "1.5 mg",
      "vitamin_k_mcg": "15.0 mg",
      "thiamin_mg": "0.3 mg",
      "riboflavin_mg": "0.1 mg",
      "niacin_mg": "1.0 mg",
      "vitamin_b6_mg": "0.2 mg",
      "folate_mcg": "150.0 mg",
      "vitamin_b12_mcg": "0.0 mg",
      "zinc_mg": "1.0 mg",
      "magnesium_mg": "50.0 mg",
      "potassium_mg": "400.0 mg",
      "sodium_mg": "300.0 mg"
    }
  }
}
```