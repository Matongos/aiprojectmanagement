from fastapi import APIRouter, HTTPException, Depends, Request
from services.weather_service import get_weather_service
from services.weather_cache_service import get_weather_cache_service
import httpx
from typing import Dict, Optional
from fastapi.responses import JSONResponse
from datetime import datetime

router = APIRouter(
    prefix="/api/weather",
    tags=["weather"]
)

async def get_location_from_ip(ip_address: str) -> Dict:
    """Get location from IP address using ipapi.co service"""
    try:
        # Don't try to geolocate local IPs
        if ip_address in ['127.0.0.1', 'localhost', '::1']:
            print(f"Local IP detected: {ip_address}, using default location")
            return {'city': 'Harare', 'country': 'Zimabwbe', 'latitude': 51.5074, 'longitude': -0.1278}
            
        async with httpx.AsyncClient() as client:
            print(f"Attempting to geolocate IP: {ip_address}")
            response = await client.get(f'https://ipapi.co/{ip_address}/json/')
            print(f"Geolocation response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Geolocation data received: {data}")
                
                # Validate the response data
                if not data.get('city'):
                    print("No city found in geolocation data")
                    raise ValueError("No city found in geolocation data")
                    
                return {
                    'city': data['city'],  # Remove default to force error if city not found
                    'country': data.get('country_name', 'Unknown'),
                    'latitude': data.get('latitude', 0),
                    'longitude': data.get('longitude', 0)
                }
            else:
                print(f"Geolocation service returned error: {response.status_code}")
                raise ValueError(f"Geolocation service error: {response.status_code}")
                
    except Exception as e:
        print(f"Error getting location from IP: {str(e)}")
        # Return a default location but log the error
        return {'city': 'harare', 'country': 'United Kingdom', 'latitude': 51.5074, 'longitude': -0.1278}

def get_client_ip(request: Request) -> str:
    """Get client IP address from request headers"""
    # Check multiple headers for IP address
    ip_headers = [
        'X-Forwarded-For',
        'X-Real-IP',
        'CF-Connecting-IP',  # Cloudflare
        'True-Client-IP',
        'X-Client-IP'
    ]
    
    for header in ip_headers:
        if header_value := request.headers.get(header):
            # Get the first IP if there are multiple
            client_ip = header_value.split(',')[0].strip()
            print(f"Found client IP {client_ip} in header {header}")
            return client_ip
    
    # If no headers found, get from request client
    client_ip = request.client.host if request.client else "127.0.0.1"
    print(f"Using client IP from request: {client_ip}")
    return client_ip

@router.get("/local")
async def get_local_weather(request: Request):
    """Get weather for the user's location based on their IP"""
    try:
        # Get weather cache service instance
        weather_cache = get_weather_cache_service()
        weather_service = get_weather_service()
        
        # Get client IP and location
        client_ip = get_client_ip(request)
        print(f"Client IP: {client_ip}")
        
        # Get location from IP
        location = await get_location_from_ip(client_ip)
        print(f"Detected location: {location}")
        
        # Try to get weather from cache first
        weather_data = await weather_cache.get_weather_data(location['city'])
        
        # If not in cache, fetch from weather service
        if not weather_data:
            print(f"Weather data for {location['city']} not in cache, fetching from service...")
            forecast = await weather_service.get_forecast(location['city'])
            if forecast:
                weather_data = {
                    "forecast": forecast,
                    "last_updated": None,
                    "location": location
                }
                # Store in cache for future use
                await weather_cache.update_weather_cache(location['city'])
        
        if weather_data and 'forecast' in weather_data:
            return {
                "location": location,
                "forecast": weather_data['forecast']
            }
                
        return JSONResponse(
            status_code=404,
            content={"detail": "Weather data not available"}
        )
                    
    except Exception as e:
        print(f"Error in get_local_weather: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Unable to fetch weather data: {str(e)}"}
        )

@router.get("/current/{city}")
async def get_city_weather(city: str):
    """Get weather for a specific city"""
    try:
        weather_cache = get_weather_cache_service()
        weather_service = get_weather_service()
        
        # Try to get from cache first
        weather_data = await weather_cache.get_weather_data(city)
        
        # If not in cache, fetch from service
        if not weather_data:
            print(f"Weather data for {city} not in cache, fetching from service...")
            forecast = await weather_service.get_forecast(city)
            if forecast:
                # Get country and coordinates from first forecast entry
                weather_data = {
                    "forecast": forecast,
                    "last_updated": datetime.now().isoformat(),
                    "location": {
                        "city": city,
                        "country": "Unknown",
                        "latitude": 0,
                        "longitude": 0
                    }
                }
                # Store in cache
                await weather_cache.update_weather_cache(city)
        
        if weather_data and 'forecast' in weather_data:
            # Ensure location data is properly structured
            location = {
                "city": city,
                "country": weather_data.get("location", {}).get("country", "Unknown") 
                         if isinstance(weather_data.get("location"), dict) 
                         else "Unknown",
                "latitude": weather_data.get("location", {}).get("latitude", 0) 
                          if isinstance(weather_data.get("location"), dict) 
                          else 0,
                "longitude": weather_data.get("location", {}).get("longitude", 0)
                           if isinstance(weather_data.get("location"), dict) 
                           else 0
            }
            
            return {
                "location": location,
                "forecast": weather_data['forecast']
            }
            
        return JSONResponse(
            status_code=404,
            content={"detail": f"Could not fetch weather data for {city}"}
        )
            
    except Exception as e:
        print(f"Error in get_city_weather: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Unable to fetch weather data: {str(e)}"}
        )

@router.get("/analysis/{city}")
async def get_weather_analysis(city: str):
    """Get detailed weather analysis for AI use"""
    try:
        weather_cache = get_weather_cache_service()
        analysis = await weather_cache.get_weather_analysis(city)
        if analysis:
            return analysis
        raise HTTPException(status_code=404, detail=f"Could not analyze weather data for {city}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 