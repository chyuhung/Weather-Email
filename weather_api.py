"""
天气数据获取模块
- 支持「彩云天气」和「高德天气」两种数据源
- 彩云天气：数据丰富（分钟级降水、小时预报、生活指数等），推荐使用
- 高德天气：支持城市名/adcode 查询，作为备用数据源

数据返回结构（统一格式）:
{
    "success": bool,       # 是否成功
    "city": str,           # 城市名称
    "live": dict | None,   # 实况天气数据
    "forecast": dict | None,  # 每日预报数据
    "hourly_forecast": list,  # 小时预报列表
    "forecast_keypoint": str, # 彩云天气关键提示（API 级别）
    "hourly_description": str, # 小时预报文字描述
    "daily_aqi": dict | None,  # 每日空气质量（用于晚间模式）
    "source": str,         # 数据源标识（caiyun / gaode）
    "error": str | None    # 错误信息
}
"""

import re
import requests
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

BEIJING_TZ = timezone(timedelta(hours=8))




# ================================================================
#  彩云天气 API
# ================================================================

class CaiyunAPI:
    """彩云天气 API 封装，支持实况、小时预报、每日预报查询"""

    # API 端点
    _API_URL: str = "https://api.caiyunapp.com/v2.6/{token}/{lng},{lat}/weather"
    _GEO_URL: str = "https://restapi.amap.com/v3/geocode/regeo"

    # 天气现象代码 → 中文映射（覆盖彩云天气所有 skycon 值）
    SKYCON_MAP: dict[str, str] = {
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

    # 风向角度 → 八方位映射表（用于找最近方位）
    _WIND_DIRS: list[tuple[float, str]] = [
        (0, "北风"), (45, "东北风"), (90, "东风"), (135, "东南风"),
        (180, "南风"), (225, "西南风"), (270, "西风"), (315, "西北风"),
    ]

    # 风速（m/s）→ 蒲福风力等级
    _WIND_LEVELS: list[tuple[float, str]] = [
        (0.3, "1"), (1.6, "2"), (3.4, "3"), (5.5, "4"), (8.0, "5"),
        (10.8, "6"), (13.9, "7"), (17.2, "8"), (20.8, "9"), (24.5, "10"),
        (28.5, "11"), (32.7, "12"),
    ]

    # ---- 工具方法 ----

    @classmethod
    def _get_wind_direction(cls, degree: Optional[float]) -> str:
        """将风向角度转换为八方位中文（如 45° → 东北风）"""
        if degree is None:
            return "未知"
        degree = float(degree) % 360
        # 选择角度差最小的方位
        return min(cls._WIND_DIRS, key=lambda x: min(abs(x[0] - degree), 360 - abs(x[0] - degree)))[1]

    @classmethod
    def _get_wind_power(cls, speed: Optional[float]) -> str:
        """将风速（m/s）转换为蒲福风力等级字符串"""
        if speed is None:
            return "0"
        for threshold, level in cls._WIND_LEVELS:
            if speed < threshold:
                return level
        return "12+"

    @classmethod
    def _latlng_to_name(cls, location: str, gaode_key: str) -> Optional[str]:
        """
        通过高德逆地理编码 API 将经纬度转换为中文地名。
        高德 API 对直辖市（北京/上海/天津/重庆）的 city 字段返回空字符串或空数组，
        此时需回退到 province 字段。
        """
        try:
            resp = requests.get(
                cls._GEO_URL,
                params={"key": gaode_key, "location": location, "extensions": "base"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "1" or not data.get("regeocode"):
                return None

            comp = data["regeocode"].get("addressComponent", {})
            province = comp.get("province", "")
            city = comp.get("city")          # 直辖市可能为 "" 或 []
            district = comp.get("district", "")

            # 处理直辖市：city 为空数组时取第一个元素，为空字符串时回退 province
            if isinstance(city, list):
                city_name = city[0] if city else province
            else:
                city_name = city or province

            # 组装地名，去除多余空格
            return f"{province} {city_name} {district}".strip().replace("  ", " ")
        except Exception:
            return None

    @classmethod
    def get_weather(
        cls,
        location: str,
        token: str,
        gaode_key: Optional[str] = None,
        extensions: str = "base",
        hourlysteps: int = 48,
        dailysteps: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        获取彩云天气数据（统一返回格式）。

        Args:
            location:   经纬度字符串，格式 "经度,纬度"（如 "116.3176,39.9760"）
            token:      彩云天气 API Token
            gaode_key:  高德地图 Key（可选，用于逆地理编码获取城市名）
            extensions: "base" 仅实况 / "all" 实况+小时+每日预报
            hourlysteps: 小时预报步数（建议 48，覆盖完整的下一天）
            dailysteps: 每日预报天数（默认：base=1, all=2）

        Returns:
            统一格式的天气数据字典
        """
        try:
            # ---- 校验经纬度格式 ----
            parts = location.split(",")
            if len(parts) != 2:
                return {"success": False, "error": "经纬度格式错误, 应为 lng,lat"}

            lng, lat = parts[0].strip(), parts[1].strip()

            # ---- 逆地理编码获取城市名 ----
            city_name: Optional[str] = None
            if gaode_key:
                city_name = cls._latlng_to_name(location, gaode_key)
            if not city_name:
                city_name = f"{lat}N, {lng}E"

            # ---- 构造请求参数 ----
            url = cls._API_URL.format(token=token, lng=lng, lat=lat)
            if dailysteps is None:
                dailysteps = 2 if extensions == "all" else 1

            params = {
                "alert": "true",
                "dailysteps": dailysteps,
                "hourlysteps": hourlysteps,
            }

            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "ok":
                return {
                    "success": False,
                    "error": f"彩云API错误: {data.get('error', '未知错误')}",
                }

            result = data.get("result", {})
            realtime = result.get("realtime", {})

            # ---- 构建统一返回结构 ----
            weather_data: dict[str, Any] = {
                "success": True,
                "city": city_name,
                "live": None,
                "forecast": None,
                "hourly_forecast": [],
                "forecast_keypoint": result.get("forecast_keypoint", ""),
                "hourly_description": "",
                "daily_aqi": None,
                "source": "caiyun",
                "error": None,
            }

            # ===================== 解析实况数据 =====================
            if realtime:
                skycon = realtime.get("skycon", "UNKNOWN")
                wind = realtime.get("wind", {})
                wind_dir = wind.get("direction")
                wind_speed = wind.get("speed", 0)

                live: dict[str, Any] = {
                    "city": city_name,
                    "skycon": skycon,
                    "weather": cls.SKYCON_MAP.get(skycon, skycon),
                    "temperature": realtime.get("temperature"),
                    "apparent_temperature": realtime.get("apparent_temperature"),
                    "humidity": round(realtime.get("humidity", 0) * 100),       # 百分比
                    "wind_direction": cls._get_wind_direction(wind_dir),
                    "wind_power": cls._get_wind_power(wind_speed),
                    "wind_speed": wind_speed,
                    "pressure": round(realtime.get("pressure", 0) / 100, 1),     # Pa → hPa
                    "visibility": realtime.get("visibility"),
                    "cloudrate": round(realtime.get("cloudrate", 0) * 100),      # 百分比
                    "report_time": datetime.fromtimestamp(
                        data.get("server_time", 0)
                    ).astimezone(BEIJING_TZ).strftime("%Y-%m-%d %H:%M"),
                }

                # 实况降水信息
                precipitation = realtime.get("precipitation", {})
                local_precip = precipitation.get("local", {})
                if local_precip and local_precip.get("status") == "ok":
                    live["precip_intensity"] = local_precip.get("intensity", 0)
                    live["precip_datasource"] = local_precip.get("datasource", "")

                # 空气质量
                air_quality = realtime.get("air_quality", {})
                if air_quality:
                    aqi_info = air_quality.get("aqi", {})
                    live["aqi"] = aqi_info.get("chn")
                    live["aqi_usa"] = aqi_info.get("usa")
                    live["pm25"] = air_quality.get("pm25")
                    live["pm10"] = air_quality.get("pm10")
                    live["o3"] = air_quality.get("o3")
                    live["air_desc"] = air_quality.get("description", {}).get("chn", "")

                # 实况生活指数（紫外线、舒适度）
                life_index = realtime.get("life_index", {})
                if life_index:
                    uv = life_index.get("ultraviolet", {})
                    comfort = life_index.get("comfort", {})
                    if uv:
                        live["uv_index"] = uv.get("index")
                        live["uv_desc"] = uv.get("desc", "")
                    if comfort:
                        live["comfort_index"] = comfort.get("index")
                        live["comfort_desc"] = comfort.get("desc", "")

                weather_data["live"] = live

            # ===================== 解析小时预报 =====================
            hourly_data = result.get("hourly", {})
            weather_data["hourly_description"] = hourly_data.get("description", "")

            if extensions == "all" and hourly_data:
                # 构建时间索引，方便交叉匹配不同指标
                temp_vals = {x.get("datetime"): x for x in hourly_data.get("temperature", [])}
                skycon_vals = {x.get("datetime"): x.get("value") for x in hourly_data.get("skycon", [])}
                wind_vals = {x.get("datetime"): x for x in hourly_data.get("wind", [])}
                humid_vals = {x.get("datetime"): x.get("value") for x in hourly_data.get("humidity", [])}
                precip_vals = {x.get("datetime"): x for x in hourly_data.get("precipitation", [])}
                apparent_vals = {x.get("datetime"): x.get("value") for x in hourly_data.get("apparent_temperature", [])}

                # 合并所有时间点
                all_dt = sorted(
                    set(temp_vals.keys()) | set(skycon_vals.keys()) | set(wind_vals.keys())
                )

                hourly_forecast = []
                for dt_str in all_dt:
                    temp_info = temp_vals.get(dt_str, {})
                    sky = skycon_vals.get(dt_str, "CLEAR_DAY")
                    w = wind_vals.get(dt_str, {})
                    humid = humid_vals.get(dt_str)
                    precip = precip_vals.get(dt_str, {})
                    apparent = apparent_vals.get(dt_str)

                    hourly_forecast.append({
                        "datetime": dt_str,
                        "temperature": temp_info.get("value"),
                        "apparent_temperature": apparent,
                        "weather": cls.SKYCON_MAP.get(sky, sky),
                        "skycon": sky,
                        "wind_direction": cls._get_wind_direction(w.get("direction")),
                        "wind_power": cls._get_wind_power(w.get("speed", 0)),
                        "wind_speed": w.get("speed", 0),
                        "humidity": round(humid * 100) if humid is not None else None,
                        "precipitation": precip.get("value", 0),
                        "precip_probability": precip.get("probability", 0),
                    })

                weather_data["hourly_forecast"] = hourly_forecast

            # ===================== 解析每日预报 =====================
            daily_data = result.get("daily", {})
            if extensions == "all" and daily_data:
                weather_data["forecast"] = {"city": city_name, "casts": []}

                # 预构建各子指标列表
                astro_list = daily_data.get("astro", [])
                skycon_0820 = daily_data.get("skycon_08h_20h", [])
                skycon_2032 = daily_data.get("skycon_20h_32h", [])
                temp_0820 = daily_data.get("temperature_08h_20h", [])
                temp_2032 = daily_data.get("temperature_20h_32h", [])
                precip_0820 = daily_data.get("precipitation_08h_20h", [])
                precip_2032 = daily_data.get("precipitation_20h_32h", [])
                life_index = daily_data.get("life_index", {})

                for i, cast in enumerate(daily_data.get("temperature", [])):
                    if i >= 3:  # 最多取 3 天
                        break

                    skycons = daily_data.get("skycon", [])
                    day_sky = skycons[i].get("value", "") if i < len(skycons) else ""

                    cast_data: dict[str, Any] = {
                        "date": cast.get("date", ""),
                        "day_temp": cast.get("max"),
                        "night_temp": cast.get("min"),
                        "day_weather": cls.SKYCON_MAP.get(day_sky, day_sky),
                        "skycon": day_sky,
                    }

                    # 日出日落
                    if i < len(astro_list):
                        astro = astro_list[i]
                        cast_data["sunrise"] = astro.get("sunrise", {}).get("time", "")
                        cast_data["sunset"] = astro.get("sunset", {}).get("time", "")

                    # 白天天气 (08-20 时)
                    if i < len(skycon_0820):
                        sky08 = skycon_0820[i].get("value", "")
                        cast_data["skycon_08h_20h"] = sky08
                        cast_data["daytime_weather"] = cls.SKYCON_MAP.get(sky08, sky08)

                    # 夜间天气 (20-次日 08 时)
                    if i < len(skycon_2032):
                        sky20 = skycon_2032[i].get("value", "")
                        cast_data["skycon_20h_32h"] = sky20
                        cast_data["nighttime_weather"] = cls.SKYCON_MAP.get(sky20, sky20)

                    # 白天/夜间温度细分
                    if i < len(temp_0820):
                        cast_data["temp_08h_20h_max"] = temp_0820[i].get("max")
                        cast_data["temp_08h_20h_min"] = temp_0820[i].get("min")
                    if i < len(temp_2032):
                        cast_data["temp_20h_32h_max"] = temp_2032[i].get("max")
                        cast_data["temp_20h_32h_min"] = temp_2032[i].get("min")

                    # 白天/夜间降水概率
                    if i < len(precip_0820):
                        cast_data["precip_08h_20h_prob"] = precip_0820[i].get("probability", 0)
                    if i < len(precip_2032):
                        cast_data["precip_20h_32h_prob"] = precip_2032[i].get("probability", 0)

                    # 生活指数
                    life_labels = {
                        "ultraviolet": "紫外线",
                        "dressing": "穿衣",
                        "comfort": "舒适度",
                        "coldRisk": "感冒",
                        "carWashing": "洗车",
                    }
                    for key, label in life_labels.items():
                        idx_list = life_index.get(key, [])
                        if i < len(idx_list):
                            idx_item = idx_list[i]
                            cast_data[f"life_{key}"] = {
                                "index": idx_item.get("index", ""),
                                "desc": idx_item.get("desc", ""),
                                "label": label,
                            }

                    weather_data["forecast"]["casts"].append(cast_data)

                # ---- 解析每日空气质量（供晚间模式使用）----
                daily_aq = daily_data.get("air_quality", {})
                if daily_aq:
                    weather_data["daily_aqi"] = {
                        "aqi": daily_aq.get("aqi", []),
                        "pm25": daily_aq.get("pm25", []),
                    }

            return weather_data

        except requests.exceptions.Timeout:
            return {"success": False, "error": "请求超时，请检查网络连接"}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"网络请求失败: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"数据解析异常: {str(e)}"}


# ================================================================
#  高德天气 API（备用数据源）
# ================================================================

class WeatherAPI:
    """高德天气 API 封装，支持城市名/adcode/经纬度查询"""

    _API_URL: str = "https://restapi.amap.com/v3/weather/weatherInfo"
    _GEO_URL: str = "https://restapi.amap.com/v3/geocode/regeo"
    _LATLNG_RE = re.compile(r"^-?\d+\.?\d*,-?\d+\.?\d*$")

    @classmethod
    def _is_latlng(cls, location: str) -> bool:
        """判断字符串是否为经纬度格式（如 "116.3176,39.9760"）"""
        return bool(cls._LATLNG_RE.match(location.strip()))

    @classmethod
    def _latlng_to_adcode(cls, location: str, amap_key: str) -> Optional[dict]:
        """通过高德逆地理编码将经纬度转换为 adcode（行政区划代码）"""
        try:
            resp = requests.get(
                cls._GEO_URL,
                params={"key": amap_key, "location": location, "extensions": "base", "output": "JSON"},
                timeout=10,
            )
            resp.raise_for_status()
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
    def get_weather(
        cls, city_or_location: str, amap_key: str, extensions: str = "base"
    ) -> dict[str, Any]:
        """
        获取高德天气数据（统一返回格式）。

        Args:
            city_or_location: 城市名、adcode 或经纬度
            amap_key: 高德 API Key
            extensions: "base" 实况 / "all" 实况+预报
        """
        params = {
            "key": amap_key,
            "extensions": extensions,
            "output": "JSON",
            "gzip": "n",
        }

        city_code = city_or_location
        if cls._is_latlng(city_or_location):
            geo = cls._latlng_to_adcode(city_or_location, amap_key)
            if geo and geo.get("adcode"):
                city_code = geo["adcode"]
            else:
                return {"success": False, "error": "经纬度解析失败, 无法获取对应城市信息"}

        params["city"] = city_code

        try:
            resp = requests.get(cls._API_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "1" or data.get("infocode") != "10000":
                return {
                    "success": False,
                    "error": f"{data.get('info', '请求失败')} ({data.get('infocode')})",
                }

            result: dict[str, Any] = {
                "success": True,
                "city": None,
                "live": None,
                "forecast": None,
                "hourly_forecast": [],
                "forecast_keypoint": "",
                "hourly_description": "",
                "daily_aqi": None,
                "source": "gaode",
                "error": None,
            }

            # 实况
            if "lives" in data and isinstance(data["lives"], list) and data["lives"]:
                live = data["lives"][0]
                result["city"] = live.get("city", "未知城市")
                result["live"] = {
                    "city": live.get("city", ""),
                    "weather": live.get("weather", "无数据"),
                    "temperature": float(live.get("temperature", 0)) if live.get("temperature") else None,
                    "wind_direction": live.get("winddirection", "无风向"),
                    "wind_power": live.get("windpower", "0"),
                    "humidity": int(live.get("humidity", 0)) if live.get("humidity") else None,
                    "report_time": live.get("reporttime", ""),
                }

            # 预报
            if extensions == "all" and "forecasts" in data and data["forecasts"]:
                forecast = data["forecasts"][0]
                result["forecast"] = {
                    "city": forecast.get("city", ""),
                    "report_time": forecast.get("reporttime", ""),
                    "casts": [],
                }
                for cast in forecast.get("casts", []):
                    result["forecast"]["casts"].append({
                        "date": cast.get("date", ""),
                        "week": cast.get("week", ""),
                        "day_weather": cast.get("dayweather", ""),
                        "night_weather": cast.get("nightweather", ""),
                        "day_temp": float(cast.get("daytemp", 0)) if cast.get("daytemp") else None,
                        "night_temp": float(cast.get("nighttemp", 0)) if cast.get("nighttemp") else None,
                    })

            return result

        except requests.exceptions.Timeout:
            return {"success": False, "error": "请求超时，请检查网络连接"}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"网络请求失败: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"数据解析异常: {str(e)}"}
