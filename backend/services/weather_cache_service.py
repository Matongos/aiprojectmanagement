from typing import Dict, Optional
import json
from redis import asyncio as aioredis
import asyncio
from datetime import datetime, timedelta
from .weather_service import get_weather_service
from config import settings

class WeatherCacheService:
    def __init__(self):
        self.redis = aioredis.from_url(f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}", decode_responses=True)
        self.weather_service = get_weather_service()
        self.update_interval = settings.WEATHER_UPDATE_INTERVAL  # Get interval from settings
        print(f"Weather cache service initialized. Updates every {self.update_interval/60} minutes")
        
    async def get_cached_weather(self, city: str) -> Optional[Dict]:
        """Get weather data from cache"""
        try:
            cached_data = await self.redis.get(f"weather:{city}")
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            print(f"Error getting cached weather: {str(e)}")
            return None
            
    async def update_weather_cache(self, city: str) -> Dict:
        """Update weather data in cache"""
        try:
            forecast = await self.weather_service.get_forecast(city, days=3)
            if forecast:
                # Store in Redis with expiration
                await self.redis.setex(
                    f"weather:{city}",
                    self.update_interval,
                    json.dumps({
                        "forecast": forecast,
                        "last_updated": datetime.now().isoformat(),
                        "location": city
                    })
                )
                return forecast
        except Exception as e:
            print(f"Error updating weather cache: {str(e)}")
        return None

    async def get_weather_data(self, city: str) -> Dict:
        """Get weather data (from cache if available, otherwise fetch and cache)"""
        cached_data = await self.get_cached_weather(city)
        if cached_data:
            return cached_data
        
        # If not in cache, fetch and cache it
        forecast = await self.update_weather_cache(city)
        if forecast:
            return {
                "forecast": forecast,
                "last_updated": datetime.now().isoformat(),
                "location": city
            }
        return None

    async def start_weather_update_loop(self):
        """Background task to keep weather data updated"""
        while True:
            try:
                # Get all cached city keys
                city_keys = await self.redis.keys("weather:*")
                cities = [key.split(":")[1] for key in city_keys]  # No need to decode since we use decode_responses=True
                
                # Update each city's weather
                for city in cities:
                    await self.update_weather_cache(city)
                    await asyncio.sleep(1)  # Small delay between updates
                
                # Also update default city if not already in list
                if "London" not in cities:
                    await self.update_weather_cache("London")
                
            except Exception as e:
                print(f"Error in weather update loop: {str(e)}")
            
            await asyncio.sleep(self.update_interval)

    async def get_weather_analysis(self, city: str) -> Dict:
        """Get weather data with analysis for AI use"""
        weather_data = await self.get_weather_data(city)
        if not weather_data:
            return None
            
        forecast = weather_data["forecast"]
        if not forecast:
            return None
            
        # Calculate weather trends and analysis
        current = forecast[0]
        next_24h = forecast[:8]  # 3-hour intervals for 24 hours
        
        analysis = {
            "current_conditions": {
                "temperature": current["temp"],
                "weather": current["weather"],
                "description": current["description"],
                "risk_level": current["risk_level"]
            },
            "trends": {
                "temperature_trend": sum(w["temp"] for w in next_24h) / len(next_24h),
                "risk_levels": [w["risk_level"] for w in next_24h],
                "predominant_weather": max(
                    set(w["weather"] for w in next_24h),
                    key=lambda x: sum(1 for w in next_24h if w["weather"] == x)
                )
            },
            "recommendations": {
                "outdoor_work_suitable": all(w["risk_level"] == "low" for w in next_24h),
                "risk_hours": [
                    i * 3 for i, w in enumerate(next_24h)
                    if w["risk_level"] in ["medium", "high"]
                ]
            }
        }
        
        weather_data["analysis"] = analysis
        return weather_data

# Create singleton instance
_weather_cache_service = None

def get_weather_cache_service() -> WeatherCacheService:
    """Get or create singleton weather cache service instance"""
    global _weather_cache_service
    if _weather_cache_service is None:
        _weather_cache_service = WeatherCacheService()
    return _weather_cache_service 