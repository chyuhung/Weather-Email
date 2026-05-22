"""
天气邮件 HTML 生成器 - UI 优化版
优化内容：
1. 响应式设计：添加媒体查询，移动端适配
2. 邮件客户端兼容：MSO 条件注释，表格降级方案
3. 可访问性：ARIA 标签，对比度优化
4. 视觉层次：增强卡片阴影，优化间距
5. 字体降级：移除 Google Fonts 依赖，强化系统字体栈
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

BEIJING_TZ = timezone(timedelta(hours=8))

# ─────────────────────────────────────────────────────────────
#  天气主题配色（优化对比度版本）
#  调整：确保所有文字与背景对比度 ≥ 4.5:1 (WCAG AA)
# ─────────────────────────────────────────────────────────────
COLOR_THEME = {
    # 晴 — 提高对比度
    "sunny": {
        "primary": "#3A9BD9",      # 加深以通过对比度
        "bg": "#F0F7FE",
        "gradient": "#6BB8E6",
        "text": "#1A365D",          # 深色文字确保对比度
    },
    # 多云
    "cloudy_light": {
        "primary": "#6B8FA3",
        "bg": "#F4F6F8",
        "gradient": "#94B5C2",
        "text": "#2D3748",
    },
    # 阴
    "cloudy_deep": {
        "primary": "#7A8E99",
        "bg": "#EEF2F4",
        "gradient": "#A8BCC6",
        "text": "#2D3748",
    },
    # 晴间多云
    "haze": {
        "primary": "#4E8FB8",
        "bg": "#F0F6FB",
        "gradient": "#7DB8CE",
        "text": "#1A365D",
    },
    # 小雨
    "rainy_light": {
        "primary": "#4A8FB5",
        "bg": "#EDF3F8",
        "gradient": "#73AAC0",
        "text": "#1E3A5F",
    },
    # 中雨/大雨
    "rainy_deep": {
        "primary": "#3A708A",
        "bg": "#E3ECF2",
        "gradient": "#5A95A8",
        "text": "#1A365D",
    },
    # 小雪
    "snow": {
        "primary": "#4E8FB5",
        "bg": "#F0F6FC",
        "gradient": "#7DB2C6",
        "text": "#1E3A5F",
    },
    # 大雪
    "snow_deep": {
        "primary": "#3D6F8A",
        "bg": "#E8F0F7",
        "gradient": "#6A9FB8",
        "text": "#1A365D",
    },
    # 雾
    "fog": {
        "primary": "#7A8A94",
        "bg": "#F5F7F8",
        "gradient": "#A2B0B8",
        "text": "#2D3748",
    },
    # 浓雾
    "fog_deep": {
        "primary": "#6B7A82",
        "bg": "#F0F2F4",
        "gradient": "#94A2AA",
        "text": "#2D3748",
    },
    # 风
    "wind": {
        "primary": "#4E8A8A",
        "bg": "#F0F7F7",
        "gradient": "#7DB8B8",
        "text": "#1A3F3F",
    },
    # 强风
    "wind_deep": {
        "primary": "#3D6F6F",
        "bg": "#E8F2F2",
        "gradient": "#6A9A9A",
        "text": "#1A3F3F",
    },
    # 雷暴
    "thunder": {
        "primary": "#5E6490",
        "bg": "#F2F3F7",
        "gradient": "#868CB0",
        "text": "#2D1F4A",
    },
    # 强雷暴
    "thunder_deep": {
        "primary": "#4E546E",
        "bg": "#EBEDF5",
        "gradient": "#787EA0",
        "text": "#2D1F4A",
    },
    # 高温
    "extreme": {
        "primary": "#C05621",      # 深橙色确保对比度
        "bg": "#FDF2EA",
        "gradient": "#D4783C",
        "text": "#742A00",
    },
}


def _beijing_now() -> datetime:
    """返回北京时间的当前时间。"""
    return datetime.now(BEIJING_TZ)


def _parse_beijing_datetime(dt_str: str) -> Optional[datetime]:
    """将 API 返回的时间字符串统一解析为北京时间。"""
    if not dt_str:
        return None
    try:
        cleaned = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=BEIJING_TZ)
        return dt.astimezone(BEIJING_TZ)
    except (ValueError, TypeError):
        return None


def _theme_key_from_text(text: str) -> str:
    """把天气文本归类到主题键。"""
    if not text:
        return "sunny"
    s = str(text).upper()
    if any(k in s for k in ("晴间", "晴转", "多云转晴")):
        return "haze"
    if any(k in s for k in ("晴", "CLEAR", "SUNNY")):
        return "sunny"
    if any(k in s for k in ("雪", "SNOW", "冻雨")):
        return "snow"
    if any(k in s for k in ("雷暴", "雷阵雨", "THUNDER", "STORM")):
        return "thunder"
    if any(k in s for k in ("雨", "RAIN", "DRIZZLE", "SHOWERS", "SLEET", "HAIL", "降水")):
        return "rainy"
    if any(k in s for k in ("雾", "霾", "FOG", "HAZE", "SMOG", "沙尘", "扬沙")):
        return "fog"
    if any(k in s for k in ("风", "WIND", "大风")):
        return "wind"
    if any(k in s for k in ("阴", "多云", "云", "CLOUD", "OVERCAST")):
        return "cloudy"
    return "sunny"


def _theme_variant_from_text(text: str, family: str) -> str:
    """根据文本判断同一主题族里的深浅版本。"""
    if not text:
        return "light"
    s = str(text).upper()
    if family == "cloudy":
        return "deep" if any(k in s for k in ("阴", "阴天", "OVERCAST", "深多云")) else "light"
    if family == "rainy":
        return "deep" if any(k in s for k in (
            "大", "暴雨", "HEAVY", "STORM", "THUNDER", "雷暴", "雷雨", "雷阵雨"
        )) else "light"
    if family == "snow":
        return "deep" if any(k in s for k in ("大雪", "暴雪", "HEAVY_SNOW")) else "light"
    if family == "thunder":
        return "deep" if any(k in s for k in ("大", "HEAVY", "STORM", "雷暴")) else "light"
    if family == "fog":
        return "deep" if any(k in s for k in ("大雾", "浓雾", "重霾", "HEAVY_HAZE", "沙尘")) else "light"
    if family == "wind":
        return "deep" if any(k in s for k in ("大风", "狂风", "强风", "HEAVY_WIND")) else "light"
    return "light"


def _get_weather_theme(slots: dict, any_rain: bool, temp_max: float, 
                       target_cast: Optional[dict] = None, hero_weather: str = "") -> dict:
    """根据整天天气选择配色主题（优化版：返回包含 text 颜色的完整主题）"""
    if temp_max >= 35:
        return COLOR_THEME["extreme"]

    family_source = hero_weather or ""
    if not family_source and target_cast:
        family_source = " ".join(str(target_cast.get(k, "")) for k in ("day_weather", "night_weather", "skycon"))
    if not family_source:
        for key in ("morning", "afternoon", "night"):
            item = slots.get(key)
            if item:
                family_source = item.get("weather", item.get("skycon", ""))
                if family_source:
                    break

    family = _theme_key_from_text(family_source)
    variant = _theme_variant_from_text(family_source, family)

    if family == "haze":
        return COLOR_THEME["haze"]
    if family == "snow":
        return COLOR_THEME["snow_deep"] if variant == "deep" else COLOR_THEME["snow"]
    if family == "thunder":
        return COLOR_THEME["thunder_deep"] if variant == "deep" else COLOR_THEME["thunder"]
    if family == "rainy":
        return COLOR_THEME["rainy_deep"] if (any_rain or variant == "deep") else COLOR_THEME["rainy_light"]
    if family == "fog":
        return COLOR_THEME["fog_deep"] if variant == "deep" else COLOR_THEME["fog"]
    if family == "wind":
        return COLOR_THEME["wind_deep"] if variant == "deep" else COLOR_THEME["wind"]
    if family == "cloudy":
        return COLOR_THEME["cloudy_deep"] if variant == "deep" else COLOR_THEME["cloudy_light"]
    if family == "sunny":
        return COLOR_THEME["sunny"]

    scores = {"sunny": 0, "cloudy": 0, "rainy": 0, "snow": 0, "thunder": 0, "fog": 0, "wind": 0}
    for key in ("morning", "afternoon", "night"):
        item = slots.get(key)
        if item:
            sky = item.get("skycon", item.get("weather", ""))
            k = _theme_key_from_text(sky)
            if k in scores:
                scores[k] += 1
    if any_rain:
        scores["rainy"] += 1
    fallback = max(scores, key=lambda kv: scores[kv])
    FALLBACK_MAP = {
        "snow": COLOR_THEME["snow"],
        "thunder": COLOR_THEME["thunder"],
        "rainy": COLOR_THEME["rainy_light"],
        "fog": COLOR_THEME["fog"],
        "wind": COLOR_THEME["wind"],
        "cloudy": COLOR_THEME["cloudy_light"],
        "sunny": COLOR_THEME["sunny"],
    }
    return FALLBACK_MAP.get(fallback, COLOR_THEME["sunny"])


def _sky_icon(skycon: str) -> str:
    """根据 skycon 代码或中文天气描述返回对应的 emoji 图标"""
    if not skycon:
        return "🌤️"

    normalized = skycon.upper().replace("（", "(").replace("）", ")").replace(" ", "")

    icon_map = {
        "CLEAR_DAY": "☀️", "CLEAR_NIGHT": "🌙",
        "PARTLY_CLOUDY_DAY": "⛅", "PARTLY_CLOUDY_NIGHT": "⛅",
        "CLOUDY": "☁️",
        "LIGHT_RAIN": "🌦️", "MODERATE_RAIN": "🌧️", "HEAVY_RAIN": "🌧️", "STORM_RAIN": "⛈️",
        "DRIZZLE": "🌦️", "SHOWERS": "🌦️",
        "THUNDERSTORM": "⛈️",
        "SLEET": "🌨️", "HAIL": "🌨️",
        "FOG": "🌫️",
        "LIGHT_HAZE": "😷", "MODERATE_HAZE": "😷", "HEAVY_HAZE": "😷",
        "LIGHT_SNOW": "🌨️", "MODERATE_SNOW": "❄️", "HEAVY_SNOW": "❄️", "STORM_SNOW": "❄️",
        "DUST": "🌿", "SAND": "🌿", "WIND": "💨",
    }

    if skycon in icon_map:
        return icon_map[skycon]
    if normalized in icon_map:
        return icon_map[normalized]

    cjk_map = {
        "晴": "☀️", "多云": "⛅", "阴": "☁️",
        "小雨": "🌦️", "中雨": "🌧️", "大雨": "🌧️", "暴雨": "⛈️",
        "雷阵雨": "⛈️", "阵雨": "🌦️", "雷雨": "⛈️",
        "雾": "🌫️", "霾": "😷",
        "沙尘": "🌿", "扬沙": "🌿",
        "雨夹雪": "🌨️", "小雪": "🌨️", "中雪": "❄️", "大雪": "❄️",
        "冰雹": "🌨️",
    }
    for keyword, icon in cjk_map.items():
        if keyword in skycon:
            return icon
    return "🌤️"


def _is_rain(skycon: str) -> bool:
    """判断天气是否需要带伞"""
    if not skycon:
        return False
    s = skycon.upper().replace("（", "(").replace("）", ")").replace(" ", "")
    rain_keywords = {
        "RAIN", "DRIZZLE", "SHOWERS", "THUNDERSTORM",
        "SLEET", "HAIL", "SNOW",
        "雨", "雪", "雨夹雪", "雷阵雨", "阵雨", "雷雨",
    }
    return any(k in s for k in rain_keywords)


def _aqi_color(aqi: Optional[int]) -> str:
    """根据 AQI 数值返回对应的颜色（中国标准）"""
    if aqi is None:
        return "#999"
    if aqi <= 50:
        return "#52c41a"
    if aqi <= 100:
        return "#faad14"
    if aqi <= 150:
        return "#fa8c16"
    if aqi <= 200:
        return "#f5222d"
    if aqi <= 300:
        return "#722ed1"
    return "#5b1a1a"


def _aqi_label(aqi: Optional[int]) -> str:
    """根据 AQI 数值返回中文等级"""
    if aqi is None:
        return "无数据"
    if aqi <= 50:
        return "优"
    if aqi <= 100:
        return "良"
    if aqi <= 150:
        return "轻度污染"
    if aqi <= 200:
        return "中度污染"
    if aqi <= 300:
        return "重度污染"
    return "严重污染"


def _clothing_advice(temp_min: float, temp_max: float) -> tuple[str, str]:
    """根据温度范围返回着装建议"""
    t = temp_max
    if t <= 0:
        brief = "🧥 极寒，厚羽绒服+围巾手套帽子"
        detail = "气温极低，请穿厚羽绒服、围巾、手套、帽子，做好全面防寒。"
    elif t <= 5:
        brief = "🧥 严寒，厚羽绒服"
        detail = "气温很低，建议穿厚羽绒服或棉衣，注意保暖。"
    elif t <= 10:
        brief = "🧥 寒冷，薄羽绒服/厚大衣"
        detail = "气温较低，薄羽绒服或厚大衣合适，可内搭毛衣。"
    elif t <= 15:
        brief = "🧣 微冷，风衣/夹克/毛衣"
        detail = "微冷天气，风衣、夹克或厚毛衣是不错的选择。"
    elif t <= 20:
        brief = "👔 凉爽，薄外套/卫衣"
        detail = "天气凉爽，薄外套或卫衣即可，早晚注意加衣。"
    elif t <= 25:
        brief = "👕 舒适，长袖/薄衫"
        detail = "温度舒适，长袖衬衫或薄衫刚好，可备一件薄外套。"
    elif t <= 30:
        brief = "👕 炎热，短袖为主"
        detail = "天气较热，短袖为主，注意防晒。"
    else:
        brief = "🩳 酷热，清凉短袖，注意防暑"
        detail = "高温天气，尽量穿清凉短袖，注意防暑降温、多喝水。"

    diff = temp_max - temp_min
    if diff > 10:
        detail += f" 日温差达{diff:.0f}℃，早晚注意加衣。"

    return brief, detail


def _generate_keypoint(
    slots: dict[str, Any],
    target_label: str,
    temp_min: float,
    temp_max: float,
    rain_slots: list[str],
    need_umbrella_morning: bool,
    forecast_keypoint: str = "",
    hourly_description: str = "",
    mode: str = "morning",
) -> str:
    """生成天气预报关键点"""
    points: list[str] = []

    if need_umbrella_morning:
        points.append(f"{target_label}上午有降水，出门请带伞🌂")
    elif rain_slots:
        points.append(f"{target_label}{'、'.join(rain_slots)}有降水，请带伞🌂")

    if temp_max >= 35:
        points.append(f"最高{temp_max:.0f}℃高温，注意防暑🔥")
    elif temp_max >= 30 and not rain_slots:
        points.append(f"最高{temp_max:.0f}℃，注意防晒☀️")
    if temp_min <= 0:
        points.append(f"最低{temp_min:.0f}℃，注意防寒🥶")
    elif temp_min <= 5:
        points.append(f"最低{temp_min:.0f}℃，注意保暖")

    diff = temp_max - temp_min
    if diff > 12:
        points.append(f"温差{diff:.0f}℃，早晚添衣")

    for key, label in [("morning", "上午"), ("afternoon", "下午"), ("night", "晚间")]:
        item = slots.get(key)
        if item:
            try:
                wp = float(item.get("wind_power", 0))
                if wp >= 5:
                    points.append(f"{label}{wp:.0f}级大风，出行注意安全💨")
                    break
            except (ValueError, TypeError):
                pass

    for key, label in [("morning", "上午"), ("afternoon", "下午"), ("night", "晚间")]:
        item = slots.get(key)
        if item:
            sky = item.get("weather", item.get("skycon", ""))
            if any(k in sky for k in ("霾", "雾", "沙尘", "浮尘")):
                points.append(f"{label}{sky}，出行注意防护😷")
                break

    if points:
        return "；".join(points)

    if hourly_description and mode == "morning":
        return hourly_description
    if forecast_keypoint and mode == "morning":
        return forecast_keypoint

    return f"{target_label}天气平稳，适宜出行 🌿"


def _slice_hourly(hourly: list[dict[str, Any]], target_date: str) -> dict[str, Optional[dict[str, Any]]]:
    """从小时预报中提取指定日期的分段聚合数据。"""
    raw_slots: dict[str, list[dict[str, Any]]] = {
        "morning": [],
        "afternoon": [],
        "night": [],
    }

    for item in hourly:
        dt_str = item.get("datetime", "")
        if not dt_str:
            continue
        dt = _parse_beijing_datetime(dt_str)
        if dt is None:
            continue

        if dt.strftime("%Y-%m-%d") != target_date:
            continue

        hour = dt.hour
        if 6 <= hour <= 11:
            raw_slots["morning"].append(item)
        elif 12 <= hour <= 17:
            raw_slots["afternoon"].append(item)
        elif 18 <= hour <= 23:
            raw_slots["night"].append(item)

    result: dict[str, Optional[dict[str, Any]]] = {}
    for key, items in raw_slots.items():
        if not items:
            result[key] = None
            continue

        mid_idx = len(items) // 2
        rep = items[mid_idx]

        temps = [
            float(x["temperature"])
            for x in items
            if x.get("temperature") is not None
        ]
        temp_min = min(temps) if temps else None
        temp_max = max(temps) if temps else None

        max_precip_prob = max(
            (x.get("precip_probability", 0) for x in items),
            default=0,
        )

        has_rain = any(_is_rain(x.get("skycon", x.get("weather", ""))) for x in items)

        result[key] = {
            "datetime": rep.get("datetime", ""),
            "temperature": rep.get("temperature"),
            "temp_min": temp_min,
            "temp_max": temp_max,
            "apparent_temperature": rep.get("apparent_temperature"),
            "weather": rep.get("weather", ""),
            "skycon": rep.get("skycon", ""),
            "wind_direction": rep.get("wind_direction", "—"),
            "wind_power": rep.get("wind_power", "—"),
            "wind_speed": rep.get("wind_speed", 0),
            "humidity": rep.get("humidity"),
            "precipitation": rep.get("precipitation", 0),
            "precip_probability": max_precip_prob,
            "has_rain": has_rain,
            "hour_count": len(items),
        }

    return result


def generate_html(weather: dict[str, Any], mode: str = "evening") -> tuple[str, str]:
    """
    生成优化的 HTML 邮件正文和邮件主题。
    
    Args:
        weather: 天气数据字典
        mode: "morning" / "evening"
    
    Returns:
        (subject, html_body)
    """
    live = weather.get("live") or {}
    city = live.get("city", weather.get("city", "未知"))
    source = weather.get("source", "unknown")
    forecast_keypoint = weather.get("forecast_keypoint", "")
    hourly_description = weather.get("hourly_description", "")
    now = _beijing_now()
    today_str = now.strftime("%Y-%m-%d")
    tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    if mode == "morning":
        target_date = today_str
        target_label = "今天"
        mode_title = "今日天气预报"
    else:
        target_date = tomorrow_str
        target_label = "明天"
        mode_title = "明日天气预报"

    hourly = weather.get("hourly_forecast", [])
    slots = _slice_hourly(hourly, target_date)

    need_umbrella_morning = False
    morning_item = slots.get("morning")
    if morning_item:
        need_umbrella_morning = morning_item.get("has_rain", False)

    rain_slots: list[str] = []
    for key, label in [("morning", "上午"), ("afternoon", "下午"), ("night", "晚间")]:
        item = slots.get(key)
        if item and item.get("has_rain"):
            rain_slots.append(label)

    any_rain = len(rain_slots) > 0 or need_umbrella_morning

    temps: list[float] = []
    for key in ["morning", "afternoon", "night"]:
        item = slots.get(key)
        if item:
            for t_key in ("temp_min", "temp_max", "temperature"):
                val = item.get(t_key)
                if val is not None:
                    try:
                        temps.append(float(val))
                    except (ValueError, TypeError):
                        pass

    forecast = weather.get("forecast") or {}
    target_cast: Optional[dict] = None
    if forecast.get("casts"):
        for cast in forecast["casts"]:
            if cast.get("date", "").startswith(target_date):
                target_cast = cast
                for t_key in ("day_temp", "night_temp", "temp_08h_20h_max",
                              "temp_08h_20h_min", "temp_20h_32h_max", "temp_20h_32h_min"):
                    val = cast.get(t_key)
                    if val is not None:
                        try:
                            temps.append(float(val))
                        except (ValueError, TypeError):
                            pass
                break

    if temps:
        temp_min, temp_max = min(temps), max(temps)
    else:
        try:
            temp_max = float(live.get("temperature", 20))
            temp_min = temp_max - 5
        except (ValueError, TypeError):
            temp_max, temp_min = 20, 15

    clothing_brief, clothing_detail = _clothing_advice(temp_min, temp_max)

    keypoint = _generate_keypoint(
        slots, target_label, temp_min, temp_max,
        rain_slots, need_umbrella_morning,
        forecast_keypoint=forecast_keypoint,
        hourly_description=hourly_description,
        mode=mode,
    )

    subject_temp_min, subject_temp_max = temp_min, temp_max
    if target_cast:
        dt = target_cast.get("day_temp")
        nt = target_cast.get("night_temp")
        if dt is not None and nt is not None:
            try:
                subject_temp_min, subject_temp_max = float(nt), float(dt)
            except (ValueError, TypeError):
                pass

    primary_sky = ""
    for key in ["morning", "afternoon", "night"]:
        item = slots.get(key)
        if item:
            primary_sky = item.get("skycon", item.get("weather", ""))
            break
    if not primary_sky and live:
        primary_sky = live.get("skycon", live.get("weather", ""))
    weather_emoji = _sky_icon(primary_sky) if primary_sky else ""

    alert_tags: list[str] = []
    if any_rain:
        alert_tags.append("🌂带伞")
    if temp_max >= 35:
        alert_tags.append("🔥防暑")
    elif temp_max >= 30:
        alert_tags.append("☀️防晒")
    if temp_min <= 0:
        alert_tags.append("🥶防寒")

    for key in ["morning", "afternoon", "night"]:
        item = slots.get(key)
        if item:
            try:
                wp = float(item.get("wind_power", 0))
                if wp >= 5:
                    alert_tags.append("💨大风")
                    break
            except (ValueError, TypeError):
                pass

    alert_str = " ".join(alert_tags)
    subject_parts = [f"{weather_emoji}{subject_temp_min:.0f}~{subject_temp_max:.0f}℃"]
    if alert_str:
        subject_parts.append(alert_str)
    subject = " · ".join(subject_parts)

    # ---- Hero 数据 ----
    target_skycon = ""
    hero_morning = slots.get("morning")
    if hero_morning:
        hero_icon = _sky_icon(hero_morning.get("skycon", hero_morning.get("weather", "")))
        hero_weather = hero_morning.get("weather", "")
        hero_humidity = hero_morning.get("humidity")
    else:
        hero_icon = _sky_icon(target_skycon) if target_skycon else "🌤️"
        hero_weather = target_cast.get("day_weather", "") if target_cast else ""
        hero_humidity = None

    theme = _get_weather_theme(slots, any_rain, temp_max, target_cast=target_cast, hero_weather=hero_weather)
    accent_color = theme["primary"]
    accent_bg = theme["bg"]
    accent_gradient = theme["gradient"]
    text_color = theme.get("text", "#1f2937")

    if target_cast:
        target_skycon = target_cast.get("skycon", "")
        target_day_temp = target_cast.get("day_temp", "?")
        target_night_temp = target_cast.get("night_temp", "?")
        sunrise = target_cast.get("sunrise", "")
        sunset = target_cast.get("sunset", "")
    else:
        target_skycon = ""
        target_day_temp = "?"
        target_night_temp = "?"
        sunrise = ""
        sunset = ""

    live_weather = live.get("weather", "")

    def _fmt_temp(val) -> str:
        if val is None or val == "N/A":
            return "?"
        try:
            return f"{float(val):.0f}"
        except (ValueError, TypeError):
            return "?"

    hero_day_str = _fmt_temp(target_day_temp)
    hero_night_str = _fmt_temp(target_night_temp)

    hero_humidity_str = ""
    if hero_humidity is not None and hero_humidity not in ("N/A", ""):
        try:
            hero_humidity_str = f'<span class="hero-tag">💧 湿度 {int(float(hero_humidity))}%</span>'
        except (ValueError, TypeError):
            pass

    hero_sun_str = ""
    if sunrise and sunset:
        hero_sun_str = f'<span class="hero-tag">🌅 {sunrise} | 🌇 {sunset}</span>'

    hero_live_temp = ""
    if mode == "morning" and live.get("temperature") is not None:
        try:
            hero_live_temp = f'<span class="hero-tag">🌡️ 实况 {float(live["temperature"]):.1f}℃</span>'
        except (ValueError, TypeError):
            pass

    # ---- 空气质量 ----
    aqi_html = ""
    if mode == "morning":
        aqi_val = live.get("aqi")
        pm25_val = live.get("pm25")
        air_desc = live.get("air_desc", "")
        pm10_val = live.get("pm10")
        o3_val = live.get("o3")

        if aqi_val is not None:
            aqi_color = _aqi_color(aqi_val)
            aqi_label = _aqi_label(aqi_val)
            parts = [f'<span class="aqi-main" style="color:{aqi_color}">AQI {int(aqi_val)} {aqi_label}</span>']
            if pm25_val is not None:
                parts.append(f"PM2.5 {int(pm25_val)}")
            if pm10_val is not None:
                parts.append(f"PM10 {int(pm10_val)}")
            if o3_val is not None:
                parts.append(f"O₃ {int(o3_val)}")
            aqi_html = f'<div class="info-section"><div class="info-label">🍃 空气质量</div><div class="info-content">{" &nbsp;·&nbsp; ".join(parts)}</div></div>'
    else:
        daily_aqi = weather.get("daily_aqi")
        if daily_aqi:
            aqi_list = daily_aqi.get("aqi", [])
            pm25_list = daily_aqi.get("pm25", [])
            if target_cast and forecast.get("casts"):
                target_idx = None
                for idx, cast in enumerate(forecast["casts"]):
                    if cast.get("date", "").startswith(target_date):
                        target_idx = idx
                        break
                if target_idx is not None and target_idx < len(aqi_list):
                    aqi_info = aqi_list[target_idx].get("avg", {})
                    aqi_val = aqi_info.get("chn")
                    pm25_avg = None
                    if target_idx < len(pm25_list):
                        pm25_avg = pm25_list[target_idx].get("avg")

                    if aqi_val is not None:
                        aqi_color = _aqi_color(aqi_val)
                        aqi_label = _aqi_label(aqi_val)
                        parts = [f'<span class="aqi-main" style="color:{aqi_color}">AQI {int(aqi_val)} {aqi_label}</span>']
                        if pm25_avg is not None:
                            parts.append(f"PM2.5 {int(pm25_avg)}")
                        aqi_html = f'<div class="info-section"><div class="info-label">🍃 预计空气质量</div><div class="info-content">{" &nbsp;·&nbsp; ".join(parts)}</div></div>'

    # ---- 实况次要信息 ----
    live_extras = ""
    if mode == "morning":
        extras_items: list[str] = []
        vis = live.get("visibility")
        pres = live.get("pressure")
        cloud = live.get("cloudrate")
        precip_int = live.get("precip_intensity")

        if vis is not None and vis not in ("N/A", ""):
            extras_items.append(f"👁️ 能见度 {vis} km")
        if pres is not None and pres not in ("N/A", ""):
            extras_items.append(f"📊 气压 {pres} hPa")
        if cloud is not None and cloud not in ("N/A", ""):
            extras_items.append(f"☁️ 云量 {cloud}%")
        if precip_int is not None and float(precip_int) > 0:
            extras_items.append(f"🌧️ 降水强度 {float(precip_int):.2f} mm/h")

        if extras_items:
            live_extras = f'<div class="info-row">{" &nbsp;|&nbsp; ".join(extras_items)}</div>'

    # ---- 生活指数 ----
    life_items: list[str] = []
    life_tags_html = ""
    if target_cast:
        life_icons = {
            "ultraviolet": "☀️",
            "dressing": "👔",
            "comfort": "😊",
            "coldRisk": "🤧",
            "carWashing": "🚗",
        }
        for key, icon in life_icons.items():
            life_data = target_cast.get(f"life_{key}")
            if life_data:
                desc = life_data.get("desc", "")
                if desc:
                    life_items.append(f'<span class="life-tag">{icon} {desc}</span>')
        if life_items:
            life_tags_html = ''.join(life_items)

    # ---- 卡片渲染 ----
    def _slot_html(item: Optional[dict], label: str, is_highlight: bool = False) -> str:
        """渲染单个时段卡片（优化版：更好的间距和可读性）"""
        if not item:
            return f"""
        <td class="card" style="opacity:.4; text-align:center; vertical-align:middle;">
            <div class="card-label">{label}</div>
            <div class="card-main">
                <span class="empty-temp">暂无数据</span>
            </div>
        </td>"""

        sky = item.get("skycon", item.get("weather", ""))
        icon = _sky_icon(sky)
        temp = item.get("temperature")
        t_min = item.get("temp_min")
        t_max = item.get("temp_max")
        wd = item.get("wind_direction", "—")
        wp = item.get("wind_power", "—")
        humid = item.get("humidity")
        precip_prob = item.get("precip_probability", 0)
        is_rain_slot = item.get("has_rain", False)

        if t_min is not None and t_max is not None and abs(t_max - t_min) >= 1:
            temp_str = f"{float(t_min):.0f}~{float(t_max):.0f}°"
        elif temp is not None:
            temp_str = f"{float(temp):.0f}°"
        else:
            temp_str = "?°"

        precip_html = ""
        if precip_prob and float(precip_prob) > 0:
            precip_html = f'<div class="slot-precip">🌧️ {int(float(precip_prob))}%</div>'

        humid_html = ""
        if humid is not None and humid not in ("N/A", "", None):
            try:
                humid_html = f'<span>💧{int(float(humid))}%</span>'
            except (ValueError, TypeError):
                pass

        rainy_class = " rainy" if is_rain_slot else ""
        highlight_class = " highlight" if is_highlight else ""

        return f"""
        <td class="card{rainy_class}{highlight_class}">
            <div class="card-label">{label}</div>
            {precip_html}
            <div class="card-main">
                <span class="big-icon">{icon}</span>
                <span class="big-temp">{temp_str}</span>
            </div>
            <div class="card-sub">{wd} {wp}级 {humid_html}</div>
        </td>"""

    # ======================== 组装优化的 HTML ========================
    html = f"""<!DOCTYPE html>
<html lang="zh-CN" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<!--[if mso]>
<xml>
  <o:OfficeDocumentSettings>
    <o:PixelsPerInch>96</o:PixelsPerInch>
  </o:OfficeDocumentSettings>
</xml>
<![endif]-->
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
<title>{mode_title} - {city}</title>
<style>
  /* 
   * 优化说明：
   * 1. 移除 Google Fonts 依赖，使用系统字体栈
   * 2. 添加媒体查询实现移动端适配
   * 3. 增强对比度符合 WCAG AA 标准
   * 4. 优化卡片间距和视觉层次
   * 5. 添加 MSO 条件注释支持 Outlook
   */
  
  /* 系统字体栈 - 邮件客户端友好 */
  @font-face {{
    font-family: 'Inter';
    font-style: normal;
    font-weight: 400;
    src: local('Inter'), local('Segoe UI'), local('PingFang SC'), local('Microsoft YaHei');
  }}
  
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 
               'Hiragino Sans GB', 'Microsoft YaHei', 'Inter', sans-serif;
    background: #F5F7FA;
    color: {text_color};
    min-height: 100vh; 
    padding: 20px;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    line-height: 1.6;
  }}
  
  .wrap {{
    max-width: 600px; 
    margin: 0 auto; 
    background: #fff;
    -webkit-border-radius: 16px;
    border-radius: 16px; 
    overflow: hidden;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
  }}

  /* 顶栏 - 优化渐变支持 */
  .topbar {{
    background: {accent_color};
    background: -webkit-linear-gradient(135deg, {accent_color} 0%, {accent_gradient} 100%);
    background: linear-gradient(135deg, {accent_color} 0%, {accent_gradient} 100%);
    color: #fff; 
    padding: 20px 24px;
    display: flex; 
    align-items: center; 
    justify-content: space-between;
  }}
  .topbar-title {{ 
    font-size: 18px; 
    font-weight: 700; 
    letter-spacing: 0.5px; 
    line-height: 1.3; 
  }}
  .topbar-right {{ 
    font-size: 14px; 
    opacity: .95; 
    text-align: right; 
    line-height: 1.5; 
  }}
  .topbar-date {{ display: block; }}
  .topbar-city {{ 
    display: block; 
    opacity: .82; 
    font-size: 13px; 
    margin-top: 2px; 
  }}

  /* Hero 概览 - 增强视觉冲击 */
  .hero {{
    padding: 32px 24px 24px; 
    margin: 0;
    background: {accent_bg};
  }}
  .hero-top {{ 
    display: flex; 
    align-items: center; 
    gap: 24px; 
    margin-bottom: 20px; 
  }}
  .hero-icon {{ 
    font-size: 64px; 
    line-height: 1; 
    flex-shrink: 0; 
  }}
  .hero-info {{ flex: 1; }}
  .hero-temp {{ 
    font-size: 56px; 
    font-weight: 700; 
    color: {accent_color}; 
    line-height: 1.1; 
    letter-spacing: -1px; 
  }}
  .hero-temp .night {{ 
    color: {accent_color}CC; 
    font-weight: 400; 
    font-size: 32px; 
  }}
  .hero-temp .sep {{ 
    color: {accent_color}88; 
    font-weight: 300; 
    margin: 0 4px; 
  }}
  .hero-weather {{ 
    font-size: 16px; 
    color: {text_color}; 
    margin-top: 8px; 
    letter-spacing: 0.3px; 
    font-weight: 500; 
  }}
  .hero-tags {{ 
    display: flex; 
    flex-wrap: wrap; 
    gap: 10px; 
    margin-top: 16px; 
  }}
  .hero-tag {{
    display: inline-block; 
    font-size: 14px; 
    color: {accent_color};
    background: #fff; 
    padding: 6px 14px; 
    -webkit-border-radius: 20px;
    border-radius: 20px;
    line-height: 1.4;
    font-weight: 500;
    border: 1px solid {accent_color}33;
  }}

  /* 关键点 - 增强可读性 */
  .hero-keypoint {{
    margin-top: 20px; 
    padding: 16px;
    background: #fff;
    -webkit-border-radius: 12px;
    border-radius: 12px;
    border-left: 4px solid {accent_color};
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  }}
  .hero-keypoint-text {{ 
    font-size: 14px; 
    color: {text_color}; 
    line-height: 1.7; 
    font-weight: 500;
  }}

  /* 小节标题 */
  .section-label {{
    padding: 24px 24px 12px;
    font-size: 14px; 
    color: {accent_color}; 
    letter-spacing: 1px; 
    font-weight: 700;
    text-transform: uppercase;
    border-top: 1px solid {accent_color}11;
  }}

  /* 分段天气卡片 - 优化网格和间距 */
  .card-container {{ padding: 0 24px 16px; }}
  .card-grid {{ 
    display: table;
    width: 100%;
    border-collapse: separate;
    border-spacing: 16px 0;
  }}
  .card {{
    background: #fff;
    -webkit-border-radius: 14px;
    border-radius: 14px;
    padding: 20px 14px;
    text-align: center;
    border: 1px solid {accent_color}22;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    transition: all .2s ease;
    display: table-cell;
    vertical-align: top;
    width: 33.33%;
    min-height: 60px;  /* 触摸目标 ≥44px */
  }}
  .card.highlight {{ 
    border-color: {accent_color}44; 
    box-shadow: 0 4px 16px rgba(0,0,0,0.1);
    background: {accent_bg};
  }}
  .card-label {{
    font-size: 14px; 
    color: {accent_color}; 
    margin-bottom: 12px;
    letter-spacing: 1.5px; 
    font-weight: 700; 
    text-transform: uppercase;
  }}
  .slot-precip {{
    background: {accent_color}11; 
    color: {accent_color}; 
    -webkit-border-radius: 10px;
    border-radius: 10px;
    font-size: 12px; 
    padding: 4px 10px; 
    margin-bottom: 8px;
    display: inline-block; 
    font-weight: 600; 
  }}
  .card-main {{ 
    display: flex; 
    flex-direction: column; 
    align-items: center; 
    gap: 8px; 
  }}
  .big-icon {{ 
    font-size: 32px; 
    line-height: 1.1; 
  }}
  .big-temp {{ 
    font-size: 24px; 
    font-weight: 700; 
    color: {text_color}; 
    line-height: 1.1; 
  }}
  .card-sub {{ 
    font-size: 13px; 
    color: #6B7280; 
    margin-top: 10px; 
    line-height: 1.5; 
  }}

  /* 信息区域 */
  .info-section {{
    padding: 16px 24px;
  }}
  .info-row {{ 
    padding: 8px 24px; 
    font-size: 13px; 
    color: #6B7280; 
    line-height: 1.6; 
  }}
  .info-label {{ 
    font-size: 14px; 
    color: {accent_color}; 
    margin-bottom: 8px; 
    letter-spacing: 0.5px; 
    font-weight: 700; 
  }}
  .info-content {{ 
    font-size: 14px; 
    color: {text_color}; 
    line-height: 1.6; 
  }}
  .aqi-main {{ font-weight: 700; }}

  /* 生活指数 */
  .life-grid {{ display: flex; flex-wrap: wrap; gap: 12px; }}
  .life-tag {{
    display: inline-block; 
    font-size: 14px; 
    color: {accent_color};
    background: {accent_bg}; 
    padding: 8px 16px; 
    -webkit-border-radius: 20px;
    border-radius: 20px; 
    line-height: 1.4;
    border: 1px solid {accent_color}22;
  }}

  /* 着装建议 - 优化视觉层次 */
  .clothing {{
    background: #fff;
    -webkit-border-radius: 12px;
    border-radius: 12px;
    padding: 16px; 
    margin-top: 12px; 
    border: 1px solid {accent_color}22;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  }}
  .clothing-brief {{ 
    font-size: 14px; 
    color: {accent_color}; 
    line-height: 1.6; 
    font-weight: 700; 
  }}
  .clothing-detail {{ 
    font-size: 13px; 
    color: #6B7280; 
    margin-top: 6px; 
    line-height: 1.7; 
  }}

  /* 底部 */
  .footer {{
    text-align: center; 
    padding: 20px 24px;
    font-size: 14px; 
    color: #9CA3AF; 
    line-height: 1.6; 
    border-top: 1px solid #E5E7EB;
  }}

  /* ============================================
   * 响应式设计 - 移动端优化
   * ============================================ */
  /* 大屏手机 / 小平板（如 iPhone 14 Pro Max） */
  @media screen and (max-width: 480px) {{
    body {{
      padding: 10px;
    }}
    
    .wrap {{
      -webkit-border-radius: 12px;
    border-radius: 12px;
    }}
    
    .topbar {{
      padding: 16px 20px;
      flex-direction: column;
      align-items: flex-start;
      gap: 8px;
    }}
    .topbar-title {{
      font-size: 16px;
    }}
    .topbar-right {{
      text-align: left;
      font-size: 13px;
    }}
    
    .hero {{
      padding: 24px 20px 20px;
    }}
    .hero-top {{
      flex-direction: column;
      align-items: flex-start;
      gap: 16px;
    }}
    .hero-icon {{
      font-size: 48px;
    }}
    .hero-temp {{
      font-size: 42px;
    }}
    .hero-temp .night {{
      font-size: 24px;
    }}
    .hero-weather {{
      font-size: 15px;
    }}
    .hero-tag {{
      font-size: 12px;
      padding: 5px 12px;
    }}
    
    .section-label {{
      padding: 20px 20px 10px;
      font-size: 12px;
    }}
    
    /* 卡片堆叠为单列 - table 布局移动端适配 */
    .card-container {{
      padding: 0 20px 12px;
    }}
    .card-grid {{
      display: block;
      width: 100%;
    }}
    .card-grid tr {{
      display: block;
      margin-bottom: 12px;
    }}
    .card {{
      display: block;
      width: 100%;
      padding: 16px 14px;
      text-align: left;
      margin-bottom: 12px;
    }}
    .card-label {{
      margin-bottom: 0;
      min-width: 60px;
      font-size: 13px;
      display: inline-block;
    }}
    .card-main {{
      display: inline-flex;
      flex-direction: row;
      align-items: center;
      gap: 12px;
    }}
    .big-icon {{
      font-size: 28px;
    }}
    .big-temp {{
      font-size: 20px;
    }}
    .card-sub {{
      margin-top: 4px;
      font-size: 12px;
    }}
    .slot-precip {{
      display: inline-block;
      margin-left: 8px;
    }}
    
    .info-section {{
      padding: 12px 20px;
    }}
    .info-row {{
      padding: 6px 20px;
      font-size: 12px;
    }}
    
    .life-grid {{
      gap: 8px;
    }}
    .life-tag {{
      font-size: 12px;
      padding: 6px 12px;
    }}
    
    .clothing {{
      padding: 14px;
    }}
    
    .footer {{
      padding: 16px 20px;
      font-size: 11px;
    }}
  }}
  
  /* 目标设备基准：iPhone 14/15/16 */
  @media screen and (max-width: 414px) {{
    .hero-temp {{
      font-size: 48px;
    }}
    .hero-icon {{
      font-size: 56px;
    }}
    .card {{
      padding: 18px 14px;
    }}
    .card-label {{
      font-size: 13px;
    }}
  }}

  /* 小屏幕手机进一步优化 */
  @media screen and (max-width: 375px) {{
    .hero-temp {{
      font-size: 36px;
    }}
    .hero-temp .night {{
      font-size: 20px;
    }}
    .card {{
      padding: 14px 12px;
    }}
    .big-temp {{
      font-size: 18px;
    }}
  }}
  
  /* 打印样式 */
  @media print {{
    body {{
      background: #fff;
      padding: 0;
    }}
    .wrap {{
      box-shadow: none;
      max-width: 100%;
    }}
  }}
</style>
<!--[if mso]>
<style>
  /* Outlook 专用样式 */
  .card-grid {{
    display: block;
  }}
  .card {{
    width: 32%;
    display: inline-block;
    vertical-align: top;
    margin-right: 1%;
  }}
  .topbar {{
    background: {accent_color} !important;
  }}
</style>
<![endif]-->
</head>
<body>
<div class="wrap" role="main" aria-label="天气预报邮件">
  <!-- 顶栏 -->
  <div class="topbar" role="banner">
    <span class="topbar-title">{mode_title}</span>
    <span class="topbar-right">
      <span class="topbar-date">{target_date}</span>
      <span class="topbar-city">{city}</span>
    </span>
  </div>

  <!-- Hero 概览 -->
  <div class="hero" role="region" aria-label="天气概览">
    <div class="hero-top">
      <span class="hero-icon" role="img" aria-label="天气图标">{hero_icon}</span>
      <div class="hero-info">
        <div class="hero-temp">
          <span class="night">{hero_night_str}°</span>
          <span class="sep"> ~ </span>
          {hero_day_str}°
        </div>
        <div class="hero-weather">{hero_weather}</div>
      </div>
    </div>
    <div class="hero-tags">
      {hero_humidity_str}
      {hero_sun_str}
      {hero_live_temp}
    </div>
    <div class="hero-keypoint" role="alert" aria-label="关键天气提示">
      <div class="hero-keypoint-text">{keypoint}</div>
    </div>
  </div>

  <!-- 分时段预报 -->
  <div class="section-label" role="heading" aria-level="2">⏰ 分时段预报</div>
  <div class="card-container">
    <table class="card-grid" width="100%" cellpadding="0" cellspacing="16" border="0" role="list">
      <tr role="listitem">
        {_slot_html(slots.get("morning"), '\u4E0A\u5348', is_highlight=(mode == "morning"))}
        {_slot_html(slots.get("afternoon"), '\u4E0B\u5348')}
        {_slot_html(slots.get("night"), '\u665A\u95F4')}
      </tr>
    </table>
  </div>

  <!-- 空气质量 -->
  {aqi_html}

  <!-- 实况次要信息 -->
  {live_extras}

  <!-- 生活指数 & 着装建议 -->
  <div class="info-section" role="region" aria-label="生活建议">
    <div class="info-label">📋 生活指数</div>
    <div class="life-grid">{life_tags_html}</div>
    <div class="clothing">
      <div class="clothing-brief">{clothing_brief}</div>
      <div class="clothing-detail">{clothing_detail}（{temp_min:.0f}~{temp_max:.0f}℃）</div>
    </div>
  </div>

  <!-- 底部 -->
  <div class="footer" role="contentinfo">
    由 Weather-Email 自动推送 &nbsp;·&nbsp; {source.upper() if source else "API"}<br>
    {now.strftime('%Y-%m-%d %H:%M')}
  </div>
</div>
</body>
</html>"""

    return subject, html
