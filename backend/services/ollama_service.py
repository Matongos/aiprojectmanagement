import httpx
from typing import Optional, Dict, Any
import json
import os

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=60.0)

    async def generate(
        self,
        prompt: str,
        model: str = "llama2",
        system_prompt: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a response from the Ollama model"""
        try:
            data = {
                "model": model,
                "prompt": prompt,
                "stream": stream,
                **kwargs
            }
            
            if system_prompt:
                data["system"] = system_prompt

            response = await self.client.post("/api/generate", json=data)
            response.raise_for_status()
            
            return response.json()

        except Exception as e:
            print(f"Error generating response from Ollama: {str(e)}")
            return {"error": str(e)}

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

# Singleton instance
_ollama_client = None

def get_ollama_client() -> OllamaClient:
    """Get or create singleton Ollama client instance"""
    global _ollama_client
    if _ollama_client is None:
        base_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
        _ollama_client = OllamaClient(base_url=base_url)
    return _ollama_client 