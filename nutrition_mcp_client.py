#!/usr/bin/env python3
"""
MCP Client for nutrition operations using JSON-RPC protocol
"""

import json
import asyncio
import subprocess
from typing import Dict, List, Any, Optional
from models import Recipe, NutritionProfile

class NutritionMCPClient:
    """MCP client using JSON-RPC protocol"""
    
    def __init__(self, server_script: str = "mcp_server.py"):
        self.server_script = server_script
        self.server_process = None
        self.request_id = 1
    
    async def start_server(self):
        """Start the MCP server process"""
        self.server_process = await asyncio.create_subprocess_exec(
            "uv", "run", "python", self.server_script,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="."
        )
        
        # Initialize MCP connection
        await self._initialize_connection()
    
    async def _initialize_connection(self):
        """Initialize MCP connection with handshake"""
        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "recipe-ai-client",
                    "version": "1.0.0"
                }
            }
        }
        
        init_response = await self._send_request(init_request)
        
        if "error" in init_response:
            raise RuntimeError(f"MCP initialization failed: {init_response['error']}")
        
        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        await self._send_notification(initialized_notification)
    
    def _next_id(self) -> int:
        """Get next request ID"""
        current = self.request_id
        self.request_id += 1
        return current
    
    async def _send_request(self, request: Dict) -> Dict:
        """Send request to MCP server and get response"""
        if not self.server_process:
            raise RuntimeError("Server not started")
        
        # Send request
        request_str = json.dumps(request) + "\n"
        self.server_process.stdin.write(request_str.encode())
        await self.server_process.stdin.drain()
        
        # Read response
        while True:
            line = await self.server_process.stdout.readline()
            if not line:
                raise RuntimeError("Server closed connection")
            
            try:
                response = json.loads(line.decode().strip())
                # Check if this is the response to our request
                if "id" in response and response.get("id") == request.get("id"):
                    return response
                # Skip notifications or other messages
            except json.JSONDecodeError:
                continue
    
    async def _send_notification(self, notification: Dict):
        """Send notification to MCP server"""
        if not self.server_process:
            raise RuntimeError("Server not started")
        
        notification_str = json.dumps(notification) + "\n"
        self.server_process.stdin.write(notification_str.encode())
        await self.server_process.stdin.drain()
    
    async def call_tool(self, tool_name: str, arguments: Dict) -> Any:
        """Call a tool on the MCP server"""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        response = await self._send_request(request)
        
        if "error" in response:
            raise RuntimeError(f"MCP tool error: {response['error']}")
        
        # Parse tool response
        if "result" in response and "content" in response["result"]:
            content = response["result"]["content"][0]["text"]
            return json.loads(content)
        
        return None
    
    async def calculate_recipe_nutrition(self, recipe: Recipe) -> Dict:
        """Calculate recipe nutrition using MCP server"""
        # Convert recipe ingredients to MCP format
        ingredients = []
        for ingredient in recipe.ingredients:
            try:
                quantity_grams = float(ingredient.qty.split()[0]) if ingredient.qty else 100.0
            except (ValueError, IndexError):
                quantity_grams = 100.0
            
            ingredients.append({
                "name": ingredient.item,
                "quantity_grams": quantity_grams
            })
        
        return await self.call_tool("calculate_recipe_nutrition", {
            "ingredients": ingredients
        })
    
    async def stop_server(self):
        """Stop the MCP server process"""
        if self.server_process:
            self.server_process.terminate()
            try:
                await asyncio.wait_for(self.server_process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.server_process.kill()
                await self.server_process.wait()

def compute_nutrition_mcp(recipe: Recipe) -> NutritionProfile:
    """Compute nutrition using MCP client"""
    
    async def _compute():
        client = NutritionMCPClient()
        
        try:
            await client.start_server()
            
            result = await client.calculate_recipe_nutrition(recipe)
            
            if "error" in result:
                raise ValueError(f"MCP nutrition calculation failed: {result['error']}")
            
            # Extract nutrition data
            recipe_nutrition = result.get("recipe_nutrition", {})
            
            # Convert to NutritionProfile format
            nutrition_data = {
                "calories": recipe_nutrition.get("calories", 0.0),
                "macros": {
                    "protein": recipe_nutrition.get("protein", 0.0),
                    "fat": recipe_nutrition.get("fat", 0.0),
                    "carbs": recipe_nutrition.get("carbs", 0.0)
                },
                "micros": {
                    "iron_mg": recipe_nutrition.get("iron_mg", 0.0),
                    "vitamin_c_mg": recipe_nutrition.get("vitamin_c_mg", 0.0),
                    "calcium_mg": recipe_nutrition.get("calcium_mg", 0.0),
                    "vitamin_a_mcg": recipe_nutrition.get("vitamin_a_mcg", 0.0),
                    "vitamin_d_mcg": recipe_nutrition.get("vitamin_d_mcg", 0.0),
                    "vitamin_e_mg": recipe_nutrition.get("vitamin_e_mg", 0.0),
                    "vitamin_k_mcg": recipe_nutrition.get("vitamin_k_mcg", 0.0),
                    "thiamin_mg": recipe_nutrition.get("thiamin_mg", 0.0),
                    "riboflavin_mg": recipe_nutrition.get("riboflavin_mg", 0.0),
                    "niacin_mg": recipe_nutrition.get("niacin_mg", 0.0),
                    "vitamin_b6_mg": recipe_nutrition.get("vitamin_b6_mg", 0.0),
                    "folate_mcg": recipe_nutrition.get("folate_mcg", 0.0),
                    "vitamin_b12_mcg": recipe_nutrition.get("vitamin_b12_mcg", 0.0),
                    "zinc_mg": recipe_nutrition.get("zinc_mg", 0.0),
                    "magnesium_mg": recipe_nutrition.get("magnesium_mg", 0.0),
                    "potassium_mg": recipe_nutrition.get("potassium_mg", 0.0),
                    "sodium_mg": recipe_nutrition.get("sodium_mg", 0.0)
                }
            }
            
            return NutritionProfile.model_validate(nutrition_data)
            
        finally:
            await client.stop_server()
    
    return asyncio.run(_compute())