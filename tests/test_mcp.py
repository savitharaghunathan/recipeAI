#!/usr/bin/env python3
"""
Test MCP server communication
"""

import asyncio
import json
from nutrition_mcp_client import NutritionMCPClient

async def test_mcp():
    """Test basic MCP communication"""
    print("Testing MCP server communication...")
    
    client = NutritionMCPClient()
    
    try:
        print("Starting server...")
        await client.start_server()
        print("✓ Server started")
        
        print("Testing tool call...")
        result = await client.call_tool("get_database_stats", {})
        print(f"✓ Tool call successful: {result}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        
        # Check if server process exists
        if client.server_process:
            print("Server process exists, checking stderr...")
            stderr = await client.server_process.stderr.read()
            if stderr:
                print(f"Server stderr: {stderr.decode()}")
    
    finally:
        await client.stop_server()

if __name__ == "__main__":
    asyncio.run(test_mcp())