import json
from typing import Any, Dict

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from src.models import Recipe


class AsyncHTTPNutritionMCPClient:
    """MCP client that connects to the nutrition server over Streamable HTTP."""

    def __init__(self, server_url: str):
        self.server_url = server_url
        self._session = None
        self._streams_context = None
        self._session_context = None

    async def connect(self):
        self._streams_context = streamablehttp_client(url=self.server_url)
        read_stream, write_stream, _ = await self._streams_context.__aenter__()
        self._session_context = ClientSession(read_stream, write_stream)
        self._session = await self._session_context.__aenter__()
        await self._session.initialize()

    async def call_tool(self, tool_name: str, arguments: Dict) -> Any:
        if not self._session:
            raise RuntimeError("Client not connected. Call connect() first.")
        result = await self._session.call_tool(tool_name, arguments)
        if result.content and len(result.content) > 0:
            return json.loads(result.content[0].text)
        return None

    async def calculate_recipe_nutrition(self, recipe: Recipe) -> Dict:
        ingredients = []
        for ingredient in recipe.ingredients:
            try:
                quantity_grams = float(ingredient.qty.split()[0]) if ingredient.qty else 100.0
            except (ValueError, IndexError):
                quantity_grams = 100.0
            ingredients.append({
                "name": ingredient.item,
                "quantity_grams": quantity_grams,
            })
        return await self.call_tool(
            "calculate_recipe_nutrition", {"ingredients": ingredients}
        )

    async def close(self):
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
            self._session_context = None
            self._session = None
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)
            self._streams_context = None
