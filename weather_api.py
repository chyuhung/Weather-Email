import requests
from datetime import datetime


# ========== 彩云天气 API ==========
class CaiyunAPI:
    _API_URL = "https://api.caiyunapp.com/v2.6/{token}/{lng},{lat}/weather"
    _GEO_URL = "https://restapi.amap.com/v3/geocode/regeo"

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
    _WIND_DIRS = [
        (0, "北风"), (45, "东北风"), (90, "东风"), (135, "东南风"),
        (180, "南风"), (225, "西南风"), (270, "西风"), (315, "西北风")
    ]

    @classmethod
    def _get_wind_direction(cls, degree):
        if degree is None:
            return "未知"
        degree = int(degree) % 360
        return min(cls._WIND_DIRS, key=lambda x: min(abs(x[0] - degree), 360 - abs(x[0] - degree)))[1]

    @classmethod
    def _get_wind_power(cls, speed):
        if speed is None:
            return "0"
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
                city_name = (city[0] if city else province) if isinstance(city, list) else (city or province)
                return f"{province} {city_name} {district}".strip().replace("  ", " ")
            return None
        except Exception:
            return None

    @classmethod
    def get_weather(cls, location, token, gaode_key=None, extensions="base", hourlysteps=48, dailysteps=None):
        try:
            parts = location.split(",")
            if len(parts) != 2:
                return {"success": False, "error": "经纬度格式错误,应为 lng,lat"}
            lng, lat = parts[0].strip(), parts[1].strip()

            # 逆地理获取地名
            city_name = None
            if gaode_key:
                city_name = cls._latlng_to_name(location, gaode_key)
            if not city_name:
                city_name = f"{lat}N, {lng}E"

            url = cls._API_URL.format(token=token, lng=lng, lat=lat)
            # dailysteps: 早间模式仅需今天(1),晚间模式需要今天+明天(2)
            if dailysteps is None:
                dailysteps = 2 if extensions == "all" else 1
            params = {
                "alert": "true",
                "dailysteps": dailysteps,
                "hourlysteps": hourlysteps
            }

            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()

            if data.get("status") != "ok":
                return {
                    "success": False,
                    "error": f"彩云API错误: {data.get('error', '未知错误')}"
                }

            result = data.get("result", {})
            realtime = result.get("realtime", {})

            weather_data = {
                "success": True,
                "city": city_name,
                "live": None,
                "forecast": None,
                "error": None,
                "source": "caiyun"
            }

            # 解析实况
            if realtime:
                skycon = realtime.get("skycon", "UNKNOWN")
                wind = realtime.get("wind", {})
                wind_dir = wind.get("direction")
                wind_speed = wind.get("speed", 0)

                live = {
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

                air_quality = realtime.get("air_quality", {})
                if air_quality:
                    live["aqi"] = str(air_quality.get("aqi", {}).get("chn", "N/A"))
                    live["pm25"] = str(air_quality.get("pm25", "N/A"))
                    live["air_desc"] = air_quality.get("description", {}).get("chn", "")

                weather_data["live"] = live
                weather_data["forecast_keypoint"] = result.get("forecast_keypoint", "")

            # 解析小时预报
            hourly_forecast = []
            if extensions == "all":
                hourly_data = result.get("hourly", {})
                # 提取小时预报描述（如“小雨，今天中午12点钟后雨停，转多云”）
                weather_data["hourly_description"] = hourly_data.get("description", "")

                # 构建时间索引，方便后续匹配
                temp_vals = {x.get("datetime"): x for x in hourly_data.get("temperature", [])}
                skycon_vals = {x.get("datetime"): x.get("value") for x in hourly_data.get("skycon", [])}
                wind_vals = {x.get("datetime"): x for x in hourly_data.get("wind", [])}
                humid_vals = {x.get("datetime"): x.get("value") for x in hourly_data.get("humidity", [])}
                precip_vals = {x.get("datetime"): x for x in hourly_data.get("precipitation", [])}
                apparent_vals = {x.get("datetime"): x.get("value") for x in hourly_data.get("apparent_temperature", [])}

                # 合并所有 datetime 键
                all_dt = set(temp_vals.keys()) | set(skycon_vals.keys()) | set(wind_vals.keys())

                for dt_str in sorted(all_dt):
                    temp_info = temp_vals.get(dt_str, {})
                    sky = skycon_vals.get(dt_str, "CLEAR_DAY")
                    w = wind_vals.get(dt_str, {})
                    humid = humid_vals.get(dt_str)
                    precip = precip_vals.get(dt_str, {})
                    apparent = apparent_vals.get(dt_str)

                    hourly_forecast.append({
                        "datetime": dt_str,
                        "temperature": temp_info.get("value", "N/A"),
                        "apparent_temperature": apparent if apparent is not None else "N/A",
                        "weather": cls.SKYCON_MAP.get(sky, sky),
                        "skycon": sky,
                        "wind_direction": cls._get_wind_direction(w.get("direction")),
                        "wind_power": cls._get_wind_power(w.get("speed", 0)),
                        "wind_speed": w.get("speed", 0),
                        "humidity": str(round(humid * 100)) if humid is not None else "N/A",
                        "precipitation": precip.get("value", 0),
                        "precip_probability": precip.get("probability", 0),
                    })

                # 解析每日预报(最高/最低温 + 日出日落 + 白天/夜间细分 + 生活指数)
                daily_data = result.get("daily", {})
                if daily_data:
                    weather_data["forecast"] = {"city": city_name, "casts": []}

                    # 预构建索引
                    astro_list   = daily_data.get("astro", [])
                    skycon_0820  = daily_data.get("skycon_08h_20h", [])
                    skycon_2032  = daily_data.get("skycon_20h_32h", [])
                    temp_0820    = daily_data.get("temperature_08h_20h", [])
                    temp_2032    = daily_data.get("temperature_20h_32h", [])
                    precip_0820  = daily_data.get("precipitation_08h_20h", [])
                    precip_2032  = daily_data.get("precipitation_20h_32h", [])
                    life_index   = daily_data.get("life_index", {})

                    for i, cast in enumerate(daily_data.get("temperature", [])):
                        if i >= 3:
                            break
                        skycons = daily_data.get("skycon", [])
                        day_sky = skycons[i].get("value", "") if i < len(skycons) else ""

                        cast_data = {
                            "date": cast.get("date", ""),
                            "day_temp": str(cast.get("max", "N/A")),
                            "night_temp": str(cast.get("min", "N/A")),
                            "day_weather": cls.SKYCON_MAP.get(day_sky, day_sky),
                            "skycon": day_sky,
                        }

                        # 日出日落
                        if i < len(astro_list):
                            astro = astro_list[i]
                            cast_data["sunrise"] = astro.get("sunrise", {}).get("time", "")
                            cast_data["sunset"] = astro.get("sunset", {}).get("time", "")

                        # 白天天气(08-20时)
                        if i < len(skycon_0820):
                            sky08 = skycon_0820[i].get("value", "")
                            cast_data["skycon_08h_20h"] = sky08
                            cast_data["daytime_weather"] = cls.SKYCON_MAP.get(sky08, sky08)
                        # 夜间天气(20-次日08时)
                        if i < len(skycon_2032):
                            sky20 = skycon_2032[i].get("value", "")
                            cast_data["skycon_20h_32h"] = sky20
                            cast_data["nighttime_weather"] = cls.SKYCON_MAP.get(sky20, sky20)

                        # 白天/夜间温度细分
                        if i < len(temp_0820):
                            cast_data["temp_08h_20h_max"] = str(temp_0820[i].get("max", ""))
                            cast_data["temp_08h_20h_min"] = str(temp_0820[i].get("min", ""))
                        if i < len(temp_2032):
                            cast_data["temp_20h_32h_max"] = str(temp_2032[i].get("max", ""))
                            cast_data["temp_20h_32h_min"] = str(temp_2032[i].get("min", ""))

                        # 白天/夜间降水概率
                        if i < len(precip_0820):
                            cast_data["precip_08h_20h_prob"] = precip_0820[i].get("probability", 0)
                        if i < len(precip_2032):
                            cast_data["precip_20h_32h_prob"] = precip_2032[i].get("probability", 0)

                        # 生活指数
                        for key, label in [("ultraviolet", "紫外线"), ("dressing", "穿衣"),
                                            ("comfort", "舒适度"), ("coldRisk", "感冒"),
                                            ("carWashing", "洗车")]:
                            idx_list = life_index.get(key, [])
                            if i < len(idx_list):
                                idx_item = idx_list[i]
                                cast_data[f"life_{key}"] = {"index": idx_item.get("index", ""), "desc": idx_item.get("desc", "")}

                        weather_data["forecast"]["casts"].append(cast_data)

            weather_data["hourly_forecast"] = hourly_forecast
            return weather_data

        except Exception as e:
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
        import re
        return bool(re.match(r'^-?\d+\.?\d*,-?\d+\.?\d*$', location))

    @classmethod
    def _latlng_to_adcode(cls, location, amap_key):
        try:
            resp = requests.get(
                cls._GEO_URL,
                params={"key": amap_key, "location": location, "extensions": "base", "output": "JSON"},
                timeout=10
            )
            data = resp.json()
            if data.get("status") == "1" and data.get("regeocode"):
                comp = data["regeocode"].get("addressComponent", {})
                return {
                    "adcode": comp.get("adcode"),
                    "city": comp.get("city"),
                    "district": comp.get("district"),
                }
            return None
        except Exception:
            return None

    @classmethod
    def get_weather(cls, city_or_location, amap_key, extensions="base"):
        params = {
            "key": amap_key,
            "extensions": extensions,
            "output": "JSON",
            "gzip": "n"
        }

        city_code = city_or_location
        if cls._is_latlng(city_or_location):
            geo = cls._latlng_to_adcode(city_or_location, amap_key)
            if geo and geo.get("adcode"):
                city_code = geo["adcode"]
            else:
                return {"success": False, "error": "经纬度解析失败,无法获取对应城市信息"}

        params["city"] = city_code

        try:
            resp = requests.get(cls._API_URL, params=params, timeout=15)
            data = resp.json()

            if data.get("status") != "1" or data.get("infocode") != "10000":
                return {
                    "success": False,
                    "error": f"{data.get('info', '请求失败')} ({data.get('infocode')})"
                }

            result = {"success": True, "city": None, "live": None, "forecast": None, "error": None, "source": "gaode"}

            # 实况
            if "lives" in data and isinstance(data["lives"], list) and data["lives"]:
                live = data["lives"][0]
                result["city"] = live.get("city", "未知城市")
                result["live"] = {
                    "city": live.get("city", ""),
                    "weather": live.get("weather", "无数据"),
                    "temperature": live.get("temperature", "N/A"),
                    "wind_direction": live.get("winddirection", "无风向"),
                    "wind_power": live.get("windpower", "0"),
                    "humidity": live.get("humidity", "N/A"),
                    "report_time": live.get("reporttime", "")
                }

            # 预报
            if extensions == "all" and "forecasts" in data and data["forecasts"]:
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
            return {"success": False, "error": f"网络/解析异常: {str(e)}"}


