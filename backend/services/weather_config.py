from pydantic_settings import BaseSettings
from functools import lru_cache

# Environment variables
ENV_VARS = {
    "OPENWEATHER_API_KEY": "56dbce1abd3adbaeef3ad878a0be6c1f",
    "DEFAULT_CITY": "London"
}

class WeatherSettings(BaseSettings):
    OPENWEATHER_API_KEY: str = ENV_VARS["OPENWEATHER_API_KEY"]
    DEFAULT_CITY: str = ENV_VARS["DEFAULT_CITY"]
    WEATHER_RISK_THRESHOLD: float = 0.3  # Threshold for considering weather as a risk factor
    
    # Weather condition thresholds
    HEAVY_RAIN_THRESHOLD: float = 10.0  # mm per 3 hours
    MODERATE_RAIN_THRESHOLD: float = 2.0  # mm per 3 hours
    STRONG_WIND_THRESHOLD: float = 10.0  # m/s
    MODERATE_WIND_THRESHOLD: float = 7.0  # m/s
    HIGH_TEMP_THRESHOLD: float = 35.0  # °C
    LOW_TEMP_THRESHOLD: float = 0.0  # °C
    MODERATE_HIGH_TEMP_THRESHOLD: float = 30.0  # °C
    MODERATE_LOW_TEMP_THRESHOLD: float = 5.0  # °C

    class Config:
        env_file = ".env"

@lru_cache()
def get_weather_settings() -> WeatherSettings:
    return WeatherSettings() 