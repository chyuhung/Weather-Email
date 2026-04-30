"""
天气邮件正文生成器
- 支持早晚两种推送模式（morning / evening）
- morning：推送今天（上午带伞判断 + 今天上午/下午/晚间 + 着装建议）
- evening：推送明天（明天上午带伞判断 + 明天上午/下午/晚间 + 着装建议）
"""
from datetime import datetime, timedelta


# ── 天气图标（emoji） ──────────────────────────────────────────────────────────
def _sky_icon(skycon: str) -> str:
    icon_map = {
        "CLEAR_DAY": "☀️", "CLEAR_NIGHT": "🌙",
        "PARTLY_CLOUDY_DAY": "⛅", "PARTLY_CLOUDY_NIGHT": "⛅",
        "CLOUDY": "☁️", "LIGHT_RAIN": "🌦️", "MODERATE_RAIN": "🌧️",
        "HEAVY_RAIN": "🌧️", "STORM_RAIN": "⛈️",
        "FOG": "🌫️", "LIGHT_HAZE": "😷", "MODERATE_HAZE": "😷",
        "HEAVY_HAZE": "😷", "LIGHT_SNOW": "🌨️", "MODERATE_SNOW": "❄️",
        "HEAVY_SNOW": "❄️", "STORM_SNOW": "❄️",
        "DUST": "🌿", "SAND": "🌿", "WIND": "💨",
    }
    # 高德天气直接传文字兜底
    if skycon not in icon_map and len(skycon) > 10:
        skycon = skycon.upper()
    if skycon not in icon_map:
        # 高德晴/雨等中文
        cjk = {"晴": "☀️", "多云": "⛅", "阴": "☁️", "小雨": "🌦️",
               "中雨": "🌧️", "大雨": "🌧️", "暴雨": "⛈️",
               "雷阵雨": "⛈️", "雾": "🌫️", "霾": "😷",
               "沙尘": "🌿", "扬沙": "🌿", "雨夹雪": "🌨️",
               "小雪": "🌨️", "中雪": "❄️", "大雪": "❄️"}
        for k, v in cjk.items():
            if k in skycon:
                return v
        return "🌤️"
    return icon_map.get(skycon, "🌤️")


def _is_rain(skycon: str) -> bool:
    """判断是否需要带伞（雨、雪、雨夹雪）"""
    rain_keys = ["RAIN", "STORM", "雪", "雨夹雪", "雨"]
    s = skycon.upper()
    return any(k.upper() in s for k in rain_keys)


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
    if forecast and forecast.get("casts"):
        for cast in forecast["casts"]:
            if cast.get("date", "").startswith(target_date):
                try:
                    t_max = float(cast.get("day_temp", 0))
                    t_min = float(cast.get("night_temp", 0))
                    temps.extend([t_max, t_min])
                except (ValueError, TypeError):
                    pass

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

    # 当前实况（早间用）
    icon_now = _sky_icon(live.get("skycon", live.get("weather", "")))
    temp_now_str = live.get("temperature", "?")
    weather_now = live.get("weather", "")
    humidity_now = live.get("humidity", "N/A")
    wind_dir_now = live.get("wind_direction", "—")
    wind_pow_now = live.get("wind_power", "—")
    feels_like = live.get("apparent_temperature", "")
    report_time = live.get("report_time", "")

    # 明日全天概览（晚间用）—— 从 daily forecast 取
    tomorrow_cast = None
    forecast_data = weather.get("forecast", {}) or {}
    for cast in (forecast_data.get("casts") or []):
        if cast.get("date", "").startswith(target_date):
            tomorrow_cast = cast
            break

    if tomorrow_cast:
        tmr_skycon = tomorrow_cast.get("skycon", tomorrow_cast.get("day_weather", ""))
        tmr_icon = _sky_icon(tmr_skycon)
        tmr_weather = tomorrow_cast.get("day_weather", "")
        tmr_day_temp = tomorrow_cast.get("day_temp", "?")
        tmr_night_temp = tomorrow_cast.get("night_temp", "?")
    else:
        tmr_skycon = ""
        tmr_icon = "🌤️"
        tmr_weather = ""
        tmr_day_temp = "?"
        tmr_night_temp = "?"

    # 次要信息（仅早间模式从实况取）
    aqi     = live.get("aqi", "") if mode == "morning" else ""
    pm25    = live.get("pm25", "") if mode == "morning" else ""
    air_desc = live.get("air_desc", "") if mode == "morning" else ""
    visibility = live.get("visibility", "") if mode == "morning" else ""
    pressure = live.get("pressure", "") if mode == "morning" else ""
    cloudrate = live.get("cloudrate", "") if mode == "morning" else ""

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
        summary_text = f"💡 {weather_summary}，{rain_hint}"
    elif weather_summary:
        summary_text = f"💡 {weather_summary}"
    elif rain_hint:
        summary_text = f"💡 {rain_hint}"
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
        umbrella_tag = '<div class="slot-umbrella">🌂 带伞</div>' if is_rain_slot else ''
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

    # ── Hero 卡片：早间=此刻实况，晚间=明日全天概览 ──────────────────────────
    if mode == "morning":
        now_card = f"""
        <div class="card hero">
            <div class="hero-main">
                <span class="hero-icon">{icon_now}</span>
                <span class="hero-temp">{temp_now_str}°C</span>
            </div>
            <div class="hero-weather">{weather_now} {'<span class="rain-badge"></span>' if _is_rain(weather_now) else ''}</div>
            {'<div class="hero-feels">体感 ' + feels_like + '°C</div>' if feels_like not in ("", "N/A", None, "?") else ''}
            <div class="hero-meta">
                <span>💧 {humidity_now}%</span>
                <span>🍃 {wind_dir_now} {wind_pow_now}级</span>
                </div>
        </div>"""
    else:
        # 晚间：明日全天概览
        now_card = f"""
        <div class="card hero">
            <div class="hero-main">
                <span class="hero-icon">{tmr_icon}</span>
                <span class="hero-temp">{tmr_night_temp}~{tmr_day_temp}°C</span>
            </div>
            <div class="hero-weather">{tmr_weather} {'<span class="rain-badge"></span>' if _is_rain(tmr_skycon) or any_rain else ''}</div>
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

    # keypoint_html 已合并到 summary_text，不再单独显示

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

  /* 当前实况（hero） */
  .card.hero {{ background: {accent_bg}; border-radius: 12px 12px 0 0;
                padding: 18px 20px; margin: 14px 20px 0; }}
  .hero-main {{ display: flex; align-items: flex-end; gap: 8px; margin-bottom: 4px; }}
  .hero-icon {{ font-size: 52px; line-height: 1; }}
  .hero-temp {{ font-size: 48px; font-weight: 700; color: #1a1a1a; line-height: 1; }}
  .hero-weather {{ font-size: 16px; color: #555; margin-bottom: 6px; }}
  .rain-badge {{ background: #e74c3c; color: #fff; border-radius: 20px;
                 padding: 2px 10px; font-size: 12px; margin-left: 6px; }}
  .hero-feels {{ font-size: 13px; color: #888; margin-bottom: 6px; }}
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
    <span class="topbar-date">{target_date if mode == 'evening' else now.strftime('%Y-%m-%d')}</span>
  </div>

  {now_card}

  <!-- 一句话总结 -->
  <div class="hint-bar">
    <div class="hint-text">{summary_text}</div>
  </div>

  <!-- {target_label}分段天气 -->
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
    report = live.get("report_time", "?")
    rain_hint = "记得带伞！" if _is_rain(weather_now) else "暂不需要带伞"

    lines = [
        f"【{city}】{weather_now} {temp}℃",
        f"💧 湿度{humidity}%  🍃 {wind_dir} {wind_pow}级",
        f"🕐 更新于 {report}",
        "",
        f"📌 {rain_hint}",
        "",
        "─── 天气预报 ───",
        "上午 (6~11时) / 下午 (12~17时) / 晚间 (18~23时)",
        "(请查看邮件正文获取详细预报)",
        "",
        "Weather-Email 自动推送",
    ]
    return subject, "\n".join(lines)
