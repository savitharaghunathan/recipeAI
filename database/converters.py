"""
Convert nutrition data from JSON to TinyDB format
"""

import json
from pathlib import Path
from tinydb import TinyDB

def convert_nutrition_data(
    input_path: str = "data/complete_nutrition_database.json",
    output_path: str = "data/nutrition.json"
) -> bool:
    """
    Convert JSON nutrition data to TinyDB format
    
    Args:
        input_path: Path to source JSON file (relative to project root)
        output_path: Path for TinyDB output file (relative to project root)
        
    Returns:
        bool: True if conversion successful, False otherwise
    """
    input_file = Path(input_path)
    output_file = Path(output_path)
    
    if not input_file.exists():
        print(f"Error: {input_file} not found")
        return False
    
    print(f"Loading data from {input_file}")
    try:
        with open(input_file, 'r') as f:
            nutrition_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error reading JSON: {e}")
        return False
    
    print(f"Found {len(nutrition_data)} foods")
    
    # Create output directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create TinyDB database
    print(f"Creating TinyDB database: {output_file}")
    db = TinyDB(output_file)
    db.truncate()  # Clear any existing data
    
    # Convert and insert data
    converted_foods = []
    for food_id, food_data in nutrition_data.items():
        # Create new document with metadata
        food_doc = food_data.copy()
        food_doc['food_id'] = food_id
        food_doc['source'] = 'usda'
        food_doc['confidence'] = 1.0
        
        converted_foods.append(food_doc)
    
    # Insert all foods
    db.insert_multiple(converted_foods)
    db.close()
    
    print(f"Successfully converted {len(converted_foods)} foods to {output_file}")
    
    # Print statistics
    _print_conversion_stats(output_file)
    
    return True

def _print_conversion_stats(db_path: Path) -> None:
    """Print database statistics after conversion"""
    db = TinyDB(db_path)
    
    total_foods = len(db.all())
    foods_with_serving_sizes = len([f for f in db.all() if 'serving_sizes' in f])
    
    print(f"\nDatabase Statistics:")
    print(f"  Total foods: {total_foods}")
    print(f"  Foods with serving sizes: {foods_with_serving_sizes}")
    print(f"  Foods without serving sizes: {total_foods - foods_with_serving_sizes}")
    
    # Show sample
    if db.all():
        sample = db.all()[0]
        print(f"\nSample food:")
        print(f"  Description: {sample.get('description', 'Unknown')}")
        print(f"  Food ID: {sample.get('food_id')}")
        print(f"  Calories: {sample.get('calories', 'N/A')}")
        print(f"  Source: {sample.get('source', 'Unknown')}")
    
    db.close()

if __name__ == "__main__":
    success = convert_nutrition_data()
    if success:
        print("\nConversion completed successfully")
    else:
        print("\nConversion failed")