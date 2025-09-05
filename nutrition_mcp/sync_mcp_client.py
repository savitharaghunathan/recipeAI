#!/usr/bin/env python3
"""
Synchronous MCP Client for nutrition operations using blocking subprocess communication
"""

import json
import subprocess
from typing import Dict, Any
from src.models import Recipe


class SyncNutritionMCPClient:
    """Synchronous MCP client using blocking subprocess communication"""
    
    def __init__(self, server_script: str = "nutrition_mcp/mcp_server.py"):
        self.server_script = server_script
        self.server_process = None
        self.request_id = 1
    
    def start_server(self):
        """Start the MCP server process"""
        self.server_process = subprocess.Popen(
            ["uv", "run", "python", self.server_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0,  # Unbuffered for immediate I/O
            cwd="."
        )
        
        # Initialize MCP connection
        self._initialize_connection()
    
    def _initialize_connection(self):
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
        
        init_response = self._send_request(init_request)
        
        if "error" in init_response:
            raise RuntimeError(f"MCP initialization failed: {init_response['error']}")
        
        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        self._send_notification(initialized_notification)
    
    def _next_id(self) -> int:
        """Get next request ID"""
        current = self.request_id
        self.request_id += 1
        return current
    
    def _send_request(self, request: Dict) -> Dict:
        """Send request to MCP server and get response"""
        if not self.server_process:
            raise RuntimeError("Server not started")
        
        # Send request
        request_str = json.dumps(request) + "\n"
        self.server_process.stdin.write(request_str)
        self.server_process.stdin.flush()
        
        # Read response
        while True:
            line = self.server_process.stdout.readline()
            if not line:
                raise RuntimeError("Server closed connection")
            
            try:
                response = json.loads(line.strip())
                # Check if this is the response to our request
                if "id" in response and response.get("id") == request.get("id"):
                    return response
                # Skip notifications or other messages
            except json.JSONDecodeError:
                continue
    
    def _send_notification(self, notification: Dict):
        """Send notification to MCP server"""
        if not self.server_process:
            raise RuntimeError("Server not started")
        
        notification_str = json.dumps(notification) + "\n"
        self.server_process.stdin.write(notification_str)
        self.server_process.stdin.flush()
    
    def call_tool(self, tool_name: str, arguments: Dict) -> Any:
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
        
        response = self._send_request(request)
        
        if "error" in response:
            raise RuntimeError(f"MCP tool error: {response['error']}")
        
        # Parse tool response
        if "result" in response and "content" in response["result"]:
            content = response["result"]["content"][0]["text"]
            return json.loads(content)
        
        return None
    
    def calculate_recipe_nutrition(self, recipe: Recipe) -> Dict:
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
        
        return self.call_tool("calculate_recipe_nutrition", {
            "ingredients": ingredients
        })
    
    def stop_server(self):
        """Stop the MCP server process"""
        if self.server_process:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                self.server_process.wait()


