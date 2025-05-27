import aiohttp
import json
from typing import Dict, Optional, Any

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.session = None

    async def _ensure_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def generate(
        self,
        model: str,
        prompt: str,
        stream: bool = False,
        options: Optional[Dict[str, Any]] = None
    ):
        """Generate a response from Ollama"""
        await self._ensure_session()
        
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            **(options or {})
        }
        
        try:
            async with self.session.post(url, json=payload) as response:
                if stream:
                    return response  # Return the response object for streaming
                else:
                    text = await response.text()
                    return type('Response', (), {'text': text})()
        except Exception as e:
            print(f"Error calling Ollama API: {str(e)}")
            # Return a dummy response object with empty text
            return type('Response', (), {'text': '{}'})()

    async def close(self):
        """Close the client session"""
        if self.session:
            await self.session.close()
            self.session = None

_ollama_client = None

def get_ollama_client() -> OllamaClient:
    """Get or create a singleton Ollama client"""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client 