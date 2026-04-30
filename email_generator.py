"""
天气邮件正文生成器
- 重点：当前实况 + 明日早/中/晚分段
- 次要：AQI、PM2.5、能见度等辅助信息
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
    rain_keys = ["RAIN", "STORM", "HAZE", "DUST", "SAND", "FOG",
                 "雨", "霾", "雾", "沙", "雪"]
    s = skycon.upper()
    return any(k.upper() in s for k in rain_keys)


# ── 提取明日分段数据 ──────────────────────────────────────────────────────────
def _slice_tomorrow_hourly(hourly: list, today_str: str) -> dict:
    """
    从小时预报中提取今日（剩余小时）和明日分段。
    返回: { "now": {...}, "tomorrow_morning": {...}, "tomorrow_afternoon": {...}, "tomorrow_night": {...} }
    """
    now = datetime.now()
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    today_date = now.strftime("%Y-%m-%d")

    slots = {
        "now": None,
        "tomorrow_morning": None,   # 06~11
        "tomorrow_afternoon": None, # 12~17
        "tomorrow_night": None,     # 18~23
    }

    for item in hourly:
        dt_str = item.get("datetime", "")
        try:
            dt = datetime.fromisoformat(dt_str.replace("+08:00", "").replace("Z", ""))
        except Exception:
            continue

        d_str = dt.strftime("%Y-%m-%d")
        hour = dt.hour

        # 优先找最近的小时作为当前
        if d_str == today_date and slots["now"] is None:
            slots["now"] = item

        if d_str == tomorrow:
            if 6 <= hour <= 11 and slots["tomorrow_morning"] is None:
                slots["tomorrow_morning"] = item
            elif 12 <= hour <= 17 and slots["tomorrow_afternoon"] is None:
                slots["tomorrow_afternoon"] = item
            elif 18 <= hour <= 23 and slots["tomorrow_night"] is None:
                slots["tomorrow_night"] = item

    return slots


def _slot_label(slot: str) -> str:
    return {"now": "此刻", "tomorrow_morning": "明早", "tomorrow_afternoon": "明午", "tomorrow_night": "明晚"}[slot]


# ── 主生成函数 ─────────────────────────────────────────────────────────────────
def generate_html(weather: dict) -> tuple[str, str]:
    """
    生成 HTML 邮件正文和邮件主题。
    返回: (subject, html_body)
    """
    live = weather.get("live", {}) or {}
    city = live.get("city", weather.get("city", "未知"))
    source = weather.get("source", "unknown")

    # ── 判断带伞（主题核心） ──────────────────────────────────────────────────
    now_sky = live.get("weather", live.get("skycon", ""))
    is_rain_now = _is_rain(now_sky)
    will_rain_tomorrow = False

    hourly = weather.get("hourly_forecast", [])
    slots = _slice_tomorrow_hourly(hourly, datetime.now().strftime("%Y-%m-%d"))
    for key in ["tomorrow_morning", "tomorrow_afternoon", "tomorrow_night"]:
        item = slots.get(key)
        if item and _is_rain(item.get("weather", item.get("skycon", ""))):
            will_rain_tomorrow = True
            break

    if is_rain_now and will_rain_tomorrow:
        umbrella_emoji = "🌂"
        umbrella_hint = "全天有雨，出门记得带伞！"
    elif is_rain_now:
        umbrella_emoji = "🌂"
        umbrella_hint = "现在有雨，出门带伞！"
    elif will_rain_tomorrow:
        umbrella_emoji = "⏰"
        umbrella_hint = "明天有雨，出行提前备伞！"
    else:
        umbrella_emoji = "✅"
        umbrella_hint = "未来天气适宜出行，暂不需要带伞"

    # ── 邮件主题 ──────────────────────────────────────────────────────────────
    temp_now = live.get("temperature", "?")
    weather_now = live.get("weather",
                           _sky_icon(live.get("skycon", "")))
    subject = f"{umbrella_emoji} {city} {weather_now} {temp_now}℃ · {umbrella_hint}"

    # ── HTML 正文 ─────────────────────────────────────────────────────────────
    accent_color = "#e74c3c" if is_rain_now or will_rain_tomorrow else "#2c98f0"
    accent_bg    = "#fdf0ef" if is_rain_now or will_rain_tomorrow else "#edf6ff"

    # 当前实况
    icon_now = _sky_icon(live.get("skycon", now_sky))
    temp_now_str = live.get("temperature", "?")
    humidity_now = live.get("humidity", live.get("humidity", "N/A"))
    wind_dir_now = live.get("wind_direction", "—")
    wind_pow_now = live.get("wind_power", "—")
    feels_like = live.get("apparent_temperature", "")

    # 次要信息
    aqi     = live.get("aqi", "")
    pm25    = live.get("pm25", "")
    air_desc = live.get("air_desc", "")
    visibility = live.get("visibility", "")
    pressure = live.get("pressure", "")
    cloudrate = live.get("cloudrate", "")
    report_time = live.get("report_time", "")

    # 明日分段
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
        rain_flag = "🔴 " if _is_rain(sky) else ""
        extra = f'<span class="sub">{rain_flag}湿度{humid}%</span>' if humid not in ("", "N/A", None) else ""
        return f"""
        <div class="card{' highlight' if is_highlight else ''}">
            <div class="card-label">{label}</div>
            <div class="card-main">
                <span class="big-icon">{icon}</span>
                <span class="big-temp">{temp}°</span>
            </div>
            <div class="card-sub">{wd} {wp}级{extra}</div>
        </div>"""

    now_card = f"""
        <div class="card hero">
            <div class="hero-location">📍 {city}</div>
            <div class="hero-main">
                <span class="hero-icon">{icon_now}</span>
                <span class="hero-temp">{temp_now_str}°C</span>
            </div>
            <div class="hero-weather">{weather_now} {'<span class="rain-badge">🌂记得带伞</span>' if is_rain_now else ''}</div>
            {'<div class="hero-feels">体感 ' + feels_like + '°C</div>' if feels_like not in ("", "N/A", None, "?") else ''}
            <div class="hero-meta">
                <span>💧 {humidity_now}%</span>
                <span>🍃 {wind_dir_now} {wind_pow_now}级</span>
                <span>🕐 {report_time}</span>
            </div>
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

    # 预警提示
    keypoint = weather.get("forecast_keypoint", "") or ""
    keypoint_html = f'<div class="keypoint">💡 {keypoint}</div>' if keypoint else ""

    # ── 组装完整 HTML ─────────────────────────────────────────────────────────
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
  .section-title {{ font-size: 12px; color: #999; text-transform: uppercase;
                    letter-spacing: 1.5px; margin-bottom: 10px; font-weight: 600; }}
  .card-grid {{ display: grid; grid-template-columns: repeat(4, 1fr);
                gap: 8px; }}

  /* 当前实况（hero） */
  .card.hero {{ background: {accent_bg}; border-radius: 12px; padding: 16px 18px;
                margin: 16px 20px 4px; }}
  .hero-location {{ font-size: 12px; color: #888; margin-bottom: 4px; }}
  .hero-main {{ display: flex; align-items: flex-end; gap: 8px; margin-bottom: 4px; }}
  .hero-icon {{ font-size: 52px; line-height: 1; }}
  .hero-temp {{ font-size: 48px; font-weight: 700; color: #1a1a1a; line-height: 1; }}
  .hero-weather {{ font-size: 16px; color: #555; margin-bottom: 6px; }}
  .rain-badge {{ background: #e74c3c; color: #fff; border-radius: 20px;
                 padding: 2px 10px; font-size: 12px; margin-left: 6px; }}
  .hero-feels {{ font-size: 13px; color: #888; margin-bottom: 6px; }}
  .hero-meta {{ display: flex; gap: 14px; flex-wrap: wrap; font-size: 12px; color: #777; }}

  /* 明日分段 */
  .card {{ background: #f8f9fa; border-radius: 10px; padding: 12px 10px;
          text-align: center; }}
  .card.highlight {{ background: {accent_bg}; }}
  .card-label {{ font-size: 11px; color: #aaa; margin-bottom: 6px; text-transform: uppercase;
                  letter-spacing: 1px; }}
  .card-main {{ display: flex; flex-direction: column; align-items: center; gap: 2px; }}
  .big-icon {{ font-size: 28px; line-height: 1; }}
  .big-temp {{ font-size: 22px; font-weight: 700; color: #1a1a1a; }}
  .card-sub {{ font-size: 11px; color: #888; margin-top: 4px; line-height: 1.4; }}
  .sub {{ display: block; margin-top: 2px; }}
  .rain-flag {{ color: #e74c3c; font-size: 11px; }}

  /* 重要提示 */
  .hint-bar {{ background: {accent_bg}; border-left: 4px solid {accent_color};
               margin: 12px 20px; padding: 10px 14px; border-radius: 0 8px 8px 0; }}
  .hint-text {{ font-size: 14px; color: #333; }}
  .hint-sub  {{ font-size: 12px; color: #888; margin-top: 2px; }}

  /* 次要信息 */
  .extras {{ padding: 8px 20px 16px; display: flex; flex-wrap: wrap;
             gap: 6px 16px; font-size: 12px; color: #888; }}
  .keypoint {{ background: #fffbe6; border-left: 3px solid #f5a623;
               margin: 0 20px 12px; padding: 8px 12px; border-radius: 0 6px 6px 0;
               font-size: 13px; color: #7a5a00; }}

  /* 底部 */
  .footer {{ text-align: center; padding: 14px; font-size: 11px; color: #bbb; }}
</style>
</head>
<body>
<div class="wrap">
  <!-- 顶栏 -->
  <div class="topbar">
    <span class="topbar-title">🌤️ Weather-Email</span>
    <span class="topbar-date">{datetime.now().strftime('%Y-%m-%d')}</span>
  </div>

  <!-- 当前实况 -->
  <div class="section">
    <div class="section-title">此刻天气</div>
  </div>
  {now_card}

  <!-- 带伞提示 -->
  <div class="hint-bar">
    <div class="hint-text">{umbrella_emoji} {umbrella_hint}</div>
    <div class="hint-sub">{city} · {report_time}</div>
  </div>

  <!-- 明日分段 -->
  <div class="section">
    <div class="section-title">明日天气</div>
  </div>
  <div class="section" style="padding-top:0">
    <div class="card-grid">
      {_slot_html(slots.get("tomorrow_morning"), '早 6~11')}
      {_slot_html(slots.get("tomorrow_afternoon"), '午 12~17')}
      {_slot_html(slots.get("tomorrow_night"), '晚 18~23')}
    </div>
  </div>

  {keypoint_html}
  {extras_html}

  <!-- 底部 -->
  <div class="footer">由 Weather-Email 自动推送 · 数据来源：{source.upper() if source else "API"}</div>
</div>
</body>
</html>"""

    return subject, html


# ── 纯文本版本（兼容备用） ────────────────────────────────────────────────────
def generate_text(weather: dict) -> tuple[str, str]:
    subject, html = generate_html(weather)
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
        "─── 明日天气 ───",
        "早 (6~11时) / 午 (12~17时) / 晚 (18~23时)",
        "(请查看邮件正文获取详细预报)",
        "",
        "Weather-Email 自动推送",
    ]
    return subject, "\n".join(lines)
