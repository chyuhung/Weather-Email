# weather_api.py 修复版 + 调试模式
import requests

class WeatherAPI:
    _API_URL = "https://restapi.amap.com/v3/weather/weatherInfo"

    @classmethod
    def get_weather(cls, city_or_location, amap_key, extensions="base"):
        params = {
            "key": amap_key,
            "extensions": extensions,
            "output": "JSON",
            "gzip": "n"
        }

        params["city"] = city_or_location  # 高德支持直接传经纬度/adcode

        try:
            resp = requests.get(cls._API_URL, params=params, timeout=15)
            data = resp.json()

            # ========== 调试输出：查看真实返回结果 ==========
            print("\n【调试】高德API原始返回：")
            print(data)
            print("="*50)

            if data.get("status") != "1" or data.get("infocode") != "10000":
                return {
                    "success": False,
                    "error": f"{data.get('info','请求失败')} ({data.get('infocode')})"
                }

            result = {
                "success": True,
                "city": None,
                "live": None,
                "forecast": None,
                "error": None
            }

            # 解析实况
            if "lives" in data and isinstance(data["lives"], list) and len(data["lives"]) > 0:
                live = data["lives"][0]
                result["city"] = live.get("city", "未知城市")
                result["live"] = {
                    "province": live.get("province", ""),
                    "city": live.get("city", ""),
                    "adcode": live.get("adcode", ""),
                    "weather": live.get("weather", "无数据"),
                    "temperature": live.get("temperature", "N/A"),
                    "wind_direction": live.get("winddirection", "无风向"),
                    "wind_power": live.get("windpower", "0"),
                    "humidity": live.get("humidity", "N/A"),
                    "report_time": live.get("reporttime", "")
                }

            # 解析预报
            if extensions == "all" and "forecasts" in data and len(data["forecasts"]) > 0:
                forecast = data["forecasts"][0]
                result["forecast"] = {
                    "city": forecast.get("city", ""),
                    "report_time": forecast.get("reporttime", ""),
                    "casts": []
                }
                for cast in forecast.get("casts", []):
                    result["forecast"]["casts"].append({
                        "date": cast.get("date", ""),
                        "week": cast.get("week", ""),
                        "day_weather": cast.get("dayweather", ""),
                        "night_weather": cast.get("nightweather", ""),
                        "day_temp": cast.get("daytemp", ""),
                        "night_temp": cast.get("nighttemp", ""),
                    })

            return result

        except Exception as e:
            print(f"【调试】异常信息：{e}")
            return {
                "success": False,
                "error": f"网络/解析异常: {str(e)}"
            }

    @classmethod
    def get_live_weather(cls, city_or_location, amap_key):
        return cls.get_weather(city_or_location, amap_key, extensions="base")