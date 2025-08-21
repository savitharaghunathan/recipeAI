"""
Fuzzy matching utilities for ingredient name matching
"""

from typing import List, Dict, Any
from difflib import SequenceMatcher

class FuzzyMatcher:
    """
    Fuzzy string matching for ingredient names
    """
    
    def __init__(self, min_confidence: float = 0.3):
        """
        Initialize fuzzy matcher
        
        Args:
            min_confidence: Minimum confidence score for matches (0.0-1.0)
        """
        self.min_confidence = min_confidence
    
    def find_best_matches(self, 
                         ingredient: str, 
                         food_list: List[Dict[str, Any]], 
                         limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find best matching foods for an ingredient name
        
        Args:
            ingredient: Ingredient name to match
            food_list: List of food documents from database
            limit: Maximum number of matches to return
            
        Returns:
            List of foods with match scores, sorted by confidence
        """
        scored_matches = []
        
        for food in food_list:
            score = self.calculate_match_score(ingredient, food['description'])
            
            if score >= self.min_confidence:
                match = food.copy()
                match['match_score'] = score
                scored_matches.append(match)
        
        # Sort by score (highest first) and limit results
        scored_matches.sort(key=lambda x: x['match_score'], reverse=True)
        return scored_matches[:limit]
    
    def calculate_match_score(self, ingredient: str, food_description: str) -> float:
        """
        Calculate match score between ingredient and food description
        
        Args:
            ingredient: Ingredient name (e.g., "coconut milk")
            food_description: Food description (e.g., "Milk, coconut, canned")
            
        Returns:
            Match score between 0.0 and 1.0
        """
        # Normalize strings
        ingredient_clean = self._normalize_string(ingredient)
        food_clean = self._normalize_string(food_description)
        
        # Calculate different types of similarity
        scores = []
        
        # 1. Direct string similarity (30% weight)
        string_sim = SequenceMatcher(None, ingredient_clean, food_clean).ratio()
        scores.append(string_sim * 0.3)
        
        # 2. Word overlap score (50% weight) - most important
        word_overlap = self._calculate_word_overlap(ingredient_clean, food_clean)
        scores.append(word_overlap * 0.5)
        
        # 3. Key ingredient presence (20% weight)
        key_match = self._calculate_key_ingredient_presence(ingredient_clean, food_clean)
        scores.append(key_match * 0.2)
        
        return sum(scores)
    
    def _normalize_string(self, text: str) -> str:
        """Normalize string for comparison"""
        # Convert to lowercase and remove extra whitespace
        text = text.lower().strip()
        
        # Remove punctuation that might interfere with matching
        text = text.replace(',', ' ').replace('(', ' ').replace(')', ' ')
        
        # Remove common noise words that don't help with ingredient identification
        noise_words = ['raw', 'cooked', 'fresh', 'canned', 'frozen', 'dried', 
                      'with', 'without', 'added', 'no', 'low', 'high', 'organic',
                      'prepared', 'liquid', 'expressed', 'from', 'grated', 'meat']
        
        words = text.split()
        filtered_words = [w for w in words if w not in noise_words and len(w) > 1]
        
        return ' '.join(filtered_words)
    
    def _calculate_word_overlap(self, ingredient: str, food_description: str) -> float:
        """Calculate what fraction of ingredient words appear in food description"""
        ingredient_words = set(ingredient.split())
        food_words = set(food_description.split())
        
        if not ingredient_words:
            return 0.0
        
        # Count how many ingredient words appear in food description
        matches = len(ingredient_words & food_words)
        return matches / len(ingredient_words)
    
    def _calculate_key_ingredient_presence(self, ingredient: str, food_description: str) -> float:
        """Calculate if key ingredients are present regardless of order"""
        ingredient_words = ingredient.split()
        food_words = food_description.split()
        
        if len(ingredient_words) == 1:
            # Single word ingredient - direct presence check
            return 1.0 if ingredient_words[0] in food_words else 0.0
        
        # Multi-word ingredients - check if most important words are present
        matches = sum(1 for word in ingredient_words if word in food_words)
        
        # For 2-word ingredients like "coconut milk", both words should be present
        if len(ingredient_words) == 2:
            return 1.0 if matches == 2 else 0.0
        
        # For longer ingredients, at least 2/3 of words should match
        threshold = max(2, len(ingredient_words) * 0.67)
        return 1.0 if matches >= threshold else 0.0
    
    def get_search_variations(self, ingredient: str) -> List[str]:
        """
        Generate search variations for an ingredient
        
        Args:
            ingredient: Original ingredient name
            
        Returns:
            List of search terms to try
        """
        variations = [ingredient]
        
        words = ingredient.split()
        
        # For 2-word ingredients, try reversed order
        if len(words) == 2:
            variations.append(f"{words[1]} {words[0]}")
        
        # Add individual words as fallback searches
        if len(words) > 1:
            variations.extend(words)
        
        return variations