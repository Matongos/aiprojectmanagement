import asyncio
from services.weather_service import get_weather_service

async def test_weather():
    weather_service = get_weather_service()
    
    print("Testing Weather Service...")
    print("---------------------------")
    
    # Test for London (default city)
    print("Fetching weather for London:")
    forecast = await weather_service.get_forecast("London", days=3)
    
    if forecast:
        print("\nSuccess! Weather data received:")
        print("---------------------------")
        for weather in forecast[:3]:  # Show first 3 entries
            print(f"\nDate: {weather['date']}")
            print(f"Time: {weather['time']}")
            print(f"Temperature: {weather['temp']}°C")
            print(f"Weather: {weather['weather']}")
            print(f"Description: {weather['description']}")
            print(f"Wind Speed: {weather['wind_speed']} m/s")
            print(f"Rain (3h): {weather['rain']} mm")
            print(f"Risk Level: {weather['risk_level']}")
    else:
        print("\nError: Could not fetch weather data!")

    # Test outdoor task detection
    test_descriptions = [
        "Install solar panels on the roof",
        "Indoor meeting with stakeholders",
        "Paint the exterior walls",
        "Write documentation"
    ]
    
    print("\nTesting Outdoor Task Detection:")
    print("---------------------------")
    for desc in test_descriptions:
        is_outdoor = weather_service.is_outdoor_task(desc, "")
        print(f"Task: {desc}")
        print(f"Is Outdoor: {is_outdoor}\n")

if __name__ == "__main__":
    asyncio.run(test_weather()) 