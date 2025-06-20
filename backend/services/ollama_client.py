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
                    # NDJSON streaming: print and collect all response chunks
                    responses = []
                    last_result = None
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if not line:
                            continue
                        print(f"Ollama NDJSON line: {line}")  # Debug print
                        try:
                            result = json.loads(line)
                            if 'response' in result:
                                responses.append(result['response'])
                            last_result = result
                        except Exception as e:
                            print(f"Error parsing NDJSON line: {e} | line: {line}")
                            continue
                    full_response = ''.join(responses)
                    if full_response:
                        return type('Response', (), {
                            'text': full_response,
                            'model': model,
                            'usage': last_result.get('stats', {}) if last_result else {}
                        })()
                    else:
                        print("No valid response text received from Ollama.")
                        return None
                    
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