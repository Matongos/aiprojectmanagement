import aiohttp
import json
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()

class OllamaClient:
    def __init__(self):
        self.base_url = os.getenv('OLLAMA_API_URL', 'http://localhost:11434')
        
    async def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a response using the Ollama API
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/api/generate"
                
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature
                    }
                }
                
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"Ollama API error: {error_text}")
                        return None
                        
                    result = await response.json()
                    return type('Response', (), {
                        'text': result.get('response', ''),
                        'model': model,
                        'usage': result.get('stats', {})
                    })
                    
        except Exception as e:
            print(f"Error calling Ollama API: {str(e)}")
            return None

_client: Optional[OllamaClient] = None

def get_ollama_client() -> OllamaClient:
    """
    Get or create an Ollama client instance
    """
    global _client
    if _client is None:
        _client = OllamaClient()
    return _client 