import { Card, CardContent } from "@/components/ui/card";
import { useQuery } from "@tanstack/react-query";
import { API_BASE_URL } from "@/lib/constants";
import { Cloud, CloudRain, Sun, Moon, Loader2, Thermometer, Wind, Droplets } from "lucide-react";

interface WeatherData {
  location: {
    city: string;
    country: string;
    latitude: number;
    longitude: number;
  };
  forecast: Array<{
    temp: number;
    feels_like: number;
    temp_min: number;
    temp_max: number;
    weather: string;
    description: string;
    wind_speed: number;
    wind_direction: number;
    clouds: number;
    precipitation: number;
    humidity: number;
    pressure: number;
    rain: number;
    date: string;
    time: string;
    risk_level: string;
    is_current?: boolean;
    today_max_temp?: number;
    today_min_temp?: number;
    sky_condition?: string;
    visibility?: number;
  }>;
}

const getWeatherIcon = (weather: string, description: string) => {
  const lowerWeather = weather.toLowerCase();
  const lowerDesc = description.toLowerCase();
  
  if (lowerDesc.includes("night") || lowerDesc.includes("clear") && lowerDesc.includes("night")) {
    return <Moon className="h-8 w-8 text-gray-600" />;
  }
  if (lowerWeather.includes("rain") || lowerDesc.includes("rain")) {
    return <CloudRain className="h-8 w-8 text-blue-500" />;
  }
  if (lowerWeather.includes("cloud") || lowerDesc.includes("cloud")) {
    return <Cloud className="h-8 w-8 text-gray-400" />;
  }
  return <Sun className="h-8 w-8 text-yellow-500" />;
};

export function WeatherWidget() {
  const { data: weatherData, isLoading, error } = useQuery<WeatherData>({
    queryKey: ["local-weather"],
    queryFn: async () => {
      console.log("Fetching weather data from:", `${API_BASE_URL}/api/weather/local`);
      try {
        // Get the authentication token
        const token = localStorage.getItem('token');
        
        const response = await fetch(`${API_BASE_URL}/api/weather/local`, {
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
            'Accept': 'application/json',
          },
          credentials: 'include'
        });
        console.log("Weather API Response status:", response.status);
        
        if (!response.ok) {
          const errorText = await response.text();
          console.error("Weather API Error:", errorText);
          throw new Error(`Failed to fetch weather data: ${response.status} ${errorText}`);
        }
        
        const data = await response.json();
        console.log("Weather API Response data:", data);
        
        if (!data || !data.forecast || !data.location) {
          console.error("Invalid weather data structure:", data);
          throw new Error("Invalid weather data structure");
        }
        
        return data;
      } catch (error) {
        console.error("Weather API Error:", error);
        throw error;
      }
    },
    refetchInterval: 1800000, // Refetch every 30 minutes
    retry: 1
  });

  if (isLoading) {
    return (
      <Card className="bg-gradient-to-br from-blue-50 to-blue-100">
        <CardContent className="p-4 flex items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
        </CardContent>
      </Card>
    );
  }

  if (error || !weatherData) {
    console.error("Weather Widget Error:", error);
    return (
      <Card className="bg-gradient-to-br from-red-50 to-red-100">
        <CardContent className="p-4">
          <p className="text-red-500 text-sm">
            Unable to load weather data: {error instanceof Error ? error.message : 'Unknown error'}
          </p>
        </CardContent>
      </Card>
    );
  }

  const currentWeather = weatherData.forecast[0];

  return (
    <Card className="bg-gradient-to-br from-blue-50 to-blue-100">
      <CardContent className="p-4">
        <div className="flex flex-col gap-3">
          {/* Location and Current Temperature */}
          <div className="flex items-start justify-between">
            <div>
              <h3 className="text-2xl font-bold">
                {Math.round(currentWeather.temp)}°
              </h3>
              <p className="text-sm text-gray-600">
                {weatherData.location.city}
              </p>
            </div>
            <div className="flex flex-col items-end">
              {getWeatherIcon(currentWeather.weather, currentWeather.description)}
              <p className="text-sm text-gray-600 mt-1 capitalize">
                {currentWeather.sky_condition || currentWeather.description}
              </p>
            </div>
          </div>

          {/* Additional Weather Info */}
          <div className="grid grid-cols-2 gap-2 text-sm text-gray-600">
            <div className="flex items-center gap-1">
              <Thermometer className="h-3 w-3" />
              <span>H:{Math.round(currentWeather.today_max_temp || currentWeather.temp_max || 0)}° L:{Math.round(currentWeather.today_min_temp || currentWeather.temp_min || 0)}°</span>
            </div>
            <div className="flex items-center gap-1 justify-end">
              <Wind className="h-3 w-3" />
              <span>{Math.round(currentWeather.wind_speed)} m/s</span>
            </div>
            <div className="flex items-center gap-1">
              <Droplets className="h-3 w-3" />
              <span>Precip: {currentWeather.precipitation || currentWeather.rain || 0}mm</span>
            </div>
            <div className="flex items-center gap-1 justify-end">
              <Cloud className="h-3 w-3" />
              <span>Clouds: {currentWeather.clouds}%</span>
            </div>
          </div>

          {/* Feels Like */}
          <div className="text-xs text-gray-500 mt-1">
            Feels like {Math.round(currentWeather.feels_like)}°
          </div>
        </div>
      </CardContent>
    </Card>
  );
} 