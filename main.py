import os
from config import *
from weather_api import WeatherAPI
from email_sender import send_email

def main():
    # ========== 敏感信息从环境变量读取 ==========
    GAODE_KEY = os.getenv("GAODE_KEY")
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")
    EMAIL_AUTH_CODE = os.getenv("EMAIL_AUTH_CODE")
    EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

    print("正在获取天气...")
    weather = WeatherAPI.get_gaode_weather(CITY_CODE, GAODE_KEY)
    if not weather:
        print("天气获取失败")
        return

    title = f"🌤️ 今日天气 - {weather['city']}"
    content = f"""
    🌤️ 今日天气预报
    ------------------------
    城市：{weather['city']}
    温度：{weather['temp']} ℃
    天气：{weather['weather']}
    风向：{weather['wind']}
    风力：{weather['power']} 级
    湿度：{weather['humidity']} %
    更新时间：{weather['time']}
    
    📍 位置：重庆市两江新区蔡家岗街道
    """

    print("正在发送邮件...")
    ok = send_email(
        EMAIL_SENDER, EMAIL_AUTH_CODE, EMAIL_RECEIVER,
        title, content, SMTP_SERVER, SMTP_PORT
    )

    if ok:
        print("✅ 邮件发送成功！")
    else:
        print("❌ 邮件发送失败！")

if __name__ == "__main__":
    main()