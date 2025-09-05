# RecipeAI

An AI-powered recipe generator with two intelligent modes: traditional cuisine-based generation and advanced ingredient-based planning using AI agents.

## What it does

### Traditional Mode (Cuisine-based)
- Generates meal plans based on cuisine type and prep time
- Creates detailed recipes with ingredients and cooking steps
- Calculates comprehensive nutritional profiles
- Respects dietary restrictions (vegan, vegetarian, etc.)

### AI Agent Mode (Ingredient-based)
- Natural language recipe requests - describe what you want in plain English
- Dynamic ingredient validation - AI agents verify and suggest alternatives using nutrition database
- Nutrition-aware recipe optimization - recipes automatically optimized for your nutrition goals
- Intelligent tool usage - LLM dynamically chooses which nutrition tools to use

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

**Traditional cuisine-based mode:**
```bash
uv run main.py --mode cuisine --cuisine thai --max-prep-time 30 --dietary-needs vegan
```

**AI agent ingredient-based mode:**
```bash
uv run main.py --mode ingredient --request "high protein vegetarian recipe with potatoes and broccoli" --nutrition-goals "high protein"
```

## MCP Server

The nutrition system uses an MCP (Model Context Protocol) server for nutrition calculations:

- **Automatic startup**: MCP server starts automatically when generating recipes
- **Automatic shutdown**: Server stops automatically after each recipe generation
- **No manual management**: No need to manually start/stop the server
- **Local operation**: Runs locally using TinyDB (348 nutrition foods database)

## Arguments

### Mode Selection
- `--mode`: Choose generation mode (`cuisine` or `ingredient`) - defaults to `cuisine`

### Cuisine Mode Arguments  
- `--cuisine`: Cuisine type (e.g., thai, indian, italian, mexican) - required
- `--max-prep-time`: Maximum preparation time in minutes - required  
- `--dietary-needs`: Optional. Dietary restrictions (e.g., vegan, vegetarian, gluten-free)

### Ingredient Mode Arguments
- `--request`: Natural language recipe request - required
- `--nutrition-goals`: Optional. Nutrition optimization goals (e.g., 'high protein', 'low carb', 'balanced')

## Sample runs

### Traditional Cuisine Mode
```bash
uv run main.py --mode cuisine --cuisine indian --max-prep-time 25 --dietary-needs vegan
```

### AI Agent Ingredient Mode  
```bash
uv run main.py --mode ingredient --request "quick healthy breakfast with eggs and spinach" --nutrition-goals "high protein"
```

```bash
uv run main.py --mode ingredient --request "vegan dinner under 10 ingredients with quinoa"
```

**Sample output:**

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

```bash
uv run main.py --mode ingredient --request "high protein vegetarian recipe with potatoes and broccoli" --nutrition-goals "high protein"


> Entering new AgentExecutor chain...
Thought: I need to find potato and broccoli in the nutrition database
Action: find_ingredient
Action Input: {"ingredient_name": "potato", "max_results": 3}{'ingredient_searched': 'potato', 'results_found': 3, 'matches': [{'ash_g': 3.06, 'calcium_mg': 42.6, 'calories': 353.0, 'carbs': 79.9, 'copper_mg': 0.208, 'description': 'Flour, potato', 'fat': 0.965, 'fiber': 6.35, 'folate_mcg': 45.4, 'food_class': 'FinalFood', 'iron_mg': 1.48, 'magnesium_mg': 84.0, 'manganese_mg': 0.611, 'niacin_mg': 6.9, 'nutrition_per': '100g', 'phosphorus_mg': 220.0, 'potassium_mg': 1520.0, 'protein': 9.14, 'riboflavin_mg': 0.13, 'sodium_mg': 17.2, 'thiamin_mg': 0.232, 'vitamin_b6_mg': 0.708, 'water_g': 6.79, 'zinc_mg': 0.944, 'food_id': 'flour_potato_174', 'source': 'usda', 'confidence': 1.0, 'match_score': 1.0}, {'ash_g': 0.915, 'calcium_mg': 5.67, 'calories': 71.6, 'carbs': 16.0, 'copper_mg': 0.13, 'description': 'Potatoes, gold, without skin, raw', 'fat': 0.225, 'food_class': 'FinalFood', 'iron_mg': 0.371, 'magnesium_mg': 22.4, 'manganese_mg': 0.148, 'niacin_mg': 1.58, 'nutrition_per': '100g', 'phosphorus_mg': 62.4, 'potassium_mg': 440.0, 'protein': 1.75, 'sugars_total': 0.645, 'thiamin_mg': 0.05, 'vitamin_b6_mg': 0.134, 'vitamin_c_mg': 23.8, 'vitamin_k_mcg': 0.7, 'water_g': 81.0, 'zinc_mg': 0.364, 'food_id': 'potatoes_gold_without_skin_raw_198', 'source': 'usda', 'confidence': 1.0, 'match_score': 1.0}, {'ash_g': 0.94, 'calcium_mg': 4.82, 'calories': 73.4, 'carbs': 16.3, 'copper_mg': 0.109, 'description': 'Potatoes, red, without skin, raw', 'fat': 0.295, 'food_class': 'FinalFood', 'iron_mg': 0.363, 'magnesium_mg': 21.8, 'manganese_mg': 0.174, 'niacin_mg': 1.38, 'nutrition_per': '100g', 'phosphorus_mg': 50.6, 'potassium_mg': 466.0, 'protein': 2.06, 'sodium_mg': 1.8, 'sugars_total': 0.664, 'thiamin_mg': 0.065, 'vitamin_b6_mg': 0.12, 'vitamin_c_mg': 21.8, 'vitamin_k_mcg': 0.7, 'water_g': 81.1, 'zinc_mg': 0.398, 'food_id': 'potatoes_red_without_skin_raw_197', 'source': 'usda', 'confidence': 1.0, 'match_score': 1.0}]} I also need to find broccoli in the nutrition database
Action: find_ingredient
Action Input: {"ingredient_name": "broccoli", "max_results": 3}{'ingredient_searched': 'broccoli', 'results_found': 1, 'matches': [{'alcohol_g': 0.059, 'ash_g': 0.83, 'calcium_mg': 46.0, 'calories': 31.0, 'carbs': 6.27, 'copper_mg': 0.063, 'description': 'Broccoli, raw', 'energy_kj': 132.0, 'fat': 0.34, 'fiber': 2.5, 'folate_mcg': 45.0, 'food_class': 'FinalFood', 'iron_mg': 0.63, 'magnesium_mg': 21.0, 'manganese_mg': 0.197, 'monounsaturated_fat_g': 0.011, 'niacin_mg': 0.609, 'nutrition_per': '100g', 'pantothenic_acid_mg': 0.62, 'phosphorus_mg': 66.0, 'polyunsaturated_fat_g': 0.017, 'potassium_mg': 306.0, 'protein': 2.57, 'riboflavin_mg': 0.112, 'saturated_fat_g': 0.039, 'selenium_mcg': 1.7, 'serving_sizes': [{'amount': 1.0, 'grams': 76.0, 'unit': 'cup'}], 'sodium_mg': 37.0, 'sugars_total': 1.4, 'thiamin_mg': 0.074, 'vitamin_a_mcg': 8.0, 'vitamin_b6_mg': 0.195, 'vitamin_c_mg': 99.3, 'vitamin_e_mg': 0.15, 'vitamin_k_mcg': 98.7, 'water_g': 90.3, 'zinc_mg': 0.42, 'food_id': 'broccoli_raw_091', 'source': 'usda', 'confidence': 1.0, 'match_score': 1.0}]} Now that I have the necessary ingredients, I'll create a simple high-protein vegetarian recipe using potatoes, broccoli, and one additional ingredient for flavor.
Final Answer: {"meal": "High Protein Broccoli and Potato Bake", "ingredients": [{"item": "potatoes", "qty": "300g"}, {"item": "broccoli", "qty": "200g"}, {"item": "cheese", "qty": "100g"}], "dietary_needs": "high protein vegetarian"}

> Finished chain.
{
  "plan": {
    "meal": "High Protein Broccoli and Potato Bake",
    "ingredients": [
      {
        "item": "potatoes",
        "qty": "300g"
      },
      {
        "item": "broccoli",
        "qty": "200g"
      },
      {
        "item": "cheese",
        "qty": "100g"
      }
    ],
    "dietary_needs": "high protein vegetarian"
  },
  "recipe": {
    "title": "High Protein Broccoli and Potato Bake with Cheese and Tofu",
    "prep_time": 15,
    "cook_time": 30,
    "ingredients": [
      {
        "item": "potatoes",
        "qty": "300g"
      },
      {
        "item": "broccoli",
        "qty": "200g"
      },
      {
        "item": "cheese",
        "qty": "100g"
      },
      {
        "item": "firm tofu",
        "qty": "200g"
      },
      {
        "item": "olive oil",
        "qty": "1 tbsp"
      },
      {
        "item": "garlic",
        "qty": "2 cloves"
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
      "Preheat the oven to 200\u00b0C (400\u00b0F).",
      "Peel and chop the potatoes into small cubes, and then steam the broccoli until tender.",
      "In a pan, heat olive oil over medium heat, then saut\u00e9 minced garlic until fragrant.",
      "Add the cubed potatoes and saut\u00e9 until golden brown, about 10 minutes.",
      "Crumble the firm tofu into the pan and cook for an additional 5 minutes.",
      "Add the steamed broccoli, and mix everything together, seasoning with salt and pepper to taste.",
      "Transfer the mixture to a baking dish, sprinkle cheese on top, and bake for 15 minutes until the cheese is melted and bubbly.",
      "Allow to cool for a few minutes before serving."
    ],
    "servings": 4
  },
  "nutrition": {
    "calories": "644.16 kcal",
    "macros": {
      "protein": "38.37 g",
      "fat": "122.07 g",
      "carbs": "36.76 g"
    },
    "micros": {
      "iron_mg": "4.22 mg",
      "vitamin_c_mg": "219.49 mg",
      "calcium_mg": "1268.59 mg",
      "vitamin_a_mcg": "766.0 mg",
      "vitamin_d_mcg": "0.4 mg",
      "vitamin_e_mg": "0.34 mg",
      "vitamin_k_mcg": "99.62 mg",
      "thiamin_mg": "0.16 mg",
      "riboflavin_mg": "0.2 mg",
      "niacin_mg": "2.81 mg",
      "vitamin_b6_mg": "0.57 mg",
      "folate_mcg": "69.4 mg",
      "vitamin_b12_mcg": "0.0 mg",
      "zinc_mg": "3.33 mg",
      "magnesium_mg": "137.21 mg",
      "potassium_mg": "1118.0 mg",
      "sodium_mg": "2168.0 mg"
    }
  }
}
```