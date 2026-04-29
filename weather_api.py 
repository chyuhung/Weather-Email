import requests

class WeatherAPI:
    """天气API统一接口，方便扩展多个源"""
    
    @staticmethod
    def get_gaode_weather(city_code, key):
        """高德地图天气API"""
        url = "https://restapi.amap.com/v3/weather/weatherInfo"
        params = {
            "city": city_code,
            "key": key,
            "extensions": "base",
            "output": "json"
        }
        
        try:
            res = requests.get(url, params=params, timeout=10)
            data = res.json()
            
            if data.get("status") == "1":
                w = data["lives"][0]
                return {
                    "city": w["city"],
                    "temp": w["temperature"],
                    "weather": w["weather"],
                    "wind": w["winddirection"],
                    "humidity": w["humidity"],
                    "power": w["windpower"],
                    "time": w["reporttime"]
                }
            return None
        except:
            return None

    # 以后扩展API直接在这里加方法
    # @staticmethod
    # def get_open_meteo_weather(lat, lon):
    #     pass