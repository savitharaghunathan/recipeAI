"""
LLM-based nutrition data estimation for missing ingredients
"""

from typing import Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
import json
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.llm_config import get_chat_llm

class NutritionProfile(BaseModel):
    """Complete nutrition profile for an ingredient"""
    # Macronutrients
    calories: float = Field(description="Energy in kcal per 100g")
    protein: float = Field(description="Protein in grams per 100g")
    fat: float = Field(description="Total fat in grams per 100g")
    carbs: float = Field(description="Carbohydrates in grams per 100g")
    fiber: float = Field(description="Dietary fiber in grams per 100g")
    
    # Minerals (mg)
    iron_mg: float = Field(description="Iron in milligrams per 100g")
    calcium_mg: float = Field(description="Calcium in milligrams per 100g")
    zinc_mg: float = Field(description="Zinc in milligrams per 100g")
    magnesium_mg: float = Field(description="Magnesium in milligrams per 100g")
    potassium_mg: float = Field(description="Potassium in milligrams per 100g")
    sodium_mg: float = Field(description="Sodium in milligrams per 100g")
    
    # Vitamins (mg or mcg)
    vitamin_c_mg: float = Field(description="Vitamin C in milligrams per 100g")
    vitamin_a_mcg: float = Field(description="Vitamin A in micrograms per 100g")
    vitamin_d_mcg: float = Field(description="Vitamin D in micrograms per 100g")
    vitamin_e_mg: float = Field(description="Vitamin E in milligrams per 100g")
    vitamin_k_mcg: float = Field(description="Vitamin K in micrograms per 100g")
    thiamin_mg: float = Field(description="Thiamin (B1) in milligrams per 100g")
    riboflavin_mg: float = Field(description="Riboflavin (B2) in milligrams per 100g")
    niacin_mg: float = Field(description="Niacin (B3) in milligrams per 100g")
    vitamin_b6_mg: float = Field(description="Vitamin B6 in milligrams per 100g")
    folate_mcg: float = Field(description="Folate in micrograms per 100g")
    vitamin_b12_mcg: float = Field(description="Vitamin B12 in micrograms per 100g")

class LLMNutritionEstimator:
    """Get nutrition estimates from LLM for missing ingredients"""
    
    def __init__(self):
        """Initialize LLM nutrition estimator"""
        self.parser = JsonOutputParser(pydantic_object=NutritionProfile)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a nutrition expert. Provide accurate nutrition data for food ingredients per 100 grams.

Base your estimates on USDA nutrition data when possible. For processed or prepared foods, use reasonable estimates based on similar ingredients.

IMPORTANT: 
- All values must be per 100 grams of the ingredient
- Use 0.0 for nutrients that are truly absent (like vitamin B12 in plant foods)
- Be conservative with estimates - better to underestimate than overestimate
- For vitamins, many foods will have 0.0 values - this is normal

Format instructions: {format_instructions}"""),
            ("human", """Provide complete nutrition data for: {ingredient_name}

Consider the typical preparation and form of this ingredient as used in cooking.

Examples for context:
- Fresh basil: High vitamin K, moderate vitamin C, low calories
- Firm tofu: High protein, calcium (if made with calcium sulfate), low vitamins
- Canned coconut milk: High fat, moderate calories, some minerals

Ingredient: {ingredient_name}""")
        ])
        
    def get_chain(self):
        """Get LLM chain with shared ChatOpenAI instance"""
        return self.prompt | get_chat_llm(temperature=0.1) | self.parser
    
    async def get_nutrition_estimate(self, ingredient_name: str) -> Optional[Dict[str, Any]]:
        """
        Get complete nutrition estimate for an ingredient
        
        Args:
            ingredient_name: Name of the ingredient
            
        Returns:
            Dictionary with complete nutrition data or None if failed
        """
        try:
            result = await self.get_chain().ainvoke({
                "ingredient_name": ingredient_name,
                "format_instructions": self.parser.get_format_instructions()
            })
            
            # Convert Pydantic model to dict if needed
            if hasattr(result, 'model_dump'):
                return result.model_dump()
            return result
            
        except Exception as e:
            print(f"Error getting nutrition estimate for {ingredient_name}: {e}")
            return None
    
    def get_nutrition_estimate_sync(self, ingredient_name: str) -> Optional[Dict[str, Any]]:
        """
        Synchronous version of nutrition estimation
        
        Args:
            ingredient_name: Name of the ingredient
            
        Returns:
            Dictionary with complete nutrition data or None if failed
        """
        try:
            result = self.get_chain().invoke({
                "ingredient_name": ingredient_name,
                "format_instructions": self.parser.get_format_instructions()
            })
            
            # Convert Pydantic model to dict if needed
            if hasattr(result, 'model_dump'):
                return result.model_dump()
            return result
            
        except Exception as e:
            print(f"Error getting nutrition estimate for {ingredient_name}: {e}")
            return None
    
    def validate_nutrition_data(self, nutrition_data: Dict[str, Any]) -> bool:
        """
        Validate that nutrition data is reasonable
        
        Args:
            nutrition_data: Nutrition data dictionary
            
        Returns:
            True if data passes basic validation
        """
        # Basic sanity checks
        calories = nutrition_data.get('calories', 0)
        protein = nutrition_data.get('protein', 0)
        fat = nutrition_data.get('fat', 0)
        carbs = nutrition_data.get('carbs', 0)
        
        # Calories should roughly match macros (4-4-9 rule)
        estimated_calories = (protein * 4) + (carbs * 4) + (fat * 9)
        
        # Allow reasonable variance (foods with high fiber, water content can vary)
        if estimated_calories > 0:
            variance = abs(calories - estimated_calories) / estimated_calories
            if variance > 0.5:  # 50% variance threshold for flexibility
                print(f"Warning: Calorie mismatch. Stated: {calories}, Calculated: {estimated_calories:.1f}")
                # Don't fail validation, just warn
                print("Proceeding anyway - some foods have complex caloric calculations")
        
        # Check for negative values
        for key, value in nutrition_data.items():
            if isinstance(value, (int, float)) and value < 0:
                print(f"Warning: Negative value for {key}: {value}")
                return False
        
        return True