import os
from config import CITY_CODE, SMTP_SERVER, SMTP_PORT
from weather_api import WeatherAPI
from email_sender import send_email

# 本地调试加载.env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def main():
    print("正在获取天气...")

    GAODE_KEY = os.getenv("GAODE_KEY")
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")
    EMAIL_AUTH_CODE = os.getenv("EMAIL_AUTH_CODE")
    EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

    if not all([GAODE_KEY, EMAIL_SENDER, EMAIL_AUTH_CODE, EMAIL_RECEIVER]):
        print("❌ 环境变量缺失！")
        return

    # ===================== 最稳定：使用经纬度 =====================
    weather = WeatherAPI.get_live_weather(CITY_CODE, GAODE_KEY)

    if not weather["success"]:
        print(f"❌ 天气获取失败: {weather['error']}")
        return

    print(f"✅ 天气获取成功: {weather['city']}")
    live = weather["live"]

    content = f"""
【今日天气播报】
城市：{live['city']}
时间：{live['report_time']}
天气：{live['weather']}
温度：{live['temperature']}℃
湿度：{live['humidity']}%
风向：{live['wind_direction']}
风力：{live['wind_power']}级
"""

    print("📤 发送邮件中...")
    ok = send_email(
        sender=EMAIL_SENDER,
        auth_code=EMAIL_AUTH_CODE,
        receiver=EMAIL_RECEIVER,
        subject=f"{live['city']} 今日{live['weather']} {live['temperature']}℃",
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