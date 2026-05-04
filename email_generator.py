"""
天气邮件正文生成器
- 支持早晚两种推送模式（morning / evening）
- morning：推送今天（今日全天概览 + 今天上午/下午/晚间 + 着装建议）
- evening：推送明天（明日全天概览 + 明天上午/下午/晚间 + 着装建议）
"""
from datetime import datetime, timedelta


# ── 天气图标（emoji） ──────────────────────────────────────────────────────────
def _sky_icon(skycon: str) -> str:
    if not skycon:
        return "🌤️"
    # 标准化输入
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

    # 精确匹配
    if skycon in icon_map:
        return icon_map[skycon]
    if normalized in icon_map:
        return icon_map[normalized]

    # 高德中文天气文字兜底
    cjk = {
        "晴": "☀️", "多云": "⛅", "阴": "☁️",
        "小雨": "🌦️", "中雨": "🌧️", "大雨": "🌧️", "暴雨": "⛈️",
        "雷阵雨": "⛈️", "阵雨": "🌦️", "雷雨": "⛈️",
        "雾": "🌫️", "霾": "😷",
        "沙尘": "🌿", "扬沙": "🌿",
        "雨夹雪": "🌨️", "小雪": "🌨️", "中雪": "❄️", "大雪": "❄️",
        "冰雹": "🌨️",
    }
    for k, v in cjk.items():
        if k in skycon:
            return v
    return "🌤️"


def _is_rain(skycon: str) -> bool:
    """判断是否需要带伞（雨系、雪系、雨夹雪）。晴/霾/雾/沙尘等返回 False。"""
    if not skycon:
        return False
    s = skycon.upper().replace("（", "(").replace("）", ")").replace(" ", "")

    # 雨/雷暴相关关键词（精确集合，避免 CLEAR_RAIN / PARTLY_CLOUDY 等误匹配）
    RAIN_KEYWORDS = {
        # 彩云 skycon
        "RAIN", "DRIZZLE", "SHOWERS", "THUNDERSTORM", "STORM",
        "SLEET", "HAIL", "HEAVY_RAIN", "MODERATE_RAIN", "LIGHT_RAIN",
        "STORM_RAIN",
        # 雪系
        "SNOW", "HEAVY_SNOW", "MODERATE_SNOW", "LIGHT_SNOW", "STORM_SNOW",
        # 高德中文天气文字
        "雨", "雪", "雨夹雪", "雷阵雨", "阵雨", "雷雨",
    }
    # 晴/霾/雾/沙尘/风 → 不带伞
    EXCLUDE = {"CLEAR", "HAZE", "FOG", "DUST", "SAND", "WIND", "CLOUDY",
               "晴", "霾", "雾", "沙尘", "阴"}

    # 必须包含雨/雪关键词，且不能是纯霾/晴/阴等
    has_rain = any(k in s for k in RAIN_KEYWORDS)
    has_exclude = any(k in s for k in EXCLUDE)
    # CLOUDY/阴 如果前面没有雨雪词也不算
    if has_exclude and not has_rain:
        return False
    return has_rain


# ── 着装建议 ──────────────────────────────────────────────────────────────────
def _clothing_advice(temp_min: float, temp_max: float) -> tuple[str, str]:
    """
    根据温度范围返回着装建议。
    返回: (简短建议, 详细说明)
    """
    # 用白天的温度（取 max）做主要判断
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

    # 如果温差大（>10℃），补充提醒
    diff = temp_max - temp_min
    if diff > 10:
        detail += f" 日温差达{diff:.0f}℃，早晚注意加衣。"

    return brief, detail


# ── 提取指定日期分段数据 ──────────────────────────────────────────────────────
def _slice_hourly(hourly: list, target_date: str) -> dict:
    """
    从小时预报中提取指定日期的分段数据。
    target_date: 要提取的日期字符串（如 "2026-04-30"）
    返回: { "morning": {...}, "afternoon": {...}, "night": {...} }
    """
    slots = {
        "morning":   None,  # 06~11
        "afternoon": None,  # 12~17
        "night":     None,  # 18~23
    }

    for item in hourly:
        dt_str = item.get("datetime", "")
        try:
            dt = datetime.fromisoformat(dt_str.replace("+08:00", "").replace("Z", ""))
        except Exception:
            continue

        if dt.strftime("%Y-%m-%d") != target_date:
            continue

        hour = dt.hour
        if 6 <= hour <= 11 and slots["morning"] is None:
            slots["morning"] = item
        elif 12 <= hour <= 17 and slots["afternoon"] is None:
            slots["afternoon"] = item
        elif 18 <= hour <= 23 and slots["night"] is None:
            slots["night"] = item

    return slots


# ── 主生成函数 ─────────────────────────────────────────────────────────────────
def generate_html(weather: dict, mode: str = "evening") -> tuple[str, str]:
    """
    生成 HTML 邮件正文和邮件主题。
    mode: "morning"（早间推送）或 "evening"（晚间推送）
    返回: (subject, html_body)
    """
    live = weather.get("live", {}) or {}
    city = live.get("city", weather.get("city", "未知"))
    source = weather.get("source", "unknown")
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    tomorrow = now + timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")

    # ── 根据 mode 决定目标日期 ──────────────────────────────────────────────
    if mode == "morning":
        target_date = today_str
        target_label = "今天"
        mode_title = "今日天气预报"
    else:
        target_date = tomorrow_str
        target_label = "明天"
        mode_title = "明日天气预报"

    # ── 提取分段数据 ────────────────────────────────────────────────────────
    hourly = weather.get("hourly_forecast", [])
    slots = _slice_hourly(hourly, target_date)

    # ── 带伞判断（基于目标日期各时段天气） ────────────────────────────────────
    need_umbrella_morning = False
    morning_item = slots.get("morning")
    if morning_item:
        morning_sky = morning_item.get("weather", morning_item.get("skycon", ""))
        need_umbrella_morning = _is_rain(morning_sky)

    rain_slots = []
    for key, label in [("morning", "上午"), ("afternoon", "下午"), ("night", "晚间")]:
        item = slots.get(key)
        if item and _is_rain(item.get("weather", item.get("skycon", ""))):
            rain_slots.append(label)

    any_rain = len(rain_slots) > 0

    if need_umbrella_morning:
        rain_hint = f"{target_label}上午有雨，出门请带伞"
    elif any_rain:
        rain_hint = f"{target_label}{'、'.join(rain_slots)}有雨，请带伞"
    else:
        rain_hint = ""

    # ── 着装建议 ────────────────────────────────────────────────────────────
    temps = []
    for key in ["morning", "afternoon", "night"]:
        item = slots.get(key)
        if item and item.get("temperature") not in (None, "N/A"):
            try:
                temps.append(float(item["temperature"]))
            except (ValueError, TypeError):
                pass

    # 也尝试从每日预报中获取最高/最低温
    forecast = weather.get("forecast", {})
    target_cast = None
    if forecast and forecast.get("casts"):
        for cast in forecast["casts"]:
            if cast.get("date", "").startswith(target_date):
                target_cast = cast
                try:
                    t_max = float(cast.get("day_temp", 0))
                    t_min = float(cast.get("night_temp", 0))
                    temps.extend([t_max, t_min])
                except (ValueError, TypeError):
                    pass
                break

    if temps:
        temp_min = min(temps)
        temp_max = max(temps)
    else:
        # 退而求其次用实况温度
        try:
            temp_max = float(live.get("temperature", 20))
            temp_min = temp_max - 5
        except (ValueError, TypeError):
            temp_max, temp_min = 20, 15

    clothing_brief, clothing_detail = _clothing_advice(temp_min, temp_max)

    # ── 邮件主题 ────────────────────────────────────────────────────────────
    # 主天气 emoji：取目标日主要天气的图标
    primary_sky = ""
    for key in ["morning", "afternoon", "night"]:
        item = slots.get(key)
        if item:
            primary_sky = item.get("skycon", item.get("weather", ""))
            break
    if not primary_sky and live:
        primary_sky = live.get("skycon", live.get("weather", ""))
    weather_emoji = _sky_icon(primary_sky) if primary_sky else ""

    # 极端天气提示标签
    alert_tags = []
    if any_rain or need_umbrella_morning:
        alert_tags.append("🌂带伞")
    if temp_max >= 35:
        alert_tags.append("🔥防暑")
    elif temp_max >= 30:
        alert_tags.append("☀️防晒")
    if temp_min <= 0:
        alert_tags.append("🥶防寒")
    # 大风检测：任一时段风力 ≥5 级
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
    subject_parts = [f"{weather_emoji}{temp_min:.0f}~{temp_max:.0f}℃"]
    if alert_str:
        subject_parts.append(alert_str)
    subject = " · ".join(subject_parts)

    # ── HTML 正文 ───────────────────────────────────────────────────────────
    accent_color = "#e74c3c" if any_rain else "#2c98f0"
    accent_bg    = "#fdf0ef" if any_rain else "#edf6ff"

    # ── Hero 卡片：目标日全天概览 ───────────────────────────────────────────
    # 从每日预报取最高/最低温 + 主天气
    if target_cast:
        target_skycon = target_cast.get("skycon", target_cast.get("day_weather", ""))
        target_day_temp = target_cast.get("day_temp", "?")
        target_night_temp = target_cast.get("night_temp", "?")
    else:
        target_skycon = ""
        target_day_temp = "?"
        target_night_temp = "?"

    # 用上午分段数据补充 hero（湿度+风力等）
    hero_morning = slots.get("morning")
    if hero_morning:
        hero_icon = _sky_icon(hero_morning.get("skycon", hero_morning.get("weather", "")))
        hero_weather = hero_morning.get("weather", "")
        hero_wind_dir = hero_morning.get("wind_direction", "—")
        hero_wind_pow = hero_morning.get("wind_power", "—")
        hero_humidity = hero_morning.get("humidity", "")
    else:
        hero_icon = _sky_icon(target_skycon) if target_skycon else "🌤️"
        hero_weather = target_cast.get("day_weather", "") if target_cast else ""
        hero_wind_dir = "—"
        hero_wind_pow = "—"
        hero_humidity = ""

    hero_extra_html = ""
    if hero_wind_dir != "—" or hero_humidity:
        parts = []
        if hero_humidity and hero_humidity not in ("N/A", ""):
            parts.append(f"💧 {hero_humidity}%")
        if hero_wind_dir != "—":
            parts.append(f"🍃 {hero_wind_dir} {hero_wind_pow}级")
        hero_extra_html = f'<div class="hero-meta">{"<span>" + "</span><span>".join(parts) + "</span>"}</div>'

    now_card = f"""
        <div class="card hero">
            <div class="hero-main">
                <span class="hero-icon">{hero_icon}</span>
                <span class="hero-temp">{target_night_temp}~{target_day_temp}°C</span>
            </div>
            <div class="hero-weather">{hero_weather}</div>
            {hero_extra_html}
        </div>"""

    # 次要信息：仅早间模式展示（晚间小时预报无 AQI/气压等数据，不展示）
    aqi        = live.get("aqi", "") if mode == "morning" else ""
    pm25       = live.get("pm25", "") if mode == "morning" else ""
    air_desc   = live.get("air_desc", "") if mode == "morning" else ""
    visibility = live.get("visibility", "") if mode == "morning" else ""
    pressure   = live.get("pressure", "") if mode == "morning" else ""
    cloudrate  = live.get("cloudrate", "") if mode == "morning" else ""

    # ── 一句话总结（天气概览 + 带伞）──────────────────────────────────────────
    weather_parts = []
    for key, label in [("morning", "上午"), ("afternoon", "下午"), ("night", "晚间")]:
        item = slots.get(key)
        if item:
            w = item.get("weather", item.get("skycon", ""))
            if w:
                weather_parts.append(f"{label}{w}")
    if weather_parts:
        if len(set(weather_parts)) == 1:
            weather_summary = f"{target_label}全天{weather_parts[0].split('，')[0].removeprefix('上午').removeprefix('下午').removeprefix('晚间')}"
        else:
            weather_summary = f"{target_label}{'，'.join(weather_parts)}"
    else:
        weather_summary = ""

    if weather_summary and rain_hint:
        summary_text = f"{weather_summary}，{rain_hint}"
    elif weather_summary:
        summary_text = f"{weather_summary}"
    elif rain_hint:
        summary_text = f"{rain_hint}"
    else:
        summary_text = ""

    # ── 构建 HTML ───────────────────────────────────────────────────────────

    def _slot_html(item: dict, label: str, is_highlight=False) -> str:
        if not item:
            return f"""
        <div class="card{' highlight' if is_highlight else ''}" style="opacity:.55">
            <div class="card-label">{label}</div>
            <div class="card-main">暂无数据</div>
        </div>"""
        sky = item.get("skycon", item.get("weather", ""))
        icon = _sky_icon(sky)
        temp = item.get("temperature", "?")
        wd = item.get("wind_direction", "—")
        wp = item.get("wind_power", "—")
        humid = item.get("humidity", "")
        is_rain_slot = _is_rain(sky)
        umbrella_tag = '<div class="slot-umbrella">🌂</div>' if is_rain_slot else ''
        extra = f'<div class="sub">湿度{humid}%</div>' if humid not in ("", "N/A", None) else ''
        return f"""
        <div class="card{' highlight' if is_highlight else ''}{' rainy' if is_rain_slot else ''}">
            <div class="card-label">{label}</div>
            {umbrella_tag}
            <div class="card-main">
                <span class="big-icon">{icon}</span>
                <span class="big-temp">{temp}°</span>
            </div>
            <div class="card-sub">{wd} {wp}级{extra}</div>
        </div>"""

    # 次要信息区
    extras = []
    if aqi and aqi not in ("N/A", "", None):
        extras.append(f"<span>🍃 AQI {aqi} {air_desc}</span>")
    if pm25 and pm25 not in ("N/A", "", None):
        extras.append(f"<span>💨 PM2.5 {pm25} μg/m³</span>")
    if visibility and visibility not in ("N/A", "", None):
        extras.append(f"<span>👁️ 能见度 {visibility} km</span>")
    if pressure and pressure not in ("N/A", "", None):
        extras.append(f"<span>📊 气压 {pressure} hPa</span>")
    if cloudrate and cloudrate not in ("N/A", "", None):
        extras.append(f"<span>☁️ 云量 {cloudrate}%</span>")

    extras_html = ""
    if extras:
        extras_html = f"""
        <div class="extras">{" &nbsp;|&nbsp; ".join(extras)}</div>"""


    # ── 组装完整 HTML ───────────────────────────────────────────────────────
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Weather-Email</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif;
         background: #f0f2f5; padding: 20px; }}
  .wrap {{ max-width: 480px; margin: 0 auto; background: #fff;
           border-radius: 16px; overflow: hidden;
           box-shadow: 0 4px 24px rgba(0,0,0,.10); }}

  /* 顶栏 */
  .topbar {{ background: {accent_color}; color: #fff; padding: 14px 20px;
             display: flex; align-items: center; justify-content: space-between; }}
  .topbar-title {{ font-size: 16px; font-weight: 600; letter-spacing: 1px; }}
  .topbar-date  {{ font-size: 12px; opacity: .85; }}

  /* 卡片通用 */
  .section {{ padding: 16px 20px 8px; }}
  .card-grid {{ display: grid; grid-template-columns: repeat(3, 1fr);
                gap: 8px; }}

  /* 全天概览（hero） */
  .card.hero {{ background: {accent_bg}; border-radius: 12px 12px 0 0;
                padding: 18px 20px; margin: 14px 20px 0; }}
  .hero-main {{ display: flex; align-items: flex-end; gap: 8px; margin-bottom: 4px; }}
  .hero-icon {{ font-size: 52px; line-height: 1; }}
  .hero-temp {{ font-size: 48px; font-weight: 700; color: #1a1a1a; line-height: 1; }}
  .hero-weather {{ font-size: 16px; color: #555; margin-bottom: 6px; }}
  .rain-badge {{ background: #e74c3c; color: #fff; border-radius: 20px;
                 padding: 2px 10px; font-size: 12px; margin-left: 6px; }}
  .hero-meta {{ display: flex; gap: 14px; flex-wrap: wrap; font-size: 12px; color: #777; }}

  /* 分段天气 */
  .card {{ background: #f8f9fa; border-radius: 10px; padding: 12px 10px;
          text-align: center; }}
  .card.rainy {{ border: 1.5px solid #e74c3c; }}
  .slot-umbrella {{ background: #e74c3c; color: #fff; border-radius: 20px; font-size: 11px; padding: 2px 8px; margin-bottom: 6px; display: inline-block; }}
  .card-label {{ font-size: 11px; color: #aaa; margin-bottom: 6px; text-transform: uppercase;
                  letter-spacing: 1px; }}
  .card-main {{ display: flex; flex-direction: column; align-items: center; gap: 2px; }}
  .big-icon {{ font-size: 28px; line-height: 1; }}
  .big-temp {{ font-size: 22px; font-weight: 700; color: #1a1a1a; }}
  .card-sub {{ font-size: 11px; color: #888; margin-top: 4px; line-height: 1.4; }}
  .sub {{ display: block; margin-top: 2px; }}

  /* 重要提示 */
  .hint-bar {{ background: {accent_bg}; border-left: 4px solid {accent_color};
             margin: 0 20px; padding: 10px 14px; border-radius: 0 0 8px 8px; }}
  .hint-text {{ font-size: 14px; color: #333; }}

  /* 着装建议 */
  .clothing-bar {{ background: #f0f9eb; border-left: 4px solid #67c23a;
                   margin: 12px 20px; padding: 10px 14px; border-radius: 0 8px 8px 0; }}
  .clothing-brief {{ font-size: 14px; color: #333; }}
  .clothing-detail {{ font-size: 12px; color: #888; margin-top: 2px; }}

  /* 次要信息 */
  .extras {{ padding: 8px 20px 16px; display: flex; flex-wrap: wrap;
             gap: 6px 16px; font-size: 12px; color: #888; }}

  /* 底部 */
  .footer {{ text-align: center; padding: 14px; font-size: 11px; color: #bbb; }}
</style>
</head>
<body>
<div class="wrap">
  <!-- 顶栏 -->
  <div class="topbar">
    <span class="topbar-title">{mode_title}</span>
    <span class="topbar-date">{target_date}</span>
  </div>

  {now_card}

  <!-- 一句话总结 -->
  <div class="hint-bar">
    <div class="hint-text">{summary_text}</div>
  </div>

  <div class="section">
    <div class="card-grid">
      {_slot_html(slots.get("morning"), '上午', mode == "morning")}
      {_slot_html(slots.get("afternoon"), '下午')}
      {_slot_html(slots.get("night"), '晚间')}
    </div>
  </div>

  <!-- 着装建议 -->
  <div class="clothing-bar">
    <div class="clothing-brief">{clothing_brief}</div>
    <div class="clothing-detail">{clothing_detail}（{temp_min:.0f}~{temp_max:.0f}℃）</div>
  </div>


  {extras_html}

  <!-- 底部 -->
  <div class="footer">由 Weather-Email 自动推送 · 数据来源：{source.upper() if source else "API"}</div>
</div>
</body>
</html>"""

    return subject, html


# ── 纯文本版本（兼容备用） ────────────────────────────────────────────────────
def generate_text(weather: dict, mode: str = "evening") -> tuple[str, str]:
    subject, html = generate_html(weather, mode=mode)
    live = weather.get("live", {}) or {}
    city = live.get("city", "?")
    temp = live.get("temperature", "?")
    weather_now = live.get("weather", "?")
    humidity = live.get("humidity", "?")
    wind_dir = live.get("wind_direction", "?")
    wind_pow = live.get("wind_power", "?")
    rain_hint = "记得带伞！" if _is_rain(weather_now) else "暂不需要带伞"

    if mode == "morning":
        day_label = "今日"
    else:
        day_label = "明日"

    lines = [
        f"【{city}】{day_label}天气预报",
        f"{weather_now} {temp}℃",
        f"💧 湿度{humidity}%  🍃 {wind_dir} {wind_pow}级",
        "",
        f"📌 {rain_hint}",
        "",
        "─── 天气预报 ───",
        "上午 / 下午 / 晚间",
        "(请查看邮件正文获取详细预报)",
        "",
        "Weather-Email 自动推送",
    ]
    return subject, "\n".join(lines)
