from __future__ import annotations

import argparse
import sys
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR))

from email_generator import generate_html

BEIJING_TZ = timezone(timedelta(hours=8))
TODAY = datetime.now(BEIJING_TZ).date()


def date_str(day) -> str:
    return day.strftime("%Y-%m-%d")


def dt_str(day, hour: int, minute: int = 0) -> str:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=BEIJING_TZ).isoformat(timespec="minutes")


def life_pack(uv: str, dressing: str, comfort: str, cold: str, car: str) -> dict[str, Any]:
    return {
        "life_ultraviolet": {"desc": uv},
        "life_dressing": {"desc": dressing},
        "life_comfort": {"desc": comfort},
        "life_coldRisk": {"desc": cold},
        "life_carWashing": {"desc": car},
    }


def build_hourly(day, periods: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for period in periods:
        start = period["start"]
        end = period["end"]
        temp_min = float(period["temp_min"])
        temp_max = float(period["temp_max"])
        span = max(end - start, 1)
        for idx, hour in enumerate(range(start, end + 1)):
            ratio = idx / span
            temp = temp_min + (temp_max - temp_min) * ratio
            items.append(
                {
                    "datetime": dt_str(day, hour),
                    "weather": period["weather"],
                    "skycon": period.get("skycon", period["weather"]),
                    "temperature": round(temp, 1),
                    "apparent_temperature": round(temp - period.get("apparent_offset", 1.0), 1),
                    "wind_direction": period.get("wind_direction", "东北风"),
                    "wind_power": period.get("wind_power", 2),
                    "wind_speed": period.get("wind_speed", 2.0),
                    "humidity": period.get("humidity", 50),
                    "precipitation": period.get("precipitation", 0),
                    "precip_probability": period.get("precip_probability", 0),
                }
            )
    return items


def build_weather(spec: dict[str, Any]) -> dict[str, Any]:
    day = TODAY
    tomorrow = TODAY + timedelta(days=1)

    live = {
        "city": spec["city"],
        "skycon": spec.get("live_skycon", spec["periods"][0]["skycon"]),
        "weather": spec.get("live_weather", spec["periods"][0]["weather"]),
        "temperature": spec.get("live_temp", spec["periods"][0]["temp_min"]),
        "apparent_temperature": spec.get("live_temp", spec["periods"][0]["temp_min"]),
        "humidity": spec.get("live_humidity", 60),
        "wind_direction": spec.get("live_wind_direction", "东北风"),
        "wind_power": spec.get("live_wind_power", 2),
        "wind_speed": spec.get("live_wind_speed", 2.0),
        "pressure": spec.get("live_pressure", 1013.2),
        "visibility": spec.get("live_visibility", 12),
        "cloudrate": spec.get("live_cloudrate", 40),
        "report_time": dt_str(day, 8, 30),
        "aqi": spec.get("aqi", 42),
        "aqi_usa": spec.get("aqi_usa", 35),
        "pm25": spec.get("pm25", 18),
        "pm10": spec.get("pm10", 28),
        "o3": spec.get("o3", 70),
        "air_desc": spec.get("air_desc", "空气质量良好"),
        "precip_intensity": spec.get("precip_intensity", 0),
    }

    forecast = {
        "casts": [
            {
                "date": date_str(day),
                "skycon": spec.get("hero_skycon", spec["periods"][0]["skycon"]),
                "day_weather": spec.get("day_weather", spec["periods"][0]["weather"]),
                "night_weather": spec.get("night_weather", spec["periods"][-1]["weather"]),
                "day_temp": spec.get("day_temp", spec["periods"][1]["temp_max"]),
                "night_temp": spec.get("night_temp", spec["periods"][-1]["temp_min"]),
                "sunrise": spec.get("sunrise", "06:08"),
                "sunset": spec.get("sunset", "18:52"),
                **life_pack(spec["life"]["uv"], spec["life"]["dressing"], spec["life"]["comfort"], spec["life"]["cold"], spec["life"]["car"]),
            },
            {
                "date": date_str(tomorrow),
                "skycon": spec.get("tomorrow_skycon", spec.get("hero_skycon", spec["periods"][0]["skycon"])),
                "day_weather": spec.get("tomorrow_day_weather", spec.get("day_weather", spec["periods"][0]["weather"])),
                "night_weather": spec.get("tomorrow_night_weather", spec.get("night_weather", spec["periods"][-1]["weather"])),
                "day_temp": spec.get("tomorrow_day_temp", spec.get("day_temp", spec["periods"][1]["temp_max"])),
                "night_temp": spec.get("tomorrow_night_temp", spec.get("night_temp", spec["periods"][-1]["temp_min"])),
                "sunrise": spec.get("tomorrow_sunrise", "06:07"),
                "sunset": spec.get("tomorrow_sunset", "18:53"),
                **life_pack(spec["life"]["uv"], spec["life"]["dressing"], spec["life"]["comfort"], spec["life"]["cold"], spec["life"]["car"]),
            },
        ]
    }

    return {
        "success": True,
        "city": spec["city"],
        "live": live,
        "forecast": forecast,
        "hourly_forecast": build_hourly(day, spec["periods"]),
        "forecast_keypoint": spec["forecast_keypoint"],
        "hourly_description": spec["hourly_description"],
        "daily_aqi": spec.get("daily_aqi"),
        "source": "caiyun",
        "error": None,
    }


SCENARIOS: list[dict[str, Any]] = [
    {
        "theme_key": "sunny",
        "title": "晴天",
        "city": "北京 · 晴天",
        "live_weather": "晴",
        "live_skycon": "CLEAR_DAY",
        "live_temp": 25,
        "live_humidity": 42,
        "live_cloudrate": 12,
        "day_weather": "晴",
        "night_weather": "晴",
        "day_temp": 28,
        "night_temp": 18,
        "forecast_keypoint": "阳光充足，适合出行和晾晒。",
        "hourly_description": "今日以晴为主，午后体感舒适。",
        "life": {"uv": "强，注意防晒", "dressing": "短袖为主", "comfort": "舒适", "cold": "低", "car": "适宜"},
        "periods": [
            {"start": 6, "end": 11, "weather": "晴", "skycon": "CLEAR_DAY", "temp_min": 19, "temp_max": 24, "humidity": 44, "wind_direction": "东风", "wind_power": 2, "wind_speed": 2.1},
            {"start": 12, "end": 17, "weather": "晴", "skycon": "CLEAR_DAY", "temp_min": 24, "temp_max": 28, "humidity": 39, "wind_direction": "东南风", "wind_power": 2, "wind_speed": 2.4},
            {"start": 18, "end": 23, "weather": "晴", "skycon": "CLEAR_NIGHT", "temp_min": 20, "temp_max": 23, "humidity": 51, "wind_direction": "北风", "wind_power": 1, "wind_speed": 1.3},
        ],
    },
    {
        "theme_key": "haze",
        "title": "晴间多云",
        "city": "北京 · 晴间多云",
        "live_weather": "晴间多云",
        "live_skycon": "PARTLY_CLOUDY_DAY",
        "live_temp": 24,
        "live_humidity": 48,
        "live_cloudrate": 38,
        "day_weather": "晴间多云",
        "night_weather": "多云",
        "day_temp": 26,
        "night_temp": 17,
        "forecast_keypoint": "阳光与云层交替，体感偏柔和。",
        "hourly_description": "今天云量会逐渐增多，但整体还算舒服。",
        "life": {"uv": "中等", "dressing": "薄外套/长袖", "comfort": "较舒适", "cold": "低", "car": "适宜"},
        "periods": [
            {"start": 6, "end": 11, "weather": "晴间多云", "skycon": "PARTLY_CLOUDY_DAY", "temp_min": 18, "temp_max": 23, "humidity": 47, "wind_direction": "东北风", "wind_power": 2, "wind_speed": 2.0},
            {"start": 12, "end": 17, "weather": "多云", "skycon": "PARTLY_CLOUDY_DAY", "temp_min": 23, "temp_max": 26, "humidity": 42, "wind_direction": "东风", "wind_power": 2, "wind_speed": 2.5},
            {"start": 18, "end": 23, "weather": "多云", "skycon": "PARTLY_CLOUDY_NIGHT", "temp_min": 19, "temp_max": 22, "humidity": 54, "wind_direction": "东南风", "wind_power": 1, "wind_speed": 1.6},
        ],
    },
    {
        "theme_key": "cloudy_light",
        "title": "多云",
        "city": "北京 · 多云",
        "live_weather": "多云",
        "live_skycon": "PARTLY_CLOUDY_DAY",
        "live_temp": 23,
        "live_humidity": 50,
        "live_cloudrate": 62,
        "day_weather": "多云",
        "night_weather": "多云",
        "day_temp": 25,
        "night_temp": 17,
        "forecast_keypoint": "云层较多，但整体还算通透。",
        "hourly_description": "今天云比较厚，适合轻装出门。",
        "life": {"uv": "中等", "dressing": "长袖/薄外套", "comfort": "平稳", "cold": "低", "car": "适宜"},
        "periods": [
            {"start": 6, "end": 11, "weather": "多云", "skycon": "PARTLY_CLOUDY_DAY", "temp_min": 18, "temp_max": 22, "humidity": 52, "wind_direction": "东风", "wind_power": 2, "wind_speed": 2.1},
            {"start": 12, "end": 17, "weather": "多云", "skycon": "PARTLY_CLOUDY_DAY", "temp_min": 22, "temp_max": 25, "humidity": 48, "wind_direction": "东南风", "wind_power": 2, "wind_speed": 2.4},
            {"start": 18, "end": 23, "weather": "多云", "skycon": "PARTLY_CLOUDY_NIGHT", "temp_min": 17, "temp_max": 20, "humidity": 57, "wind_direction": "东北风", "wind_power": 1, "wind_speed": 1.5},
        ],
    },
    {
        "theme_key": "cloudy_deep",
        "title": "阴天",
        "city": "北京 · 阴天",
        "live_weather": "阴",
        "live_skycon": "CLOUDY",
        "live_temp": 21,
        "live_humidity": 56,
        "live_cloudrate": 78,
        "day_weather": "阴",
        "night_weather": "阴",
        "day_temp": 23,
        "night_temp": 16,
        "forecast_keypoint": "云层较厚，整体平稳。",
        "hourly_description": "阴天为主，光线偏柔，适合室内外切换。",
        "life": {"uv": "弱", "dressing": "长袖/薄外套", "comfort": "平稳", "cold": "低", "car": "适宜"},
        "periods": [
            {"start": 6, "end": 11, "weather": "阴", "skycon": "CLOUDY", "temp_min": 17, "temp_max": 21, "humidity": 58, "wind_direction": "北风", "wind_power": 2, "wind_speed": 2.0},
            {"start": 12, "end": 17, "weather": "阴", "skycon": "CLOUDY", "temp_min": 20, "temp_max": 23, "humidity": 55, "wind_direction": "东北风", "wind_power": 2, "wind_speed": 2.2},
            {"start": 18, "end": 23, "weather": "阴", "skycon": "CLOUDY", "temp_min": 16, "temp_max": 19, "humidity": 63, "wind_direction": "东风", "wind_power": 1, "wind_speed": 1.5},
        ],
    },
    {
        "theme_key": "rainy_light",
        "title": "小雨",
        "city": "北京 · 小雨",
        "live_weather": "小雨",
        "live_skycon": "LIGHT_RAIN",
        "live_temp": 20,
        "live_humidity": 78,
        "live_cloudrate": 88,
        "live_precip_intensity": 0.15,
        "day_weather": "小雨",
        "night_weather": "小雨",
        "day_temp": 22,
        "night_temp": 17,
        "forecast_keypoint": "有零星降水，出门带伞更稳妥。",
        "hourly_description": "今天会有间歇性小雨，体感略潮湿。",
        "life": {"uv": "弱", "dressing": "薄外套/雨具", "comfort": "偏潮湿", "cold": "中", "car": "不宜"},
        "periods": [
            {"start": 6, "end": 11, "weather": "小雨", "skycon": "LIGHT_RAIN", "temp_min": 18, "temp_max": 20, "humidity": 82, "wind_direction": "东北风", "wind_power": 2, "wind_speed": 2.0, "precip_probability": 55, "precipitation": 0.2},
            {"start": 12, "end": 17, "weather": "阵雨", "skycon": "LIGHT_RAIN", "temp_min": 20, "temp_max": 22, "humidity": 79, "wind_direction": "东风", "wind_power": 2, "wind_speed": 2.6, "precip_probability": 72, "precipitation": 0.4},
            {"start": 18, "end": 23, "weather": "小雨", "skycon": "LIGHT_RAIN", "temp_min": 17, "temp_max": 19, "humidity": 84, "wind_direction": "东南风", "wind_power": 1, "wind_speed": 1.8, "precip_probability": 68, "precipitation": 0.3},
        ],
    },
    {
        "theme_key": "rainy_deep",
        "title": "暴雨",
        "city": "北京 · 暴雨",
        "live_weather": "暴雨",
        "live_skycon": "STORM_RAIN",
        "live_temp": 19,
        "live_humidity": 91,
        "live_cloudrate": 96,
        "live_precip_intensity": 1.8,
        "day_weather": "大雨",
        "night_weather": "暴雨",
        "day_temp": 21,
        "night_temp": 16,
        "forecast_keypoint": "降水较强，尽量减少户外停留。",
        "hourly_description": "今天雨势较强，出行请提前规划路线。",
        "life": {"uv": "很弱", "dressing": "防水外套", "comfort": "潮湿", "cold": "中", "car": "不宜"},
        "periods": [
            {"start": 6, "end": 11, "weather": "大雨", "skycon": "HEAVY_RAIN", "temp_min": 18, "temp_max": 19, "humidity": 90, "wind_direction": "东北风", "wind_power": 3, "wind_speed": 4.0, "precip_probability": 88, "precipitation": 1.5},
            {"start": 12, "end": 17, "weather": "暴雨", "skycon": "STORM_RAIN", "temp_min": 19, "temp_max": 21, "humidity": 92, "wind_direction": "东风", "wind_power": 4, "wind_speed": 5.5, "precip_probability": 95, "precipitation": 2.2},
            {"start": 18, "end": 23, "weather": "中雨", "skycon": "MODERATE_RAIN", "temp_min": 16, "temp_max": 18, "humidity": 93, "wind_direction": "东南风", "wind_power": 3, "wind_speed": 4.2, "precip_probability": 86, "precipitation": 1.1},
        ],
    },
    {
        "theme_key": "snow",
        "title": "小雪",
        "city": "北京 · 小雪",
        "live_weather": "小雪",
        "live_skycon": "LIGHT_SNOW",
        "live_temp": 0,
        "live_humidity": 76,
        "live_cloudrate": 84,
        "day_weather": "小雪",
        "night_weather": "中雪",
        "day_temp": 2,
        "night_temp": -4,
        "forecast_keypoint": "气温较低，路面湿滑，请注意保暖。",
        "hourly_description": "今天有降雪过程，体感偏冷。",
        "life": {"uv": "弱", "dressing": "厚外套/羽绒服", "comfort": "寒冷", "cold": "高", "car": "不宜"},
        "periods": [
            {"start": 6, "end": 11, "weather": "小雪", "skycon": "LIGHT_SNOW", "temp_min": -2, "temp_max": 0, "humidity": 78, "wind_direction": "北风", "wind_power": 2, "wind_speed": 2.2, "precip_probability": 52, "precipitation": 0.2},
            {"start": 12, "end": 17, "weather": "中雪", "skycon": "MODERATE_SNOW", "temp_min": 0, "temp_max": 2, "humidity": 74, "wind_direction": "东北风", "wind_power": 2, "wind_speed": 2.5, "precip_probability": 68, "precipitation": 0.4},
            {"start": 18, "end": 23, "weather": "小雪", "skycon": "LIGHT_SNOW", "temp_min": -4, "temp_max": -1, "humidity": 80, "wind_direction": "东风", "wind_power": 1, "wind_speed": 1.4, "precip_probability": 60, "precipitation": 0.3},
        ],
    },
    {
        "theme_key": "snow_deep",
        "title": "大雪",
        "city": "北京 · 大雪",
        "live_weather": "大雪",
        "live_skycon": "HEAVY_SNOW",
        "live_temp": -2,
        "live_humidity": 79,
        "live_cloudrate": 88,
        "day_weather": "大雪",
        "night_weather": "暴雪",
        "day_temp": -1,
        "night_temp": -6,
        "forecast_keypoint": "雪势增强，注意积雪和路面结冰。",
        "hourly_description": "今天大雪持续，注意保暖和交通安全。",
        "life": {"uv": "弱", "dressing": "厚羽绒服", "comfort": "严寒", "cold": "高", "car": "不宜"},
        "periods": [
            {"start": 6, "end": 11, "weather": "大雪", "skycon": "HEAVY_SNOW", "temp_min": -5, "temp_max": -2, "humidity": 82, "wind_direction": "北风", "wind_power": 2, "wind_speed": 2.1, "precip_probability": 72, "precipitation": 0.4},
            {"start": 12, "end": 17, "weather": "暴雪", "skycon": "STORM_SNOW", "temp_min": -3, "temp_max": -1, "humidity": 80, "wind_direction": "东北风", "wind_power": 3, "wind_speed": 3.6, "precip_probability": 90, "precipitation": 0.8},
            {"start": 18, "end": 23, "weather": "大雪", "skycon": "HEAVY_SNOW", "temp_min": -6, "temp_max": -3, "humidity": 84, "wind_direction": "东风", "wind_power": 2, "wind_speed": 2.4, "precip_probability": 78, "precipitation": 0.5},
        ],
    },
    {
        "theme_key": "fog",
        "title": "薄雾",
        "city": "北京 · 薄雾",
        "live_weather": "雾",
        "live_skycon": "FOG",
        "live_temp": 16,
        "live_humidity": 88,
        "live_cloudrate": 86,
        "live_visibility": 4,
        "day_weather": "雾",
        "night_weather": "霾",
        "day_temp": 18,
        "night_temp": 12,
        "forecast_keypoint": "能见度偏低，注意通行安全。",
        "hourly_description": "今天雾气较重，外出建议做好防护。",
        "life": {"uv": "很弱", "dressing": "长袖/薄外套", "comfort": "闷湿", "cold": "中", "car": "一般"},
        "periods": [
            {"start": 6, "end": 11, "weather": "雾", "skycon": "FOG", "temp_min": 14, "temp_max": 16, "humidity": 90, "wind_direction": "北风", "wind_power": 1, "wind_speed": 1.2, "precip_probability": 8, "precipitation": 0},
            {"start": 12, "end": 17, "weather": "霾", "skycon": "LIGHT_HAZE", "temp_min": 16, "temp_max": 18, "humidity": 86, "wind_direction": "东北风", "wind_power": 1, "wind_speed": 1.5, "precip_probability": 10, "precipitation": 0},
            {"start": 18, "end": 23, "weather": "浓雾", "skycon": "FOG", "temp_min": 12, "temp_max": 14, "humidity": 91, "wind_direction": "东风", "wind_power": 1, "wind_speed": 1.1, "precip_probability": 6, "precipitation": 0},
        ],
    },
    {
        "theme_key": "fog_deep",
        "title": "浓雾",
        "city": "北京 · 浓雾",
        "live_weather": "浓雾",
        "live_skycon": "FOG",
        "live_temp": 15,
        "live_humidity": 92,
        "live_cloudrate": 90,
        "live_visibility": 2,
        "day_weather": "大雾",
        "night_weather": "浓雾",
        "day_temp": 17,
        "night_temp": 11,
        "forecast_keypoint": "能见度较低，出行请注意安全。",
        "hourly_description": "浓雾持续，注意道路和交通安全。",
        "life": {"uv": "很弱", "dressing": "长袖/薄外套", "comfort": "闷湿", "cold": "中", "car": "一般"},
        "periods": [
            {"start": 6, "end": 11, "weather": "大雾", "skycon": "FOG", "temp_min": 13, "temp_max": 15, "humidity": 93, "wind_direction": "北风", "wind_power": 1, "wind_speed": 1.0, "precip_probability": 5, "precipitation": 0},
            {"start": 12, "end": 17, "weather": "浓雾", "skycon": "FOG", "temp_min": 15, "temp_max": 17, "humidity": 92, "wind_direction": "东北风", "wind_power": 1, "wind_speed": 1.2, "precip_probability": 8, "precipitation": 0},
            {"start": 18, "end": 23, "weather": "重霾", "skycon": "LIGHT_HAZE", "temp_min": 11, "temp_max": 13, "humidity": 94, "wind_direction": "东风", "wind_power": 1, "wind_speed": 1.0, "precip_probability": 5, "precipitation": 0},
        ],
    },
    {
        "theme_key": "wind",
        "title": "微风",
        "city": "北京 · 微风",
        "live_weather": "微风",
        "live_skycon": "WIND",
        "live_temp": 22,
        "live_humidity": 46,
        "live_cloudrate": 35,
        "live_wind_power": 3,
        "day_weather": "微风",
        "night_weather": "微风",
        "day_temp": 24,
        "night_temp": 18,
        "forecast_keypoint": "风力不大，体感清爽。",
        "hourly_description": "今天有轻风，适合轻装出门。",
        "life": {"uv": "中等", "dressing": "长袖/薄外套", "comfort": "舒适", "cold": "低", "car": "适宜"},
        "periods": [
            {"start": 6, "end": 11, "weather": "微风", "skycon": "WIND", "temp_min": 17, "temp_max": 21, "humidity": 48, "wind_direction": "东风", "wind_power": 3, "wind_speed": 4.2, "precip_probability": 0, "precipitation": 0},
            {"start": 12, "end": 17, "weather": "和风", "skycon": "WIND", "temp_min": 21, "temp_max": 24, "humidity": 43, "wind_direction": "东南风", "wind_power": 3, "wind_speed": 4.6, "precip_probability": 0, "precipitation": 0},
            {"start": 18, "end": 23, "weather": "微风", "skycon": "WIND", "temp_min": 18, "temp_max": 20, "humidity": 50, "wind_direction": "东北风", "wind_power": 2, "wind_speed": 2.8, "precip_probability": 0, "precipitation": 0},
        ],
    },
    {
        "theme_key": "wind_deep",
        "title": "大风",
        "city": "北京 · 大风",
        "live_weather": "大风",
        "live_skycon": "WIND",
        "live_temp": 20,
        "live_humidity": 44,
        "live_cloudrate": 30,
        "live_wind_power": 5,
        "day_weather": "大风",
        "night_weather": "强风",
        "day_temp": 22,
        "night_temp": 16,
        "forecast_keypoint": "风力偏大，出行注意防风。",
        "hourly_description": "今天阵风较明显，建议固定好随身物品。",
        "life": {"uv": "中等", "dressing": "防风外套", "comfort": "偏风", "cold": "中", "car": "一般"},
        "periods": [
            {"start": 6, "end": 11, "weather": "大风", "skycon": "WIND", "temp_min": 16, "temp_max": 20, "humidity": 46, "wind_direction": "北风", "wind_power": 5, "wind_speed": 8.0, "precip_probability": 0, "precipitation": 0},
            {"start": 12, "end": 17, "weather": "强风", "skycon": "WIND", "temp_min": 20, "temp_max": 22, "humidity": 42, "wind_direction": "东北风", "wind_power": 6, "wind_speed": 10.5, "precip_probability": 0, "precipitation": 0},
            {"start": 18, "end": 23, "weather": "大风", "skycon": "WIND", "temp_min": 15, "temp_max": 18, "humidity": 49, "wind_direction": "东风", "wind_power": 5, "wind_speed": 8.8, "precip_probability": 0, "precipitation": 0},
        ],
    },
    {
        "theme_key": "thunder",
        "title": "雷阵雨",
        "city": "北京 · 雷阵雨",
        "live_weather": "雷阵雨",
        "live_skycon": "THUNDERSTORM",
        "live_temp": 23,
        "live_humidity": 84,
        "live_cloudrate": 94,
        "live_precip_intensity": 0.9,
        "day_weather": "雷阵雨",
        "night_weather": "阵雨",
        "day_temp": 25,
        "night_temp": 18,
        "forecast_keypoint": "午后对流明显，注意雷雨天气。",
        "hourly_description": "今天有雷阵雨过程，请注意防雷和防雨。",
        "life": {"uv": "中等", "dressing": "雨具随身", "comfort": "闷热", "cold": "低", "car": "不宜"},
        "periods": [
            {"start": 6, "end": 11, "weather": "雷阵雨", "skycon": "THUNDERSTORM", "temp_min": 21, "temp_max": 23, "humidity": 86, "wind_direction": "东北风", "wind_power": 3, "wind_speed": 4.5, "precip_probability": 70, "precipitation": 0.5},
            {"start": 12, "end": 17, "weather": "雷阵雨", "skycon": "THUNDERSTORM", "temp_min": 23, "temp_max": 25, "humidity": 82, "wind_direction": "东风", "wind_power": 4, "wind_speed": 5.4, "precip_probability": 88, "precipitation": 1.0},
            {"start": 18, "end": 23, "weather": "阵雨", "skycon": "SHOWERS", "temp_min": 18, "temp_max": 21, "humidity": 85, "wind_direction": "东南风", "wind_power": 2, "wind_speed": 2.8, "precip_probability": 58, "precipitation": 0.3},
        ],
    },
    {
        "theme_key": "thunder_deep",
        "title": "强雷暴",
        "city": "北京 · 强雷暴",
        "live_weather": "强雷暴",
        "live_skycon": "THUNDERSTORM",
        "live_temp": 24,
        "live_humidity": 87,
        "live_cloudrate": 98,
        "live_precip_intensity": 1.4,
        "day_weather": "强雷暴",
        "night_weather": "雷暴",
        "day_temp": 26,
        "night_temp": 19,
        "forecast_keypoint": "强对流明显，请远离高处和金属构筑物。",
        "hourly_description": "今天强雷暴来袭，注意及时避雨防雷。",
        "life": {"uv": "中等", "dressing": "雨具随身", "comfort": "闷热", "cold": "低", "car": "不宜"},
        "periods": [
            {"start": 6, "end": 11, "weather": "雷暴", "skycon": "THUNDERSTORM", "temp_min": 22, "temp_max": 24, "humidity": 88, "wind_direction": "东北风", "wind_power": 4, "wind_speed": 5.1, "precip_probability": 82, "precipitation": 0.8},
            {"start": 12, "end": 17, "weather": "强雷暴", "skycon": "THUNDERSTORM", "temp_min": 24, "temp_max": 26, "humidity": 85, "wind_direction": "东风", "wind_power": 5, "wind_speed": 6.8, "precip_probability": 96, "precipitation": 1.6},
            {"start": 18, "end": 23, "weather": "雷暴", "skycon": "THUNDERSTORM", "temp_min": 19, "temp_max": 22, "humidity": 88, "wind_direction": "东南风", "wind_power": 4, "wind_speed": 5.0, "precip_probability": 74, "precipitation": 0.6},
        ],
    },
    {
        "theme_key": "extreme",
        "title": "高温",
        "city": "北京 · 高温",
        "live_weather": "高温",
        "live_skycon": "CLEAR_DAY",
        "live_temp": 37,
        "live_humidity": 32,
        "live_cloudrate": 8,
        "day_weather": "晴",
        "night_weather": "晴",
        "day_temp": 39,
        "night_temp": 28,
        "forecast_keypoint": "高温持续，注意防暑降温。",
        "hourly_description": "今天进入高温时段，尽量避免长时间暴晒。",
        "life": {"uv": "很强", "dressing": "清凉短袖", "comfort": "炎热", "cold": "低", "car": "不宜"},
        "periods": [
            {"start": 6, "end": 11, "weather": "晴", "skycon": "CLEAR_DAY", "temp_min": 31, "temp_max": 35, "humidity": 35, "wind_direction": "东风", "wind_power": 2, "wind_speed": 2.5, "precip_probability": 0, "precipitation": 0},
            {"start": 12, "end": 17, "weather": "高温", "skycon": "CLEAR_DAY", "temp_min": 35, "temp_max": 39, "humidity": 30, "wind_direction": "东南风", "wind_power": 2, "wind_speed": 2.8, "precip_probability": 0, "precipitation": 0},
            {"start": 18, "end": 23, "weather": "晴", "skycon": "CLEAR_NIGHT", "temp_min": 28, "temp_max": 32, "humidity": 40, "wind_direction": "北风", "wind_power": 1, "wind_speed": 1.5, "precip_probability": 0, "precipitation": 0},
        ],
    },
]


def write_index(out_dir: Path, outputs: list[dict[str, Any]]) -> Path:
    rows = []
    for item in outputs:
        rows.append(
            f'<li><a href="{item["filename"]}" target="_blank">{item["label"]}</a></li>'
        )
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Weather-Email 本地预览索引</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif; padding: 24px; color: #1f2937; }}
  h1 {{ font-size: 22px; margin-bottom: 8px; }}
  p {{ color: #6b7280; margin-bottom: 16px; }}
  ul {{ line-height: 1.9; padding-left: 20px; }}
  a {{ color: #2563eb; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .meta {{ color: #374151; margin-bottom: 16px; }}
</style>
</head>
<body>
  <h1>Weather-Email 本地预览索引</h1>
  <div class="meta">主题键总数：{len(SCENARIOS)}；当前生成：{len(outputs)} 个 HTML 文件</div>
  <p>点击下面文件，逐个查看不同天气主题下的邮件效果。</p>
  <ul>
    {''.join(rows)}
  </ul>
</body>
</html>"""
    path = out_dir / "preview_index.html"
    path.write_text(html, encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Weather-Email 本地多天气预览生成器")
    parser.add_argument(
        "--mode",
        choices=["morning", "evening", "both"],
        default="both",
        help="生成 morning / evening / both 的预览页面",
    )
    parser.add_argument("--open", action="store_true", help="生成后自动打开索引页")
    args = parser.parse_args()

    out_dir = PROJECT_DIR
    modes = [args.mode] if args.mode in {"morning", "evening"} else ["morning", "evening"]

    outputs: list[dict[str, Any]] = []
    for idx, spec in enumerate(SCENARIOS, start=1):
        weather = build_weather(spec)
        for mode in modes:
            subject, html = generate_html(weather, mode=mode)
            filename = f"preview_{idx:02d}_{mode}_{spec['theme_key']}.html"
            (out_dir / filename).write_text(html, encoding="utf-8")
            outputs.append(
                {
                    "label": f"{idx:02d}. {spec['title']} · {spec['theme_key']} · {mode} · {subject}",
                    "filename": filename,
                }
            )
            print(f"✓ {filename}  ->  {subject}")

    index_path = write_index(out_dir, outputs)
    print(f"\n主题总数: {len(SCENARIOS)}")
    print(f"输出文件数: {len(outputs)}")
    print(f"索引页: {index_path}")
    print(f"输出目录: {out_dir}")

    if args.open:
        webbrowser.open(index_path.as_uri())


if __name__ == "__main__":
    main()
