#!/usr/bin/env python3
"""
Test MCP server communication
"""

import json
import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from nutrition_mcp.sync_mcp_client import SyncNutritionMCPClient

def test_mcp():
    """Test basic MCP communication"""
    print("Testing MCP server communication...")
    
    client = SyncNutritionMCPClient()
    
    try:
        print("Starting server...")
        client.start_server()
        print("✓ Server started")
        
        print("Testing tool call...")
        result = client.call_tool("get_database_stats", {})
        print(f"✓ Tool call successful: {result}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
    
    finally:
        client.stop_server()

if __name__ == "__main__":
    test_mcp()