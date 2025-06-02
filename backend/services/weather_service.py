from typing import Dict, List, Optional
import aiohttp
from datetime import datetime, timedelta
import json
from sqlalchemy.orm import Session
from config.settings import get_settings

class WeatherService:
    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.OPENWEATHER_API_KEY
        self.base_url = "http://api.openweathermap.org/data/2.5"
        
    async def get_forecast(self, city: str, days: int = 15) -> List[Dict]:
        """Get weather forecast for a city."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/forecast?q={city}&appid={self.api_key}&units=metric"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._process_forecast(data, days)
                    return []
        except Exception as e:
            print(f"Error fetching weather forecast: {str(e)}")
            return []
    
    def _process_forecast(self, data: Dict, days: int) -> List[Dict]:
        """Process raw forecast data into a simplified format."""
        forecasts = []
        try:
            current_data = data['list'][0]  # Current weather
            today_data = [item for item in data['list'][:8]]  # First 24 hours (8 x 3-hour intervals)
            
            # Calculate daily stats
            today_temps = [item['main']['temp'] for item in today_data]
            today_max_temp = max(today_temps)
            today_min_temp = min(today_temps)
            
            # Process each forecast interval
            for item in data['list'][:days * 8]:  # API returns 3-hour forecasts
                dt = datetime.fromtimestamp(item['dt'])
                
                # Calculate precipitation (rain + snow if any)
                precipitation = 0
                if 'rain' in item:
                    precipitation += item.get('rain', {}).get('3h', 0)
                if 'snow' in item:
                    precipitation += item.get('snow', {}).get('3h', 0)
                
                weather = {
                    'date': dt.date().isoformat(),
                    'time': dt.time().isoformat(),
                    'temp': item['main']['temp'],
                    'feels_like': item['main']['feels_like'],
                    'temp_min': item['main']['temp_min'],
                    'temp_max': item['main']['temp_max'],
                    'weather': item['weather'][0]['main'],
                    'description': item['weather'][0]['description'],
                    'wind_speed': item['wind']['speed'],
                    'wind_direction': item['wind'].get('deg', 0),
                    'clouds': item['clouds']['all'],  # Cloud coverage percentage
                    'precipitation': precipitation,
                    'humidity': item['main']['humidity'],
                    'pressure': item['main']['pressure'],
                    'rain': item.get('rain', {}).get('3h', 0),
                    'risk_level': self._calculate_weather_risk(item)
                }
                
                # Add additional current weather info for the first item
                if len(forecasts) == 0:
                    weather.update({
                        'is_current': True,
                        'today_max_temp': today_max_temp,
                        'today_min_temp': today_min_temp,
                        'sky_condition': 'Clear' if item['clouds']['all'] < 20 else 
                                      'Partly Cloudy' if item['clouds']['all'] < 60 else 
                                      'Cloudy',
                        'visibility': item.get('visibility', 10000) / 1000,  # Convert to km
                    })
                
                forecasts.append(weather)
        except Exception as e:
            print(f"Error processing forecast data: {str(e)}")
        return forecasts
    
    def _calculate_weather_risk(self, weather_data: Dict) -> str:
        """Calculate weather risk level."""
        risk_level = "low"
        
        # Check rain
        rain = weather_data.get('rain', {}).get('3h', 0)
        if rain > self.settings.HEAVY_RAIN_THRESHOLD:
            risk_level = "high"
        elif rain > self.settings.MODERATE_RAIN_THRESHOLD:
            risk_level = "medium"
            
        # Check wind
        wind_speed = weather_data['wind']['speed']
        if wind_speed > self.settings.STRONG_WIND_THRESHOLD:
            risk_level = "high"
        elif wind_speed > self.settings.MODERATE_WIND_THRESHOLD:
            risk_level = max(risk_level, "medium")
            
        # Check extreme temperatures
        temp = weather_data['main']['temp']
        if temp > self.settings.HIGH_TEMP_THRESHOLD or temp < self.settings.LOW_TEMP_THRESHOLD:
            risk_level = max(risk_level, "high")
        elif temp > self.settings.MODERATE_HIGH_TEMP_THRESHOLD or temp < self.settings.MODERATE_LOW_TEMP_THRESHOLD:
            risk_level = max(risk_level, "medium")
            
        return risk_level

    def extract_location_from_text(self, text: str) -> Optional[str]:
        """Extract location information from text using simple keyword matching."""
        # List of location indicators
        location_indicators = ['in', 'at', 'location:', 'site:', 'venue:', 'place:']
        
        text_lower = text.lower()
        for indicator in location_indicators:
            if indicator in text_lower:
                # Get the word after the indicator
                parts = text_lower.split(indicator)
                if len(parts) > 1:
                    location = parts[1].strip().split()[0]
                    return location.capitalize()
        return None

    def is_outdoor_task(self, description: str, name: str) -> bool:
        """Determine if a task is outdoor-related based on its description and name."""
        # Keywords indicating outdoor activities
        outdoor_keywords = [
            'outdoor', 'outside', 'exterior', 'field', 'site', 'construction',
            'drone', 'survey', 'installation', 'maintenance', 'garden', 'landscape',
            'paint', 'repair', 'build', 'inspect', 'delivery', 'event',
            'install', 'setup', 'assemble', 'mount', 'dig', 'excavate',
            'pave', 'concrete', 'roof', 'fence', 'wall', 'parking',
            'playground', 'park', 'street', 'road', 'highway', 'bridge',
            'solar', 'antenna', 'tower', 'camera', 'security', 'clean',
            'wash', 'spray', 'trim', 'cut', 'mow', 'plant', 'prune'
        ]
        
        text = f"{description} {name}".lower()
        return any(keyword in text for keyword in outdoor_keywords)

# Create a singleton instance
_weather_service = None

def get_weather_service() -> WeatherService:
    """Get or create singleton weather service instance"""
    global _weather_service
    if _weather_service is None:
        _weather_service = WeatherService()
    return _weather_service 