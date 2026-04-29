# weather_api.py 修复版 + 调试模式
import requests
import re

class WeatherAPI:
    _API_URL = "https://restapi.amap.com/v3/weather/weatherInfo"
    _GEO_URL = "https://restapi.amap.com/v3/geocode/regeo"

    @classmethod
    def _is_latlng(cls, location):
        """判断是否为经纬度格式（如 106.50,29.73）"""
        pattern = r'^-?\d+\.?\d*,-?\d+\.?\d*$'
        return bool(re.match(pattern, location))

    @classmethod
    def _latlng_to_adcode(cls, location, amap_key):
        """经纬度转 adcode"""
        try:
            resp = requests.get(
                cls._GEO_URL,
                params={
                    "key": amap_key,
                    "location": location,
                    "extensions": "base",
                    "output": "JSON"
                },
                timeout=10
            )
            data = resp.json()
            if data.get("status") == "1" and data.get("regeocode"):
                adcode = data["regeocode"].get("addressComponent", {}).get("adcode")
                city = data["regeocode"].get("addressComponent", {}).get("city")
                district = data["regeocode"].get("addressComponent", {}).get("district")
                print(f"【调试】经纬度 {location} 解析为: {district or city} (adcode: {adcode})")
                return adcode
            else:
                print(f"【调试】逆地理编码失败: {data.get('info', '未知错误')}")
                return None
        except Exception as e:
            print(f"【调试】逆地理编码异常: {e}")
            return None

    @classmethod
    def get_weather(cls, city_or_location, amap_key, extensions="base"):
        params = {
            "key": amap_key,
            "extensions": extensions,
            "output": "JSON",
            "gzip": "n"
        }

        # 如果是经纬度，先转成 adcode
        city_code = city_or_location
        if cls._is_latlng(city_or_location):
            adcode = cls._latlng_to_adcode(city_or_location, amap_key)
            if adcode:
                city_code = adcode
            else:
                return {
                    "success": False,
                    "error": "经纬度解析失败，无法获取对应城市信息"
                }

        params["city"] = city_code

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