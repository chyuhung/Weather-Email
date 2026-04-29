import os
from config import CITY_CODE, SMTP_SERVER, SMTP_PORT
from weather_api import WeatherAPI
from email_sender import send_email

# 本地调试加载 .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def main():
    print("正在获取天气...")

    # 从环境变量读取敏感信息
    GAODE_KEY = os.getenv("GAODE_KEY")
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")
    EMAIL_AUTH_CODE = os.getenv("EMAIL_AUTH_CODE")
    EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

    # 检查配置
    if not all([GAODE_KEY, EMAIL_SENDER, EMAIL_AUTH_CODE, EMAIL_RECEIVER]):
        print("❌ 环境变量缺失！")
        return

    # 获取天气
    weather = WeatherAPI.get_gaode_weather(CITY_CODE, GAODE_KEY)
    if not weather:
        print("❌ 天气获取失败")
        return

    print("✅ 天气获取成功")

    # 构造内容
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

    # 发送邮件
    print("📤 发送邮件中...")
    ok = send_email(
        EMAIL_SENDER,
        EMAIL_AUTH_CODE,
        EMAIL_RECEIVER,
        f"🌤️ 今日天气 - {weather['city']}",
        content,
        SMTP_SERVER,
        SMTP_PORT
    )

    if ok:
        print("✅ 邮件发送成功！")
    else:
        print("❌ 邮件发送失败！")

if __name__ == "__main__":
    main()