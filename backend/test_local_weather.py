import asyncio
import aiohttp

async def test_local_weather():
    print("Testing Local Weather API...")
    print("---------------------------")
    
    async with aiohttp.ClientSession() as session:
        # Test local weather endpoint
        print("\nTesting /api/weather/local endpoint:")
        async with session.get('http://localhost:8000/api/weather/local') as response:
            if response.status == 200:
                data = await response.json()
                print("\nSuccess! Local weather data received:")
                print("---------------------------")
                print(f"Location: {data['location']['city']}, {data['location']['country']}")
                
                # Show first weather entry
                if data['forecast']:
                    weather = data['forecast'][0]
                    print(f"\nCurrent Weather:")
                    print(f"Temperature: {weather['temp']}°C")
                    print(f"Conditions: {weather['weather']}")
                    print(f"Description: {weather['description']}")
                    print(f"Wind Speed: {weather['wind_speed']} m/s")
                    print(f"Rain (3h): {weather['rain']} mm")
                    print(f"Risk Level: {weather['risk_level']}")
            else:
                print(f"Error: {response.status}")
                print(await response.text())

if __name__ == "__main__":
    asyncio.run(test_local_weather()) 