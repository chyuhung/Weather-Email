import requests

class WeatherAPI:
    @staticmethod
    def get_gaode_weather(city_code, key):
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
        except Exception as e:
            print("天气API错误：", e)
        return None