#!/usr/bin/env python3
"""
Setup nutrition database for first-time users
"""

from pathlib import Path
from database.converters import convert_nutrition_data

def setup_nutrition_database():
    """Initialize nutrition database from source data"""
    
    print("Setting up nutrition database...")
    
    # Check if database already exists
    if Path("data/nutrition.json").exists():
        print("Nutrition database already exists at data/nutrition.json")
        return True
    
    # Check if source data exists
    if not Path("data/complete_nutrition_database.json").exists():
        print("Source nutrition data not found at data/complete_nutrition_database.json")
        print("Please ensure the complete nutrition database file is present.")
        return False
    
    # Convert source data to TinyDB format
    print("Converting nutrition data to TinyDB format...")
    success = convert_nutrition_data(
        input_path="data/complete_nutrition_database.json",
        output_path="data/nutrition.json"
    )
    
    if success:
        print("Nutrition database setup complete!")
        print("Database: data/nutrition.json")
        print("Ready to generate recipes!")
        return True
    else:
        print("Failed to setup nutrition database")
        return False

if __name__ == "__main__":
    setup_nutrition_database()