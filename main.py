import os
from config import *
from weather_api import WeatherAPI, CaiyunAPI
from email_sender import send_email

# 本地调试加载.env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def main():
    print("正在获取天气...")

    # 从环境变量读取敏感信息
    GAODE_KEY = os.getenv("GAODE_KEY")
    CAIYUN_TOKEN = os.getenv("CAIYUN_TOKEN")
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")
    EMAIL_AUTH_CODE = os.getenv("EMAIL_AUTH_CODE")
    EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

    if not all([EMAIL_SENDER, EMAIL_AUTH_CODE, EMAIL_RECEIVER]):
        print("❌ 邮箱环境变量缺失！")
        return

    # ========== 根据数据源选择 API ==========
    if WEATHER_SOURCE == "caiyun":
        if not CAIYUN_TOKEN:
            print("❌ 彩云 API Token 缺失！请设置环境变量 CAIYUN_TOKEN")
            return
        weather = CaiyunAPI.get_weather(LOCATION, CAIYUN_TOKEN, extensions=WEATHER_TYPE)
    else:  # 默认使用高德
        if not GAODE_KEY:
            print("❌ 高德 API Key 缺失！请设置环境变量 GAODE_KEY")
            return
        weather = WeatherAPI.get_weather(LOCATION, GAODE_KEY, extensions=WEATHER_TYPE)

    if not weather["success"]:
        print(f"❌ 天气获取失败: {weather['error']}")
        return

    print(f"✅ 天气获取成功 ({WEATHER_SOURCE}): {weather['city']}")
    live = weather["live"]

    if live is None:
        print("❌ 天气实况数据为空，请检查配置是否正确")
        return

    # ========== 彩云特有关键点提示 ==========
    if weather.get("source") == "caiyun" and weather.get("forecast_keypoint"):
        print(f"🌤️ {weather['forecast_keypoint']}")

    # ========== 根据 config 中的 WEATHER_FIELDS 动态生成邮件内容 ==========
    content = "【今日天气播报】\n"
    content += "------------------------\n"

    # 基础字段映射（高德+彩云通用）
    field_map = {
        "城市": f"城市：{live['city']}",
        "温度": f"温度：{live['temperature']}℃",
        "天气": f"天气：{live['weather']}",
        "湿度": f"湿度：{live['humidity']}%",
        "风向": f"风向：{live['wind_direction']}",
        "风力": f"风力：{live['wind_power']}级",
        "更新时间": f"更新时间：{live['report_time']}"
    }

    # 彩云特有字段
    if weather.get("source") == "caiyun":
        field_map.update({
            "体感温度": f"体感温度：{live.get('apparent_temperature', 'N/A')}℃",
            "能见度": f"能见度：{live.get('visibility', 'N/A')} km",
            "气压": f"气压：{live.get('pressure', 'N/A')} hPa",
            "云量": f"云量：{live.get('cloudrate', 'N/A')}%",
            "AQI": f"AQI：{live.get('aqi', 'N/A')}",
            "PM2.5": f"PM2.5：{live.get('pm25', 'N/A')} μg/m³",
            "空气质量": f"空气质量：{live.get('air_desc', 'N/A')}",
        })

    for field in WEATHER_FIELDS:
        if field in field_map:
            content += field_map[field] + "\n"

    # ========== 彩云特有关键点（加入邮件内容） ==========
    if weather.get("source") == "caiyun" and weather.get("forecast_keypoint"):
        content += f"\n📍 {weather['forecast_keypoint']}\n"

    # ========== 发送邮件 ==========
    print("📤 发送邮件中...")
    ok = send_email(
        sender=EMAIL_SENDER,
        auth_code=EMAIL_AUTH_CODE,
        receiver=EMAIL_RECEIVER,
        subject=f"{live['city']} {live['weather']} {live['temperature']}℃",
        content=content,
        smtp_server=SMTP_SERVER,
        smtp_port=SMTP_PORT
    )

    if ok:
        print("✅ 邮件发送成功！")
    else:
        print("❌ 邮件发送失败！")

if __name__ == "__main__":
    main()