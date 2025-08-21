"""
NutritionDB - Main interface for querying nutrition data
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
from tinydb import TinyDB, Query
from utils.fuzzy_match import FuzzyMatcher
from .llm_nutrition import LLMNutritionEstimator

class NutritionDB:
    """
    Main interface for nutrition database operations
    """
    
    def __init__(self, db_path: str = "data/nutrition.json", min_confidence: float = 0.4, enable_llm: bool = True):
        """
        Initialize nutrition database
        
        Args:
            db_path: Path to TinyDB database file
            min_confidence: Minimum confidence for fuzzy matching
            enable_llm: Whether to enable LLM nutrition estimation
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")
        
        self.db = TinyDB(self.db_path)
        self.Food = Query()
        self.fuzzy_matcher = FuzzyMatcher(min_confidence=min_confidence)
        self.llm_estimator = LLMNutritionEstimator() if enable_llm else None
    
    def get_food_by_id(self, food_id: str) -> Optional[Dict[str, Any]]:
        """
        Get food by exact food_id
        
        Args:
            food_id: The food_id to search for
            
        Returns:
            Food document or None if not found
        """
        result = self.db.search(self.Food.food_id == food_id)
        return result[0] if result else None
    
    def search_by_description(self, description: str) -> List[Dict[str, Any]]:
        """
        Search foods by description (case-insensitive partial match)
        
        Args:
            description: Text to search for in food descriptions
            
        Returns:
            List of matching food documents
        """
        # Case-insensitive search
        description_lower = description.lower()
        results = self.db.search(
            self.Food.description.test(lambda desc: description_lower in desc.lower())
        )
        return results
    
    def find_ingredient(self, ingredient_name: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Find foods matching an ingredient name using fuzzy matching
        
        Args:
            ingredient_name: Name of ingredient to find
            max_results: Maximum number of results to return
            
        Returns:
            List of matching foods with match scores, sorted by confidence
        """
        # Try exact search first
        exact_matches = self.search_by_description(ingredient_name)
        if exact_matches:
            # Add perfect match score to exact matches
            for match in exact_matches:
                match['match_score'] = 1.0
            return exact_matches[:max_results]
        
        # Fall back to fuzzy matching on all foods
        all_foods = self.db.all()
        fuzzy_matches = self.fuzzy_matcher.find_best_matches(
            ingredient_name, all_foods, limit=max_results
        )
        
        return fuzzy_matches
    
    def find_or_create_ingredient(self, ingredient_name: str, auto_add: bool = True) -> Optional[Dict[str, Any]]:
        """
        Find ingredient in database, or create it using LLM if not found
        
        Args:
            ingredient_name: Name of ingredient to find
            auto_add: Whether to automatically add missing ingredients using LLM
            
        Returns:
            Food document with nutrition data, or None if not found and auto_add=False
        """
        # First try to find in database
        matches = self.find_ingredient(ingredient_name, max_results=1)
        
        if matches and matches[0].get('match_score', 0) >= 0.8:
            # High confidence match found - but check if it's complete
            match = matches[0]
            
            # Check if nutrition profile is complete (has key vitamins)
            required_fields = ['vitamin_c_mg', 'vitamin_a_mcg', 'thiamin_mg', 'riboflavin_mg']
            missing_key_fields = [field for field in required_fields if field not in match]
            
            # If it's missing key nutrition data and source is LLM estimate, get fresh data
            if missing_key_fields and match.get('source') == 'llm_estimate':
                print(f"Found incomplete nutrition data for '{ingredient_name}'. Getting complete LLM estimate...")
                # Don't return the incomplete match, proceed to LLM estimation
            else:
                return match
        
        if not auto_add:
            return None
        
        if not self.llm_estimator:
            print(f"Ingredient '{ingredient_name}' not found and LLM is disabled")
            return None
        
        # No good match found, ask LLM for nutrition data
        print(f"Ingredient '{ingredient_name}' not found in database. Getting LLM estimate...")
        
        nutrition_data = self.llm_estimator.get_nutrition_estimate_sync(ingredient_name)
        
        if not nutrition_data:
            print(f"Failed to get LLM estimate for {ingredient_name}")
            return None
        
        # Validate the LLM data
        if not self.llm_estimator.validate_nutrition_data(nutrition_data):
            print(f"LLM nutrition data for {ingredient_name} failed validation")
            return None
        
        # Add to database
        food_id = self.add_food(
            food_name=ingredient_name,
            nutrition_data=nutrition_data,
            source="llm_estimate",
            confidence=0.7
        )
        
        # Return the newly added food
        return self.get_food_by_id(food_id)
    
    def add_food(self, 
                 food_name: str, 
                 nutrition_data: Dict[str, Any], 
                 source: str = "llm_estimate",
                 confidence: float = 0.6) -> str:
        """
        Add new food to the database
        
        Args:
            food_name: Name/description of the food
            nutrition_data: Dictionary containing nutrition information
            source: Data source ('llm_estimate', 'user_added', etc.)
            confidence: Confidence score for the data (0.0-1.0)
            
        Returns:
            str: The food_id of the added food
        """
        # Generate unique food_id
        food_id = self._generate_food_id(food_name)
        
        # Create food document
        food_doc = {
            'food_id': food_id,
            'description': food_name,
            'source': source,
            'confidence': confidence,
            'nutrition_per': '100g',  # Standardize to per 100g
            'created_date': self._get_current_date()
        }
        
        # Add nutrition data
        food_doc.update(nutrition_data)
        
        # Insert into database
        self.db.insert(food_doc)
        
        return food_id
    
    def update_food_usage(self, food_id: str) -> bool:
        """
        Update usage count for a food (for tracking popularity)
        
        Args:
            food_id: ID of the food to update
            
        Returns:
            bool: True if updated successfully
        """
        food = self.get_food_by_id(food_id)
        if not food:
            return False
        
        # Update usage count
        current_usage = food.get('usage_count', 0)
        self.db.update({'usage_count': current_usage + 1}, self.Food.food_id == food_id)
        
        return True
    
    def get_foods_with_serving_sizes(self) -> List[Dict[str, Any]]:
        """
        Get all foods that have defined serving sizes
        
        Returns:
            List of foods with serving_sizes field
        """
        return self.db.search(self.Food.serving_sizes.exists())
    
    def get_high_protein_foods(self, min_protein: float = 20.0) -> List[Dict[str, Any]]:
        """
        Get foods with protein content above threshold
        
        Args:
            min_protein: Minimum protein content in grams per 100g
            
        Returns:
            List of high-protein foods
        """
        return self.db.search(
            (self.Food.protein.exists()) & (self.Food.protein >= min_protein)
        )
    
    def get_foods_by_source(self, source: str) -> List[Dict[str, Any]]:
        """
        Get foods by data source
        
        Args:
            source: Data source ('usda', 'llm_estimate', etc.)
            
        Returns:
            List of foods from specified source
        """
        return self.db.search(self.Food.source == source)
    
    def count_foods(self) -> int:
        """Get total number of foods in database"""
        return len(self.db.all())
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive database statistics
        
        Returns:
            Dictionary with database statistics
        """
        all_foods = self.db.all()
        
        return {
            'total_foods': len(all_foods),
            'foods_with_serving_sizes': len([f for f in all_foods if 'serving_sizes' in f]),
            'foods_by_source': {
                'usda': len(self.get_foods_by_source('usda')),
                'llm_estimate': len(self.get_foods_by_source('llm_estimate')),
            },
            'foods_with_protein_data': len([f for f in all_foods if 'protein' in f]),
            'foods_with_fat_data': len([f for f in all_foods if 'fat' in f]),
            'foods_with_carb_data': len([f for f in all_foods if 'carbs' in f]),
        }
    
    def close(self):
        """Close database connection"""
        self.db.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
    
    def _generate_food_id(self, food_name: str) -> str:
        """
        Generate unique food_id from food name
        
        Args:
            food_name: Name of the food
            
        Returns:
            str: Unique food_id
        """
        import re
        from datetime import datetime
        
        # Clean the name for ID generation
        clean_name = re.sub(r'[^\w\s]', '', food_name.lower())
        clean_name = re.sub(r'\s+', '_', clean_name.strip())
        
        # Truncate if too long
        if len(clean_name) > 30:
            clean_name = clean_name[:30]
        
        # Add timestamp to ensure uniqueness
        timestamp = datetime.now().strftime("%y%m%d_%H%M")
        
        return f"{clean_name}_{timestamp}"
    
    def _get_current_date(self) -> str:
        """Get current date string"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")