# weather_api.py 修复版 + 调试模式
import requests
import re
from datetime import datetime

# ========== 彩云天气 API ==========
class CaiyunAPI:
    _API_URL = "https://api.caiyunapp.com/v2.6/{token}/{lng},{lat}/weather"
    _GEO_URL = "https://restapi.amap.com/v3/geocode/regeo"   # 高德逆地理

    # 天气现象映射
    SKYCON_MAP = {
        "CLEAR_DAY": "晴",
        "CLEAR_NIGHT": "晴",
        "PARTLY_CLOUDY_DAY": "多云",
        "PARTLY_CLOUDY_NIGHT": "多云",
        "CLOUDY": "阴",
        "LIGHT_HAZE": "轻度雾霾",
        "MODERATE_HAZE": "中度雾霾",
        "HEAVY_HAZE": "重度雾霾",
        "LIGHT_RAIN": "小雨",
        "MODERATE_RAIN": "中雨",
        "HEAVY_RAIN": "大雨",
        "STORM_RAIN": "暴雨",
        "FOG": "雾",
        "LIGHT_SNOW": "小雪",
        "MODERATE_SNOW": "中雪",
        "HEAVY_SNOW": "大雪",
        "STORM_SNOW": "暴雪",
        "DUST": "浮尘",
        "SAND": "沙尘",
        "WIND": "大风",
    }
    
    # 风向映射
    WIND_DIR_MAP = {
        0: "北风", 45: "东北风", 90: "东风", 135: "东南风",
        180: "南风", 225: "西南风", 270: "西风", 315: "西北风"
    }
    
    @classmethod
    def _get_wind_direction(cls, degree):
        """风向角度转文字"""
        if degree is None:
            return "未知"
        degree = int(degree) % 360
        directions = [
            (0, "北风"), (45, "东北风"), (90, "东风"), (135, "东南风"),
            (180, "南风"), (225, "西南风"), (270, "西风"), (315, "西北风")
        ]
        return min(directions, key=lambda x: min(abs(x[0] - degree), 360 - abs(x[0] - degree)))[1]
    
    @classmethod
    def _get_wind_power(cls, speed):
        """风速转风力等级"""
        if speed is None:
            return "0"
        # 蒲福风级近似
        levels = [
            (0.3, "1"), (1.6, "2"), (3.4, "3"), (5.5, "4"), (8.0, "5"),
            (10.8, "6"), (13.9, "7"), (17.2, "8"), (20.8, "9"), (24.5, "10"),
            (28.5, "11"), (32.7, "12")
        ]
        for threshold, level in levels:
            if speed < threshold:
                return level
        return "12+"
    
    @classmethod
    def _latlng_to_name(cls, location, gaode_key):
        """用高德逆地理编码将经纬度转为省市区名称"""
        try:
            resp = requests.get(
                cls._GEO_URL,
                params={"key": gaode_key, "location": location, "extensions": "base"},
                timeout=10
            )
            data = resp.json()
            if data.get("status") == "1" and data.get("regeocode"):
                comp = data["regeocode"].get("addressComponent", {})
                province = comp.get("province", "")
                city = comp.get("city")
                district = comp.get("district", "")
                # 城市可能为空（如直辖市），取 province
                city_name = (city[0] if city else province) if isinstance(city, list) else (city or province)
                return f"{province} {city_name} {district}".strip().replace("  ", " ")
            return None
        except Exception as e:
            print(f"【调试】逆地理编码失败: {e}")
            return None

    @classmethod
    def get_weather(cls, location, token, gaode_key=None, extensions="base"):
        """
        获取彩云天气
        :param location: 经纬度字符串 "lng,lat"
        :param token: 彩云 API Token
        :param gaode_key: 高德 Key（用于逆地理编码显示地名）
        :param extensions: base=实况, all=实况+预报
        """
        try:
            parts = location.split(",")
            if len(parts) != 2:
                return {"success": False, "error": "经纬度格式错误，应为 lng,lat"}
            lng, lat = parts[0].strip(), parts[1].strip()

            # 先用高德逆地理获取地名
            city_name = None
            if gaode_key:
                city_name = cls._latlng_to_name(location, gaode_key)
            if not city_name:
                city_name = f"{lat}°N, {lng}°E"

            # 构建请求
            url = cls._API_URL.format(token=token, lng=lng, lat=lat)
            params = {
                "alert": "true",
                "dailysteps": 3 if extensions == "all" else 1,
                "hourlysteps": 24
            }

            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()

            # 调试输出
            print("\n【调试】彩云API返回状态:", data.get("status"))
            print("=" * 50)

            if data.get("status") != "ok":
                return {
                    "success": False,
                    "error": f"彩云API错误: {data.get('error', '未知错误')}"
                }

            result = data.get("result", {})
            realtime = result.get("realtime", {})

            # 构建返回结构（与高德格式兼容）
            weather_data = {
                "success": True,
                "city": city_name,
                "live": None,
                "forecast": None,
                "error": None,
                "source": "caiyun"
            }

            # 解析实况天气
            if realtime:
                skycon = realtime.get("skycon", "UNKNOWN")
                wind = realtime.get("wind", {})
                wind_dir = wind.get("direction")
                wind_speed = wind.get("speed", 0)

                weather_data["live"] = {
                    "city": city_name,
                    "weather": cls.SKYCON_MAP.get(skycon, skycon),
                    "temperature": str(realtime.get("temperature", "N/A")),
                    "apparent_temperature": str(realtime.get("apparent_temperature", "N/A")),
                    "humidity": str(round(realtime.get("humidity", 0) * 100)),
                    "wind_direction": cls._get_wind_direction(wind_dir),
                    "wind_power": cls._get_wind_power(wind_speed),
                    "wind_speed": str(wind_speed),
                    "pressure": str(round(realtime.get("pressure", 0) / 100, 1)),
                    "visibility": str(realtime.get("visibility", "N/A")),
                    "cloudrate": str(round(realtime.get("cloudrate", 0) * 100)),
                    "report_time": datetime.fromtimestamp(data.get("server_time", 0)).strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # 空气质量（可选）
                air_quality = realtime.get("air_quality", {})
                if air_quality:
                    weather_data["live"]["aqi"] = str(air_quality.get("aqi", {}).get("chn", "N/A"))
                    weather_data["live"]["pm25"] = str(air_quality.get("pm25", "N/A"))
                    weather_data["live"]["air_desc"] = air_quality.get("description", {}).get("chn", "")
                
                # 天气关键点
                weather_data["forecast_keypoint"] = result.get("forecast_keypoint", "")
            
            # ── 解析小时级预报（用于明日分段天气）─────────────────────────
            hourly_forecast = []
            if extensions == "all":
                hourly_data = result.get("hourly", {})
                for item in hourly_data.get("temperature", []):
                    dt_str = item.get("datetime", "")
                    skycon_vals = hourly_data.get("skycon", [])
                    sky = next(
                        (s.get("value") for s in skycon_vals if s.get("datetime") == dt_str),
                        "CLEAR_DAY"
                    )
                    wind_vals = hourly_data.get("wind", [])
                    w = next((w for w in wind_vals if w.get("datetime") == dt_str), {})
                    hourly_forecast.append({
                        "datetime": dt_str,
                        "temperature": item.get("value", "N/A"),
                        "weather": cls.SKYCON_MAP.get(sky, sky),
                        "skycon": sky,
                        "wind_direction": cls._get_wind_direction(w.get("direction")),
                        "wind_power": cls._get_wind_power(w.get("speed", 0)),
                        "humidity": round(w.get("humidity", 0) * 100) if w.get("humidity") is not None else "N/A",
                    })

                # ── 解析每日预报（最高/最低温）───────────────────────────────
                daily_data = result.get("daily", {})
                if daily_data:
                    weather_data["forecast"] = {
                        "city": city_name,
                        "casts": []
                    }
                    for i, cast in enumerate(daily_data.get("temperature", [])):
                        if i >= 3:
                            break
                        skycons = daily_data.get("skycon", [])
                        day_sky = skycons[i].get("value", "") if i < len(skycons) else ""
                        weather_data["forecast"]["casts"].append({
                            "date": cast.get("date", ""),
                            "day_temp": str(cast.get("max", "N/A")),
                            "night_temp": str(cast.get("min", "N/A")),
                            "day_weather": cls.SKYCON_MAP.get(day_sky, day_sky),
                            "skycon": day_sky,
                        })

            weather_data["hourly_forecast"] = hourly_forecast
            
            return weather_data
            
        except Exception as e:
            print(f"【调试】彩云API异常: {e}")
            return {
                "success": False,
                "error": f"网络/解析异常: {str(e)}"
            }


# ========== 高德天气 API ==========
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