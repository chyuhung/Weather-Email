"""
天气邮件 HTML 生成器
- 支持早晚两种推送模式（morning / evening）
- morning：推送今天（今日概览 + 关键点 + 三时段 + 生活指数 + 着装建议）
- evening：推送明天（明日概览 + 关键点 + 三时段 + 生活指数 + 着装建议）
- 小时预报按时段聚合（取中间小时为代表值，温度显示区间）
- 生活指数区域展示紫外线、穿衣、舒适度、感冒风险、洗车建议
- 统一、自然的大气配色方案
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
BEIJING_TZ = timezone(timedelta(hours=8))


COLOR_THEME = {
    "sunny": {"primary": "#4A90D9", "bg": "#EEF6FF", "gradient": "#4A90D9"},
    "rainy": {"primary": "#5B7BA3", "bg": "#EDF1F7", "gradient": "#6B8299"},
    "cloudy": {"primary": "#7C8DA5", "bg": "#F3F4F6", "gradient": "#8E9DAD"},
    "extreme": {"primary": "#E8745C", "bg": "#FEF0ED", "gradient": "#E8745C"},
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


def _get_weather_theme(slots: dict, any_rain: bool, temp_max: float) -> dict:
    """根据天气状况智能选择配色主题"""
    if any_rain:
        return COLOR_THEME["rainy"]
    if temp_max >= 35:
        return COLOR_THEME["extreme"]
    for key in ["morning", "afternoon", "night"]:
        item = slots.get(key)
        if item:
            sky = item.get("skycon", item.get("weather", "")).upper()
            if "CLOUD" in sky or "OVERCAST" in sky:
                return COLOR_THEME["cloudy"]
    return COLOR_THEME["sunny"]


# ================================================================
#  天气图标 & 辅助函数
# ================================================================

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

    # 高德中文天气文字兜底
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
    """
    判断天气是否需要带伞（雨系、雪系、雨夹雪等）。
    晴/霾/雾/沙尘/阴等返回 False。
    """
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
        return "#52c41a"   # 优 - 绿
    if aqi <= 100:
        return "#faad14"   # 良 - 黄
    if aqi <= 150:
        return "#fa8c16"   # 轻度污染 - 橙
    if aqi <= 200:
        return "#f5222d"   # 中度污染 - 红
    if aqi <= 300:
        return "#722ed1"   # 重度污染 - 紫
    return "#5b1a1a"       # 严重污染 - 深红


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


# ================================================================
#  着装建议
# ================================================================

def _clothing_advice(temp_min: float, temp_max: float) -> tuple[str, str]:
    """根据温度范围返回着装建议 (简短建议, 详细说明)"""
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


# ================================================================
#  天气关键点生成
# ================================================================

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
    """
    生成天气预报关键点——突出最重要的天气信息。
    优先级：降水 > 极端温度 > 大温差 > 大风 > 雾霾 > 平稳天气
    如果没有显著天气事件，则使用 API 提供的 forecast_keypoint 或 hourly_description。
    """
    points: list[str] = []

    # 1. 降水/带伞（最高优先级）
    if need_umbrella_morning:
        points.append(f"{target_label}上午有降水，出门请带伞🌂")
    elif rain_slots:
        points.append(f"{target_label}{'、'.join(rain_slots)}有降水，请带伞🌂")

    # 2. 极端温度
    if temp_max >= 35:
        points.append(f"最高{temp_max:.0f}℃高温，注意防暑🔥")
    elif temp_max >= 30 and not rain_slots:
        points.append(f"最高{temp_max:.0f}℃，注意防晒☀️")
    if temp_min <= 0:
        points.append(f"最低{temp_min:.0f}℃，注意防寒🥶")
    elif temp_min <= 5:
        points.append(f"最低{temp_min:.0f}℃，注意保暖")

    # 3. 大温差
    diff = temp_max - temp_min
    if diff > 12:
        points.append(f"温差{diff:.0f}℃，早晚添衣")

    # 4. 大风
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

    # 5. 雾霾沙尘
    for key, label in [("morning", "上午"), ("afternoon", "下午"), ("night", "晚间")]:
        item = slots.get(key)
        if item:
            sky = item.get("weather", item.get("skycon", ""))
            if any(k in sky for k in ("霾", "雾", "沙尘", "浮尘")):
                points.append(f"{label}{sky}，出行注意防护😷")
                break

    # 有显著天气事件 → 返回我们的关键点
    if points:
        return "；".join(points)

    # 无显著事件：优先使用 hourly_description（更详细），其次 forecast_keypoint
    if hourly_description and mode == "morning":
        return hourly_description
    if forecast_keypoint and mode == "morning":
        return forecast_keypoint

    return f"{target_label}天气平稳，适宜出行 🌿"


# ================================================================
#  小时预报分片聚合
# ================================================================

def _slice_hourly(hourly: list[dict[str, Any]], target_date: str) -> dict[str, Optional[dict[str, Any]]]:
    """
    从小时预报中提取指定日期的分段聚合数据。

    每个时段（上午/下午/晚间）取该时段所有小时数据的聚合：
    - 天气状况：取中间时刻的代表值
    - 温度：显示该时段的最低~最高
    - 降水概率：取该时段最大值
    - 湿度：取中间时刻的代表值
    - 风向/风力：取中间时刻的代表值

    Returns:
        {"morning": {...}, "afternoon": {...}, "night": {...}}
    """
    raw_slots: dict[str, list[dict[str, Any]]] = {
        "morning": [],     # 06:00 ~ 11:00
        "afternoon": [],   # 12:00 ~ 17:00
        "night": [],       # 18:00 ~ 23:00
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

    # 聚合每个时段
    result: dict[str, Optional[dict[str, Any]]] = {}
    for key, items in raw_slots.items():
        if not items:
            result[key] = None
            continue

        # 取中间时刻作为代表值
        mid_idx = len(items) // 2
        rep = items[mid_idx]

        # 温度区间
        temps = [
            float(x["temperature"])
            for x in items
            if x.get("temperature") is not None
        ]
        temp_min = min(temps) if temps else None
        temp_max = max(temps) if temps else None

        # 最大降水概率
        max_precip_prob = max(
            (x.get("precip_probability", 0) for x in items),
            default=0,
        )

        # 是否有降水时段
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


# ================================================================
#  主生成函数
# ================================================================

def generate_html(weather: dict[str, Any], mode: str = "evening") -> tuple[str, str]:
    """
    生成 HTML 邮件正文和邮件主题。

    Args:
        weather: 天气数据字典（由 weather_api 返回）
        mode: "morning"（早间推送，显示今天）/ "evening"（晚间推送，显示明天）

    Returns:
        (subject, html_body) 邮件主题和 HTML 正文
    """
    live = weather.get("live") or {}
    city = live.get("city", weather.get("city", "未知"))
    source = weather.get("source", "unknown")
    forecast_keypoint = weather.get("forecast_keypoint", "")
    hourly_description = weather.get("hourly_description", "")
    now = _beijing_now()
    today_str = now.strftime("%Y-%m-%d")
    tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    # ---- 根据 mode 决定目标日期 ----
    if mode == "morning":
        target_date = today_str
        target_label = "今天"
        mode_title = "今日天气预报"
    else:
        target_date = tomorrow_str
        target_label = "明天"
        mode_title = "明日天气预报"

    # ---- 提取分段小时数据（聚合后）----
    hourly = weather.get("hourly_forecast", [])
    slots = _slice_hourly(hourly, target_date)

    # ---- 带伞判断 ----
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

    # ---- 温度数据计算 ----
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

    # 从每日预报补充温度范围
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

    # ---- 着装建议 ----
    clothing_brief, clothing_detail = _clothing_advice(temp_min, temp_max)

    # ---- 天气关键点 ----
    keypoint = _generate_keypoint(
        slots, target_label, temp_min, temp_max,
        rain_slots, need_umbrella_morning,
        forecast_keypoint=forecast_keypoint,
        hourly_description=hourly_description,
        mode=mode,
    )

    # ---- 邮件主题 ----
    # 温度范围使用每日预报的 day_temp/night_temp，与 Hero 大卡片保持一致
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

    # ======================== HTML 正文 ========================

    # 获取智能配色主题
    theme = _get_weather_theme(slots, any_rain, temp_max)
    accent_color = theme["primary"]
    accent_bg = theme["bg"]

    # ---- Hero 卡片数据 ----
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

    # 取上午小时数据作为 hero 天气描述
    hero_morning = slots.get("morning")
    if hero_morning:
        hero_icon = _sky_icon(hero_morning.get("skycon", hero_morning.get("weather", "")))
        hero_weather = hero_morning.get("weather", "")
        hero_humidity = hero_morning.get("humidity")
    else:
        hero_icon = _sky_icon(target_skycon) if target_skycon else "🌤️"
        hero_weather = target_cast.get("day_weather", "") if target_cast else ""
        hero_humidity = None

    # 实况天气描述（仅早间模式用于 hero）
    live_weather = live.get("weather", "")

    # 温度显示
    def _fmt_temp(val) -> str:
        if val is None or val == "N/A":
            return "?"
        try:
            return f"{float(val):.0f}"
        except (ValueError, TypeError):
            return "?"

    hero_day_str = _fmt_temp(target_day_temp)
    hero_night_str = _fmt_temp(target_night_temp)

    # Hero 湿度
    hero_humidity_str = ""
    if hero_humidity is not None and hero_humidity not in ("N/A", ""):
        try:
            hero_humidity_str = f'<span class="hero-tag">💧 湿度 {int(float(hero_humidity))}%</span>'
        except (ValueError, TypeError):
            pass

    # Hero 日出日落
    hero_sun_str = ""
    if sunrise and sunset:
        hero_sun_str = f'<span class="hero-tag">🌅 {sunrise} | 🌇 {sunset}</span>'

    # Hero 实况温度（仅早间模式）
    hero_live_temp = ""
    if mode == "morning" and live.get("temperature") is not None:
        try:
            hero_live_temp = f'<span class="hero-tag">🌡️ 实况 {float(live["temperature"]):.1f}℃</span>'
        except (ValueError, TypeError):
            pass

    # ---- 空气质量（早间用实况，晚间用每日预报）----
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
        # 晚间模式：从每日预报取明天的 AQI
        daily_aqi = weather.get("daily_aqi")
        if daily_aqi:
            aqi_list = daily_aqi.get("aqi", [])
            pm25_list = daily_aqi.get("pm25", [])
            # 取第二条（明天的数据，因为第一条是今天）
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

    # ---- 实况次要信息（仅早间模式）----
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

    # ---- 卡片渲染函数 ----
    def _slot_html(item: Optional[dict], label: str, is_highlight: bool = False) -> str:
        """渲染单个时段卡片，支持温度区间和降水概率显示"""
        if not item:
            return f"""
        <div class="card" style="opacity:.4">
            <div class="card-label">{label}</div>
            <div class="card-main">
                <span class="empty-temp">暂无数据</span>
            </div>
        </div>"""

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

        # 温度显示：如果有区间则显示 min~max，否则显示单值
        if t_min is not None and t_max is not None and abs(t_max - t_min) >= 1:
            temp_str = f"{float(t_min):.0f}~{float(t_max):.0f}°"
        elif temp is not None:
            temp_str = f"{float(temp):.0f}°"
        else:
            temp_str = "?°"

        # 降水概率
        precip_html = ""
        if precip_prob and float(precip_prob) > 0:
            precip_html = f'<div class="slot-precip">🌧️ {int(float(precip_prob))}%</div>'

        # 湿度
        humid_html = ""
        if humid is not None and humid not in ("N/A", "", None):
            try:
                humid_html = f'<span>💧{int(float(humid))}%</span>'
            except (ValueError, TypeError):
                pass

        rainy_class = " rainy" if is_rain_slot else ""
        highlight_class = " highlight" if is_highlight else ""

        return f"""
        <div class="card{rainy_class}{highlight_class}">
            <div class="card-label">{label}</div>
            {precip_html}
            <div class="card-main">
                <span class="big-icon">{icon}</span>
                <span class="big-temp">{temp_str}</span>
            </div>
            <div class="card-sub">{wd} {wp}级 {humid_html}</div>
        </div>"""

    # ======================== 组装 HTML ========================
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{mode_title} - {city}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif;
    background: linear-gradient(180deg, #F0F4FA 0%, #E4ECF5 100%);
    color: #1f2937;
    min-height: 100vh; padding: 20px;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    line-height: 1.5;
  }}
  .wrap {{
    max-width: 500px; margin: 0 auto; background: #fff;
    border-radius: 20px; overflow: hidden;
    box-shadow: 0 8px 32px rgba(99, 130, 175, 0.13);
  }}

  /* ── 顶栏 ── */
  .topbar {{
    background: {accent_color};
    color: #fff; padding: 18px 24px;
    display: flex; align-items: center; justify-content: space-between;
  }}
  .topbar-title {{ font-size: 16px; font-weight: 600; letter-spacing: 1px; line-height: 1.15; }}
  .topbar-right {{ font-size: 12px; opacity: .95; text-align: right; line-height: 1.35; }}
  .topbar-date {{ display: block; letter-spacing: .5px; }}
  .topbar-city {{ display: block; opacity: .78; font-size: 11px; margin-top: 3px; line-height: 1.15; }}

  /* ── Hero 概览卡片 ── */
  .hero {{
    padding: 30px 24px 24px; margin: 0;
  }}
  .hero-top {{ display: flex; align-items: center; gap: 22px; margin-bottom: 16px; }}
  .hero-icon {{ font-size: 58px; line-height: 1; flex-shrink: 0; filter: drop-shadow(0 4px 8px rgba(0,0,0,.08)); }}
  .hero-info {{ flex: 1; }}
  .hero-temp {{ font-size: 40px; font-weight: 700; color: #1f2937; line-height: 1.08; letter-spacing: -.5px; }}
  .hero-temp .night {{ color: #6b7280; font-weight: 500; font-size: 28px; }}
  .hero-temp .sep {{ color: #c0c6d0; font-weight: 300; margin: 0 4px; }}
  .hero-weather {{ font-size: 16px; color: #4b5563; margin-top: 6px; letter-spacing: .5px; line-height: 1.35; }}
  .hero-tags {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 16px; }}
  .hero-tag {{
    display: inline-block; font-size: 12px; color: #556070;
    background: #F5F7FA; padding: 6px 14px; border-radius: 20px;
    line-height: 1.25;
  }}

  /* ── 小节标题 ── */
  .section-label {{
    padding: 20px 24px 10px;
    font-size: 12px; color: #8f98a6; letter-spacing: 1px;
  }}

  /* ── 天气关键点（内嵌 Hero 底部） ── */
  .hero-keypoint {{
    margin-top: 16px; padding: 12px 14px;
    background: #F5F7FA; border-radius: 10px;
  }}
  .hero-keypoint-text {{ font-size: 13px; color: #5f6673; line-height: 1.68; }}

  /* ── 分段天气卡片 ── */
  .card-container {{ padding: 0 24px 10px; }}
  .card-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }}
  .card {{
    background: #F5F7FA; border-radius: 16px;
    padding: 18px 12px; text-align: center;
    border: 1px solid #EAEEF3;
    transition: all .15s ease;
  }}
  .card.highlight {{
    background: {accent_bg};
    border-color: {accent_color}33;
  }}
  .card.rainy {{ background: #F0F2F7; }}
  .card-label {{
    font-size: 11px; color: #8f98a6; margin-bottom: 10px;
    letter-spacing: 2px; font-weight: 600; line-height: 1.2;
  }}
  .slot-precip {{
    background: #fff; color: {accent_color}; border-radius: 12px;
    font-size: 11px; padding: 3px 10px; margin-bottom: 7px;
    display: inline-block; font-weight: 600; line-height: 1.2;
  }}
  .card-main {{ display: flex; flex-direction: column; align-items: center; gap: 6px; }}
  .big-icon {{ font-size: 30px; line-height: 1.08; }}
  .big-temp {{ font-size: 22px; font-weight: 700; color: #1f2937; line-height: 1.1; }}
  .card-sub {{ font-size: 11px; color: #7b8594; margin-top: 8px; line-height: 1.5; }}
  .card-sub span {{ margin: 0 3px; }}

  /* ── 信息区域 ── */
  .info-section {{
    padding: 12px 24px;
  }}
  .aqi-block {{ margin-top: 6px; }}
  .live-extras-block {{ margin-top: 2px; }}
  .info-row {{
    padding: 7px 24px; font-size: 12px; color: #7b8594; line-height: 1.9;
  }}
  .info-label {{
    font-size: 11px; color: #8f98a6; margin-bottom: 9px;
    letter-spacing: 1px; line-height: 1.2;
  }}
  .info-content {{ font-size: 13px; color: #4b5563; line-height: 1.65; }}
  .aqi-main {{ font-weight: 700; }}
  .empty-temp {{ font-size: 13px; color: #9aa3af; line-height: 1.2; }}

  /* ── 生活指数 ── */
  .life-grid {{
    display: flex; flex-wrap: wrap; gap: 10px;
  }}
  .life-tag {{
    display: inline-block; font-size: 12px; color: #556070;
    background: #F5F7FA; padding: 6px 14px; border-radius: 20px;
    line-height: 1.25;
  }}

  /* ── 着装建议 ── */
  .clothing {{
    background: #F5F7FA;
    border-radius: 10px;
    padding: 12px 14px; margin-top: 10px;
  }}
  .clothing-brief {{ font-size: 13px; color: #2f3640; line-height: 1.55; font-weight: 600; }}
  .clothing-detail {{ font-size: 12px; color: #7b8594; margin-top: 4px; line-height: 1.6; }}

  /* ── 底部 ── */
  .footer {{
    text-align: center; padding: 18px 24px 20px;
    font-size: 11px; color: #aab2bf; line-height: 1.6;
  }}
</style>
</head>
<body>
<div class="wrap">
  <!-- 顶栏 -->
  <div class="topbar">
    <span class="topbar-title">{mode_title}</span>
    <span class="topbar-right">
      <span class="topbar-date">{target_date}</span>
      <span class="topbar-city">{city}</span>
    </span>
  </div>

  <!-- Hero 概览 -->
  <div class="hero">
    <div class="hero-top">
      <span class="hero-icon">{hero_icon}</span>
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
    <div class="hero-keypoint">
      <div class="hero-keypoint-text">{keypoint}</div>
    </div>
  </div>

  <!-- 分时段预报 -->
  <div class="section-label">⏰ 分时段预报</div>
  <div class="card-container">
    <div class="card-grid">
      {_slot_html(slots.get("morning"), '\u4E0A\u5348', is_highlight=(mode == "morning"))}
      {_slot_html(slots.get("afternoon"), '\u4E0B\u5348')}
      {_slot_html(slots.get("night"), '\u665A\u95F4')}
    </div>
  </div>

  <!-- 空气质量 -->
  {aqi_html}

  <!-- 实况次要信息 -->
  {live_extras}

  <!-- 生活指数 & 着装建议 -->
  <div class="info-section">
    <div class="info-label">📋 生活指数</div>
    <div class="life-grid">{life_tags_html}</div>
    <div class="clothing">
      <div class="clothing-brief">{clothing_brief}</div>
      <div class="clothing-detail">{clothing_detail}（{temp_min:.0f}~{temp_max:.0f}℃）</div>
    </div>
  </div>

  <!-- 底部 -->
  <div class="footer">
    由 Weather-Email 自动推送 &nbsp;·&nbsp; {source.upper() if source else "API"}<br>
    {now.strftime('%Y-%m-%d %H:%M')}
  </div>
</div>
</body>
</html>"""

    return subject, html
